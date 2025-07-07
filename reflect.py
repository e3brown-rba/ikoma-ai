#!/usr/bin/env python3
"""
Nightly Reflection Script for Ikoma Agent

This script runs nightly to:
1. Analyze the day's conversations from the SQLite database
2. Generate summaries and extract "lessons learned"
3. Store insights back to the memory system for improved future responses

Usage:
    python reflect.py [--date YYYY-MM-DD] [--dry-run]

Schedule with cron:
    0 2 * * * /usr/bin/python3 /path/to/reflect.py >> /var/log/ikoma_reflect.log 2>&1
"""

import os
import sqlite3
import json
import argparse
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any

# LangChain imports
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from tools.vector_store import get_vector_store
from langchain_openai import OpenAIEmbeddings

# Load environment variables
load_dotenv()

class PatchedOpenAIEmbeddings(OpenAIEmbeddings):
    """Patched embeddings for local LM Studio compatibility."""
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        import openai
        temp_client = openai.OpenAI(
            api_key=self.openai_api_key,
            base_url=self.openai_api_base
        )
        response = temp_client.embeddings.create(input=text, model=self.model)
        return response.data[0].embedding

class ReflectionEngine:
    """Engine for analyzing conversations and generating insights."""
    
    def __init__(self):
        """Initialize the reflection engine with LLM and memory store."""
        # Get environment variables
        self.base_url = os.getenv("LMSTUDIO_BASE_URL", "http://127.0.0.1:11434/v1")
        self.model_name = os.getenv("LMSTUDIO_MODEL", "meta-llama-3-8b-instruct")
        self.embed_model = os.getenv("LMSTUDIO_EMBED_MODEL", "nomic-ai/nomic-embed-text-v1.5-GGUF")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            base_url=self.base_url,
            model=self.model_name,
            temperature=0.1,
        )
        
        # Initialize embeddings and memory store
        self.embeddings = PatchedOpenAIEmbeddings(
            openai_api_key="sk-dummy",
            openai_api_base=self.base_url,
            model=self.embed_model,
        )
        
        self.store = get_vector_store()
        
        # Database path
        self.db_path = Path("agent/memory/conversations.sqlite")
        
    def get_daily_conversations(self, target_date: date) -> List[Dict[str, Any]]:
        """Retrieve conversations from the specified date."""
        if not self.db_path.exists():
            print(f"Warning: Database not found at {self.db_path}")
            return []
        
        conversations = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Calculate date range for the target date
                start_date = datetime.combine(target_date, datetime.min.time())
                end_date = start_date + timedelta(days=1)
                
                # Query conversations within the date range
                # Note: This is a simplified query - actual LangGraph schema may differ
                query = """
                SELECT thread_id, checkpoint_ns, checkpoint_id, parent_checkpoint_id, 
                       type, checkpoint, metadata, created_at
                FROM checkpoints 
                WHERE created_at >= ? AND created_at < ?
                ORDER BY thread_id, created_at
                """
                
                cursor.execute(query, (start_date.isoformat(), end_date.isoformat()))
                rows = cursor.fetchall()
                
                for row in rows:
                    try:
                        # Parse checkpoint data (contains the conversation state)
                        checkpoint_data = json.loads(row['checkpoint']) if row['checkpoint'] else {}
                        
                        conversation = {
                            'thread_id': row['thread_id'],
                            'checkpoint_id': row['checkpoint_id'],
                            'timestamp': row['created_at'],
                            'messages': checkpoint_data.get('channel_values', {}).get('messages', []),
                            'metadata': json.loads(row['metadata']) if row['metadata'] else {}
                        }
                        
                        conversations.append(conversation)
                        
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"Warning: Could not parse checkpoint data: {e}")
                        continue
                        
        except sqlite3.Error as e:
            print(f"Error accessing database: {e}")
            
        return conversations
    
    def extract_meaningful_exchanges(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract meaningful conversation exchanges from raw database data."""
        exchanges = []
        
        for conv in conversations:
            messages = conv.get('messages', [])
            if not messages:
                continue
                
            # Group messages into user-AI exchanges
            current_exchange = {'user': None, 'ai': None, 'timestamp': conv['timestamp']}
            
            for msg in messages:
                if not isinstance(msg, dict):
                    continue
                    
                msg_type = msg.get('type', '')
                content = msg.get('content', '')
                
                if not content:
                    continue
                    
                if msg_type == 'human':
                    # Start new exchange if we have a complete previous one
                    if current_exchange['user'] and current_exchange['ai']:
                        exchanges.append(current_exchange)
                        current_exchange = {'user': None, 'ai': None, 'timestamp': conv['timestamp']}
                    current_exchange['user'] = content
                    
                elif msg_type == 'ai':
                    current_exchange['ai'] = content
                    
            # Add final exchange if complete
            if current_exchange['user'] and current_exchange['ai']:
                exchanges.append(current_exchange)
                
        return exchanges
    
    def generate_daily_summary(self, exchanges: List[Dict[str, Any]], target_date: date) -> Dict[str, Any]:
        """Generate a comprehensive summary of the day's conversations."""
        if not exchanges:
            return {
                'date': target_date.isoformat(),
                'summary': 'No conversations occurred on this date.',
                'key_topics': [],
                'lessons_learned': [],
                'user_patterns': [],
                'improvement_suggestions': []
            }
        
        # Format exchanges for analysis
        formatted_exchanges = []
        for exchange in exchanges:
            formatted_exchanges.append(f"User: {exchange['user']}")
            formatted_exchanges.append(f"AI: {exchange['ai']}")
            formatted_exchanges.append("---")
        
        conversation_text = "\n".join(formatted_exchanges)
        
        # Create analysis prompt
        analysis_prompt = f"""
        Analyze the following day's conversations from {target_date.strftime('%Y-%m-%d')} and provide insights:

        CONVERSATIONS:
        {conversation_text}

        Please provide a comprehensive analysis in the following format:

        DAILY SUMMARY:
        [Provide a 2-3 sentence overview of the day's interactions]

        KEY TOPICS:
        [List 3-5 main topics or themes discussed]

        LESSONS LEARNED:
        [Extract 3-5 insights about user preferences, common questions, or interaction patterns]

        USER PATTERNS:
        [Identify any patterns in how users interact with the assistant]

        IMPROVEMENT SUGGESTIONS:
        [Suggest 2-3 ways the assistant could improve based on these interactions]

        Keep responses concise but informative. Focus on actionable insights.
        """
        
        try:
            response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            analysis_text = response.content
            
            # Parse the structured response
            summary = self._parse_analysis_response(analysis_text)
            summary['date'] = target_date.isoformat()
            summary['total_exchanges'] = len(exchanges)
            
            return summary
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return {
                'date': target_date.isoformat(),
                'summary': f'Error generating summary: {e}',
                'key_topics': [],
                'lessons_learned': [],
                'user_patterns': [],
                'improvement_suggestions': [],
                'total_exchanges': len(exchanges)
            }
    
    def _parse_analysis_response(self, analysis_text: str) -> Dict[str, Any]:
        """Parse the LLM's structured analysis response."""
        sections = {
            'summary': '',
            'key_topics': [],
            'lessons_learned': [],
            'user_patterns': [],
            'improvement_suggestions': []
        }
        
        lines = analysis_text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Detect section headers
            if 'DAILY SUMMARY:' in line.upper():
                current_section = 'summary'
                continue
            elif 'KEY TOPICS:' in line.upper():
                current_section = 'key_topics'
                continue
            elif 'LESSONS LEARNED:' in line.upper():
                current_section = 'lessons_learned'
                continue
            elif 'USER PATTERNS:' in line.upper():
                current_section = 'user_patterns'
                continue
            elif 'IMPROVEMENT SUGGESTIONS:' in line.upper():
                current_section = 'improvement_suggestions'
                continue
            
            # Add content to current section
            if current_section:
                if current_section == 'summary':
                    sections[current_section] = line
                else:
                    # Remove bullet points and add to list
                    clean_line = line.lstrip('- •*').strip()
                    if clean_line:
                        sections[current_section].append(clean_line)
        
        return sections
    
    def store_insights_to_memory(self, summary: Dict[str, Any], dry_run: bool = False) -> None:
        """Store the daily insights to the memory system."""
        if dry_run:
            print("DRY RUN: Would store the following insights:")
            print(json.dumps(summary, indent=2))
            return
        
        try:
            # Store overall daily summary
            namespace = ("reflections", "daily_summaries")
            memory_id = f"summary_{summary['date']}"
            
            summary_entry = {
                "content": f"Daily summary for {summary['date']}: {summary['summary']}",
                "date": summary['date'],
                "type": "daily_summary",
                "total_exchanges": summary.get('total_exchanges', 0),
                "timestamp": datetime.now().isoformat()
            }
            
            self.store.put(namespace, memory_id, summary_entry)
            
            # Store individual lessons learned
            lessons_namespace = ("reflections", "lessons_learned")
            for i, lesson in enumerate(summary.get('lessons_learned', [])):
                lesson_id = f"lesson_{summary['date']}_{i}"
                lesson_entry = {
                    "content": lesson,
                    "date": summary['date'],
                    "type": "lesson_learned",
                    "timestamp": datetime.now().isoformat()
                }
                self.store.put(lessons_namespace, lesson_id, lesson_entry)
            
            # Store improvement suggestions
            improvements_namespace = ("reflections", "improvements")
            for i, suggestion in enumerate(summary.get('improvement_suggestions', [])):
                improvement_id = f"improvement_{summary['date']}_{i}"
                improvement_entry = {
                    "content": suggestion,
                    "date": summary['date'],
                    "type": "improvement_suggestion",
                    "timestamp": datetime.now().isoformat()
                }
                self.store.put(improvements_namespace, improvement_id, improvement_entry)
            
            print(f"✅ Successfully stored insights for {summary['date']}")
            
        except Exception as e:
            print(f"❌ Error storing insights: {e}")
    
    def run_reflection(self, target_date: date = None, dry_run: bool = False) -> Dict[str, Any]:
        """Run the complete reflection process for a given date."""
        if target_date is None:
            target_date = date.today() - timedelta(days=1)  # Yesterday by default
        
        print(f"🤔 Running reflection for {target_date.strftime('%Y-%m-%d')}...")
        
        # Step 1: Get conversations
        conversations = self.get_daily_conversations(target_date)
        print(f"📊 Found {len(conversations)} conversation records")
        
        # Step 2: Extract meaningful exchanges
        exchanges = self.extract_meaningful_exchanges(conversations)
        print(f"💬 Extracted {len(exchanges)} meaningful exchanges")
        
        # Step 3: Generate summary and insights
        print("🧠 Generating insights...")
        summary = self.generate_daily_summary(exchanges, target_date)
        
        # Step 4: Store to memory
        print("💾 Storing insights to memory...")
        self.store_insights_to_memory(summary, dry_run)
        
        return summary

def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(description="Run nightly reflection on conversation data")
    parser.add_argument("--date", type=str, help="Date to analyze (YYYY-MM-DD). Default: yesterday")
    parser.add_argument("--dry-run", action="store_true", help="Print insights without storing them")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    # Parse target date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("❌ Invalid date format. Use YYYY-MM-DD")
            return 1
    else:
        target_date = date.today() - timedelta(days=1)
    
    try:
        # Initialize reflection engine
        engine = ReflectionEngine()
        
        # Run reflection
        summary = engine.run_reflection(target_date, args.dry_run)
        
        if args.verbose:
            print("\n" + "="*50)
            print("REFLECTION SUMMARY")
            print("="*50)
            print(f"Date: {summary['date']}")
            print(f"Total Exchanges: {summary.get('total_exchanges', 0)}")
            print(f"\nSummary: {summary['summary']}")
            
            if summary.get('key_topics'):
                print("\nKey Topics:")
                for topic in summary['key_topics']:
                    print(f"  • {topic}")
            
            if summary.get('lessons_learned'):
                print("\nLessons Learned:")
                for lesson in summary['lessons_learned']:
                    print(f"  • {lesson}")
            
            if summary.get('improvement_suggestions'):
                print("\nImprovement Suggestions:")
                for suggestion in summary['improvement_suggestions']:
                    print(f"  • {suggestion}")
        
        print(f"\n✅ Reflection completed for {target_date.strftime('%Y-%m-%d')}")
        return 0
        
    except Exception as e:
        print(f"❌ Error during reflection: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 
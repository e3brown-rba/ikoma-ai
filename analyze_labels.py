#!/usr/bin/env python3
"""
Label Analysis Tool for iKOMA
Analyzes exported GitHub labels and compares with proposed Phase 1B labels.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Set, Tuple

def get_proposed_labels() -> Dict[str, str]:
    """Get the labels we proposed in our templates."""
    return {
        # Priority labels
        'critical': 'System-breaking issues',
        'high': 'Major functionality affected', 
        'medium': 'Moderate impact',
        'low': 'Minor issues or improvements',
        
        # Platform labels
        'platform:windows': 'Windows-specific issues',
        'platform:macos': 'macOS-specific issues',
        'platform:linux': 'Linux-specific issues',
        'cross-platform': 'Affects all platforms',
        
        # Status labels
        'needs-triage': 'New issue, needs review',
        'in-progress': 'Being worked on',
        'blocked': 'Waiting for dependencies',
        'ready-for-review': 'Ready for PR review',
        'wont-fix': 'Issue will not be addressed',
        
        # Component labels
        'agent': 'Core agent functionality',
        'memory': 'Memory/vector store issues',
        'tools': 'Tool system issues',
        'setup': 'Installation/setup issues',
        'ui/ux': 'User interface issues',
        
        # Template labels (already in templates)
        'bug': 'Bug reports',
        'enhancement': 'Feature requests',
        'platform': 'Platform-specific issues'
    }

def load_existing_labels(filename: str = "existing_labels.json") -> List[Dict]:
    """Load existing labels from JSON file."""
    if not os.path.exists(filename):
        print(f"❌ File not found: {filename}")
        print("Run ./export_labels.sh first to export labels from GitHub")
        return []
    
    try:
        with open(filename, 'r') as f:
            labels = json.load(f)
        return labels
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing JSON file: {e}")
        return []

def categorize_existing_labels(labels: List[Dict]) -> Dict[str, List[Dict]]:
    """Categorize existing labels by type."""
    categories = {
        'Priority': [],
        'Status': [],
        'Type': [],
        'Platform': [],
        'Component': [],
        'Other': []
    }
    
    for label in labels:
        name = label['name'].lower()
        
        # Priority/Severity
        if any(word in name for word in ['critical', 'high', 'medium', 'low', 'urgent', 'important', 'minor', 'trivial', 'priority']):
            categories['Priority'].append(label)
        # Status/Workflow
        elif any(word in name for word in ['open', 'closed', 'pending', 'resolved', 'in-progress', 'blocked', 'review', 'status', 'triage']):
            categories['Status'].append(label)
        # Type/Category
        elif any(word in name for word in ['bug', 'feature', 'enhancement', 'documentation', 'security', 'type']):
            categories['Type'].append(label)
        # Platform
        elif any(word in name for word in ['windows', 'mac', 'linux', 'platform', 'cross']):
            categories['Platform'].append(label)
        # Component/Area
        elif any(word in name for word in ['agent', 'memory', 'tools', 'setup', 'ui', 'ux', 'frontend', 'backend', 'api', 'database', 'component']):
            categories['Component'].append(label)
        else:
            categories['Other'].append(label)
    
    return categories

def find_similar_labels(existing_labels: List[Dict], proposed_labels: Dict[str, str]) -> Dict[str, List[Tuple[str, float]]]:
    """Find similar labels between existing and proposed."""
    similarities = {}
    
    for proposed_name, proposed_desc in proposed_labels.items():
        similar = []
        proposed_words = set(proposed_name.lower().replace(':', ' ').replace('-', ' ').split())
        
        for existing_label in existing_labels:
            existing_name = existing_label['name'].lower()
            existing_words = set(existing_name.replace(':', ' ').replace('-', ' ').split())
            
            # Calculate similarity
            intersection = len(proposed_words.intersection(existing_words))
            union = len(proposed_words.union(existing_words))
            similarity = intersection / union if union > 0 else 0
            
            if similarity > 0.2:  # Threshold for similarity
                similar.append((existing_label['name'], similarity))
        
        # Sort by similarity
        similar.sort(key=lambda x: x[1], reverse=True)
        similarities[proposed_name] = similar
    
    return similarities

def generate_analysis_report(existing_labels: List[Dict], proposed_labels: Dict[str, str]):
    """Generate a comprehensive analysis report."""
    print("iKOMA Label Analysis Report")
    print("=" * 60)
    
    # Basic stats
    print(f"\n📊 Basic Statistics:")
    print(f"  Existing Labels: {len(existing_labels)}")
    print(f"  Proposed Labels: {len(proposed_labels)}")
    
    # Categorize existing labels
    categories = categorize_existing_labels(existing_labels)
    
    print(f"\n📂 Existing Labels by Category:")
    for category, labels in categories.items():
        if labels:
            print(f"  {category}: {len(labels)} labels")
            for label in sorted(labels, key=lambda x: x['name']):
                print(f"    • {label['name']} (#{label['color']})")
    
    # Find similarities
    similarities = find_similar_labels(existing_labels, proposed_labels)
    
    print(f"\n🔍 Similarity Analysis:")
    print(f"  Proposed labels with potential matches:")
    
    exact_matches = []
    similar_matches = []
    no_matches = []
    
    for proposed_name, similar_list in similarities.items():
        if similar_list and similar_list[0][1] > 0.8:  # High similarity
            exact_matches.append((proposed_name, similar_list[0][0]))
        elif similar_list:
            similar_matches.append((proposed_name, similar_list[0][0], similar_list[0][1]))
        else:
            no_matches.append(proposed_name)
    
    if exact_matches:
        print(f"\n  ✅ Exact/High Similarity Matches:")
        for proposed, existing in exact_matches:
            print(f"    • {proposed} → {existing}")
    
    if similar_matches:
        print(f"\n  ⚠️  Similar Matches:")
        for proposed, existing, similarity in similar_matches:
            print(f"    • {proposed} → {existing} (similarity: {similarity:.2f})")
    
    if no_matches:
        print(f"\n  ❌ No Similar Matches (need to create):")
        for proposed in no_matches:
            print(f"    • {proposed}")
    
    # Generate recommendations
    print(f"\n💡 Recommendations:")
    
    if exact_matches:
        print(f"  1. Use existing labels for exact matches")
    
    if similar_matches:
        print(f"  2. Consider using existing labels for similar matches")
        print(f"     Or create new labels if existing ones don't fit well")
    
    if no_matches:
        print(f"  3. Create new labels for missing essential ones")
    
    print(f"  4. Focus on Phase 1B essential labels first:")
    essential_labels = ['critical', 'high', 'medium', 'low', 'platform:macos', 'platform:windows', 'needs-triage', 'in-progress', 'agent', 'memory', 'tools', 'setup']
    for label in essential_labels:
        if label in no_matches:
            print(f"     • {label} - {proposed_labels.get(label, 'No description')}")
    
    # Save detailed report
    report_file = "label_analysis_report.md"
    with open(report_file, 'w') as f:
        f.write("# iKOMA Label Analysis Report\n\n")
        f.write(f"Generated: {os.popen('date').read().strip()}\n")
        f.write(f"Existing Labels: {len(existing_labels)}\n")
        f.write(f"Proposed Labels: {len(proposed_labels)}\n\n")
        
        f.write("## Existing Labels by Category\n\n")
        for category, labels in categories.items():
            if labels:
                f.write(f"### {category} ({len(labels)})\n\n")
                for label in sorted(labels, key=lambda x: x['name']):
                    f.write(f"- **{label['name']}** (#{label['color']})")
                    if label.get('description'):
                        f.write(f" - {label['description']}")
                    f.write("\n")
                f.write("\n")
        
        f.write("## Similarity Analysis\n\n")
        f.write("### Exact Matches\n\n")
        for proposed, existing in exact_matches:
            f.write(f"- `{proposed}` → `{existing}`\n")
        
        f.write("\n### Similar Matches\n\n")
        for proposed, existing, similarity in similar_matches:
            f.write(f"- `{proposed}` → `{existing}` (similarity: {similarity:.2f})\n")
        
        f.write("\n### Missing Labels\n\n")
        for proposed in no_matches:
            f.write(f"- `{proposed}` - {proposed_labels.get(proposed, 'No description')}\n")
        
        f.write("\n## Action Plan\n\n")
        f.write("1. **Use existing labels** for exact matches\n")
        f.write("2. **Evaluate similar labels** for potential reuse\n")
        f.write("3. **Create missing essential labels** for Phase 1B\n")
        f.write("4. **Update issue templates** to use final label set\n")
    
    print(f"\n📝 Detailed report saved to: {report_file}")

def main():
    print("iKOMA Label Analysis Tool")
    print("=" * 60)
    
    # Load existing labels
    existing_labels = load_existing_labels()
    if not existing_labels:
        return
    
    # Get proposed labels
    proposed_labels = get_proposed_labels()
    
    # Generate analysis
    generate_analysis_report(existing_labels, proposed_labels)
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Review the analysis report")
    print(f"2. Make decisions on label reuse vs. creation")
    print(f"3. Update issue templates with final label set")
    print(f"4. Test the labeling system with sample issues")

if __name__ == "__main__":
    main() 
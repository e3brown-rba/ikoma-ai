#!/usr/bin/env python3
"""
Script to check existing GitHub labels in the repository.
Run this to see what labels already exist before creating new ones.
"""

import requests
import json
import os
from pathlib import Path

def get_repo_info():
    """Extract repository information from git remote."""
    import subprocess
    try:
        result = subprocess.run(['git', 'remote', 'get-url', 'origin'], 
                              capture_output=True, text=True, check=True)
        remote_url = result.stdout.strip()
        
        # Parse GitHub URL
        if 'github.com' in remote_url:
            # Handle both HTTPS and SSH URLs
            if remote_url.startswith('https://'):
                parts = remote_url.replace('https://github.com/', '').replace('.git', '').split('/')
            else:
                parts = remote_url.replace('git@github.com:', '').replace('.git', '').split('/')
            
            if len(parts) == 2:
                return parts[0], parts[1]
    except Exception as e:
        print(f"Error getting repo info: {e}")
    
    return None, None

def check_labels(owner, repo, token=None):
    """Check existing labels in the repository."""
    url = f"https://api.github.com/repos/{owner}/{repo}/labels"
    
    headers = {
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'iKOMA-Label-Checker'
    }
    
    if token:
        headers['Authorization'] = f'token {token}'
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        labels = response.json()
        
        print(f"Found {len(labels)} existing labels in {owner}/{repo}:")
        print("=" * 60)
        
        # Group labels by category
        categories = {
            'Priority': [],
            'Platform': [],
            'Status': [],
            'Component': [],
            'Other': []
        }
        
        for label in labels:
            name = label['name']
            color = label['color']
            description = label.get('description', '')
            
            # Categorize labels
            if any(word in name.lower() for word in ['critical', 'high', 'medium', 'low', 'priority']):
                categories['Priority'].append((name, color, description))
            elif any(word in name.lower() for word in ['platform', 'windows', 'macos', 'linux', 'cross']):
                categories['Platform'].append((name, color, description))
            elif any(word in name.lower() for word in ['status', 'progress', 'blocked', 'review', 'fix']):
                categories['Status'].append((name, color, description))
            elif any(word in name.lower() for word in ['agent', 'memory', 'tools', 'setup', 'ui', 'ux']):
                categories['Component'].append((name, color, description))
            else:
                categories['Other'].append((name, color, description))
        
        # Print categorized labels
        for category, labels_list in categories.items():
            if labels_list:
                print(f"\n{category} Labels ({len(labels_list)}):")
                print("-" * 40)
                for name, color, description in sorted(labels_list):
                    print(f"  • {name} (#{color})")
                    if description:
                        print(f"    {description}")
        
        # Check for duplicates with our proposed labels
        proposed_labels = {
            'critical', 'high', 'medium', 'low',
            'platform:windows', 'platform:macos', 'platform:linux', 'cross-platform',
            'needs-triage', 'in-progress', 'blocked', 'ready-for-review', 'wont-fix',
            'agent', 'memory', 'tools', 'setup', 'ui/ux'
        }
        
        existing_names = {label['name'] for label in labels}
        duplicates = proposed_labels.intersection(existing_names)
        missing = proposed_labels - existing_names
        
        print(f"\n" + "=" * 60)
        print("LABEL ANALYSIS:")
        print("=" * 60)
        
        if duplicates:
            print(f"\n⚠️  DUPLICATE LABELS (already exist):")
            for label in sorted(duplicates):
                print(f"  • {label}")
        
        if missing:
            print(f"\n✅ MISSING LABELS (need to create):")
            for label in sorted(missing):
                print(f"  • {label}")
        
        if not duplicates and not missing:
            print("\n✅ All proposed labels are new and can be created.")
        
        return labels
        
    except requests.exceptions.RequestException as e:
        print(f"Error accessing GitHub API: {e}")
        print("\nTo use this script with authentication:")
        print("1. Create a GitHub Personal Access Token")
        print("2. Set environment variable: export GITHUB_TOKEN=your_token")
        print("3. Run this script again")
        return None

def main():
    print("iKOMA Label Checker")
    print("=" * 60)
    
    owner, repo = get_repo_info()
    if not owner or not repo:
        print("❌ Could not determine repository information from git remote.")
        print("Make sure you're in the correct repository directory.")
        return
    
    print(f"Repository: {owner}/{repo}")
    
    # Check for GitHub token
    token = os.environ.get('GITHUB_TOKEN')
    if not token:
        print("\n⚠️  No GitHub token found. Using unauthenticated request (rate limited).")
        print("For better results, set GITHUB_TOKEN environment variable.")
    
    labels = check_labels(owner, repo, token)
    
    if labels:
        print(f"\n📊 SUMMARY:")
        print(f"Total existing labels: {len(labels)}")
        print(f"Repository: {owner}/{repo}")
        
        # Save labels to file for reference
        output_file = "existing_labels.json"
        with open(output_file, 'w') as f:
            json.dump(labels, f, indent=2)
        print(f"\n💾 Labels saved to: {output_file}")

if __name__ == "__main__":
    main() 
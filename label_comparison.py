#!/usr/bin/env python3
"""
Label comparison tool for iKOMA repository.
This script helps you compare existing labels with proposed new labels.
"""

def get_proposed_labels():
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

def main():
    print("iKOMA Label Comparison Tool")
    print("=" * 60)
    
    proposed_labels = get_proposed_labels()
    
    print(f"Proposed labels ({len(proposed_labels)}):")
    print("-" * 40)
    
    # Group by category
    categories = {
        'Priority': ['critical', 'high', 'medium', 'low'],
        'Platform': ['platform:windows', 'platform:macos', 'platform:linux', 'cross-platform'],
        'Status': ['needs-triage', 'in-progress', 'blocked', 'ready-for-review', 'wont-fix'],
        'Component': ['agent', 'memory', 'tools', 'setup', 'ui/ux'],
        'Template': ['bug', 'enhancement', 'platform']
    }
    
    for category, labels in categories.items():
        print(f"\n{category} Labels:")
        for label in labels:
            description = proposed_labels.get(label, '')
            print(f"  • {label}")
            if description:
                print(f"    {description}")
    
    print(f"\n" + "=" * 60)
    print("INSTRUCTIONS:")
    print("=" * 60)
    
    print("\n1. Go to your GitHub repository: https://github.com/e3brown-rba/ikoma-ai")
    print("2. Click on 'Issues' tab")
    print("3. Click on 'Labels' (on the right sidebar)")
    print("4. You'll see all existing labels")
    
    print("\n5. Compare with the proposed labels above:")
    print("   - If a label already exists, you can use it")
    print("   - If a label doesn't exist, you can create it")
    print("   - If you have similar labels, consider using existing ones")
    
    print("\n6. For each proposed label, check if you have:")
    print("   - Exact match (use existing)")
    print("   - Similar label (consider using existing or creating new)")
    print("   - No match (create new)")
    
    print("\n7. Common existing labels to look for:")
    print("   - Priority: 'urgent', 'important', 'minor', 'trivial'")
    print("   - Status: 'open', 'closed', 'pending', 'resolved'")
    print("   - Type: 'bug', 'feature', 'documentation', 'enhancement'")
    print("   - Platform: 'windows', 'mac', 'linux', 'cross-platform'")
    
    print("\n8. When creating new labels, use these colors:")
    print("   - Priority: Red (#d73a4a), Orange (#fbca04), Blue (#0075ca), Gray (#6f42c1)")
    print("   - Platform: Green (#28a745), Purple (#6f42c1), Blue (#0366d6)")
    print("   - Status: Yellow (#fbca04), Red (#d73a4a), Green (#28a745)")
    print("   - Component: Blue (#0366d6), Purple (#6f42c1), Orange (#fbca04)")
    
    # Create a checklist file
    with open('label_checklist.md', 'w') as f:
        f.write("# Label Checklist\n\n")
        f.write("Use this checklist to review and create labels:\n\n")
        
        for category, labels in categories.items():
            f.write(f"## {category} Labels\n\n")
            for label in labels:
                description = proposed_labels.get(label, '')
                f.write(f"- [ ] **{label}**")
                if description:
                    f.write(f" - {description}")
                f.write("\n")
            f.write("\n")
        
        f.write("## Action Items\n\n")
        f.write("- [ ] Review existing labels in GitHub\n")
        f.write("- [ ] Identify duplicates/similar labels\n")
        f.write("- [ ] Create missing labels\n")
        f.write("- [ ] Update issue templates if needed\n")
        f.write("- [ ] Test issue creation with new labels\n")
    
    print(f"\n📝 Checklist saved to: label_checklist.md")
    print("\n💡 TIP: Start with the most important labels first:")
    print("   1. Priority labels (critical, high, medium, low)")
    print("   2. Platform labels (platform:macos, platform:windows)")
    print("   3. Status labels (needs-triage, in-progress)")
    print("   4. Component labels (agent, memory, tools)")

if __name__ == "__main__":
    main() 
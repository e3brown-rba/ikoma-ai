# Label Management Guide for iKOMA

## Current Situation
You have **50 existing labels** in your repository. We've proposed **21 new labels** for Phase 1B. This guide helps you manage and consolidate them effectively.

## Strategy for Managing 50 Labels

### 1. **Audit Existing Labels**
First, review your existing labels and categorize them:

**Go to GitHub:**
1. Navigate to https://github.com/e3brown-rba/ikoma-ai
2. Click "Issues" tab
3. Click "Labels" in the right sidebar
4. Review all 50 labels

### 2. **Categorize Existing Labels**
Group your existing labels into these categories:

#### **Priority/Severity**
- Look for: `urgent`, `important`, `minor`, `trivial`, `critical`, `high`, `medium`, `low`
- **Action**: Use existing ones or map to our proposed priority labels

#### **Status/Workflow**
- Look for: `open`, `closed`, `pending`, `resolved`, `in-progress`, `blocked`, `review`
- **Action**: Map to our proposed status labels or keep useful existing ones

#### **Type/Category**
- Look for: `bug`, `feature`, `enhancement`, `documentation`, `security`
- **Action**: Use existing ones that match our templates

#### **Platform**
- Look for: `windows`, `mac`, `linux`, `cross-platform`
- **Action**: Map to our proposed platform labels

#### **Component/Area**
- Look for: `frontend`, `backend`, `api`, `database`, `ui`, `ux`
- **Action**: Map to our proposed component labels

### 3. **Consolidation Strategy**

#### **Option A: Minimal Changes (Recommended)**
- Keep most existing labels
- Only add missing essential labels
- Update issue templates to use existing labels where possible

#### **Option B: Full Consolidation**
- Replace existing labels with our proposed set
- Archive unused labels
- Update all existing issues

#### **Option C: Hybrid Approach**
- Keep useful existing labels
- Add missing proposed labels
- Deprecate redundant labels gradually

### 4. **Recommended Approach for Phase 1B**

Since you're between phases and the Windows version was just frozen:

1. **Keep existing labels** that are working well
2. **Add only essential missing labels** for Phase 1B
3. **Map existing labels** to our templates where possible
4. **Avoid breaking changes** to existing issue workflows

### 5. **Essential Labels to Add (if missing)**

#### **Priority (if not exists)**
- `critical` - System-breaking issues
- `high` - Major functionality affected
- `medium` - Moderate impact
- `low` - Minor issues

#### **Platform (if not exists)**
- `platform:macos` - macOS-specific issues
- `platform:windows` - Windows-specific issues
- `cross-platform` - Affects all platforms

#### **Status (if not exists)**
- `needs-triage` - New issue, needs review
- `in-progress` - Being worked on

#### **Component (if not exists)**
- `agent` - Core agent functionality
- `memory` - Memory/vector store issues
- `tools` - Tool system issues
- `setup` - Installation/setup issues

### 6. **Label Mapping Examples**

If you have these existing labels, map them to our templates:

| Existing Label | Map To | Action |
|----------------|--------|--------|
| `urgent` | `critical` | Use existing or create `critical` |
| `important` | `high` | Use existing or create `high` |
| `minor` | `low` | Use existing or create `low` |
| `open` | `needs-triage` | Use existing or create `needs-triage` |
| `in-progress` | `in-progress` | Use existing |
| `bug` | `bug` | Use existing |
| `feature` | `enhancement` | Use existing or create `enhancement` |
| `windows` | `platform:windows` | Use existing or create `platform:windows` |
| `mac` | `platform:macos` | Use existing or create `platform:macos` |

### 7. **Implementation Steps**

#### **Step 1: Audit (5 minutes)**
1. Go to GitHub labels page
2. Note down existing labels by category
3. Identify gaps with our proposed labels

#### **Step 2: Plan (5 minutes)**
1. Decide which existing labels to keep
2. Identify which new labels to add
3. Plan any label renames/mappings

#### **Step 3: Execute (10 minutes)**
1. Add missing essential labels
2. Update issue templates if needed
3. Test with a sample issue

#### **Step 4: Document (5 minutes)**
1. Update `ISSUE_GUIDELINES.md` with final label set
2. Document any label mappings
3. Update team on new labeling system

### 8. **Quick Decision Matrix**

| Scenario | Action |
|----------|--------|
| Exact match exists | Use existing label |
| Similar label exists | Use existing or create new |
| No match exists | Create new label |
| Too many similar labels | Consolidate to most useful |
| Unused labels | Archive/delete |

### 9. **Color Scheme for New Labels**

When creating new labels, use these colors:

- **Priority**: Red (#d73a4a), Orange (#fbca04), Blue (#0075ca), Gray (#6f42c1)
- **Platform**: Green (#28a745), Purple (#6f42c1), Blue (#0366d6)
- **Status**: Yellow (#fbca04), Red (#d73a4a), Green (#28a745)
- **Component**: Blue (#0366d6), Purple (#6f42c1), Orange (#fbca04)

### 10. **Next Steps**

1. **Run the audit** using the checklist in `label_checklist.md`
2. **Make decisions** on which labels to keep/add
3. **Implement changes** in GitHub
4. **Update documentation** with final label set
5. **Test the system** with sample issues

This approach will help you manage your 50 existing labels while adding the essential ones for Phase 1B without disrupting your current workflow. 
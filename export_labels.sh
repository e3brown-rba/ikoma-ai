#!/bin/bash

# GitHub Label Export Script for iKOMA
# This script exports all labels from a GitHub repository to a JSON file

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get repository information from git
get_repo_info() {
    local remote_url=$(git remote get-url origin 2>/dev/null || echo "")
    
    if [[ -z "$remote_url" ]]; then
        print_error "Could not get git remote URL. Make sure you're in a git repository."
        exit 1
    fi
    
    # Parse GitHub URL
    if [[ $remote_url =~ github\.com ]]; then
        if [[ $remote_url =~ https://github\.com/([^/]+)/([^/]+)\.git ]]; then
            echo "${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
        elif [[ $remote_url =~ git@github\.com:([^/]+)/([^/]+)\.git ]]; then
            echo "${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
        else
            print_error "Could not parse GitHub URL: $remote_url"
            exit 1
        fi
    else
        print_error "Not a GitHub repository: $remote_url"
        exit 1
    fi
}

# Check if required tools are installed
check_dependencies() {
    local missing_tools=()
    
    if ! command -v curl &> /dev/null; then
        missing_tools+=("curl")
    fi
    
    if ! command -v jq &> /dev/null; then
        missing_tools+=("jq")
    fi
    
    if [[ ${#missing_tools[@]} -gt 0 ]]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        echo ""
        echo "Install missing tools:"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "  brew install ${missing_tools[*]}"
        else
            echo "  sudo apt-get install ${missing_tools[*]}  # Ubuntu/Debian"
            echo "  sudo yum install ${missing_tools[*]}      # CentOS/RHEL"
        fi
        exit 1
    fi
}

# Main function
main() {
    echo "GitHub Label Export Tool"
    echo "========================"
    
    # Check dependencies
    print_status "Checking dependencies..."
    check_dependencies
    print_success "All dependencies found"
    
    # Get repository info
    print_status "Getting repository information..."
    local repo_info=$(get_repo_info)
    local owner=$(echo "$repo_info" | cut -d'/' -f1)
    local repo=$(echo "$repo_info" | cut -d'/' -f2)
    print_success "Repository: $owner/$repo"
    
    # Check for GitHub token
    local token=""
    if [[ -n "$GITHUB_TOKEN" ]]; then
        token="$GITHUB_TOKEN"
        print_success "Using GitHub token from environment"
    else
        print_warning "No GITHUB_TOKEN environment variable found"
        echo ""
        echo "To use authentication (recommended):"
        echo "1. Create a GitHub Personal Access Token"
        echo "2. Set environment variable: export GITHUB_TOKEN=your_token"
        echo "3. Run this script again"
        echo ""
        echo "Continuing without authentication (rate limited)..."
    fi
    
    # Set up headers
    local headers=("Accept: application/vnd.github.v3+json")
    if [[ -n "$token" ]]; then
        headers+=("Authorization: Bearer $token")
    fi
    
    # Build curl command as array to avoid quote issues
    local curl_cmd=(curl --silent)
    for header in "${headers[@]}"; do
        curl_cmd+=( -H "$header" )
    done
    
    # Fetch labels
    print_status "Fetching labels from GitHub..."
    local api_url="https://api.github.com/repos/$owner/$repo/labels?per_page=100"
    local labels_json
    
    if labels_json=$(${curl_cmd[@]} "$api_url" 2>/dev/null); then
        # Check if we got a valid JSON response
        if echo "$labels_json" | jq empty 2>/dev/null; then
            # Check for error responses
            if echo "$labels_json" | jq -e '.message' >/dev/null 2>&1; then
                local error_msg=$(echo "$labels_json" | jq -r '.message')
                print_error "GitHub API error: $error_msg"
                echo ""
                echo "Possible causes:"
                echo "1. Repository doesn't exist: $owner/$repo"
                echo "2. Repository is private and requires authentication"
                echo "3. Invalid repository name"
                echo ""
                echo "To create the repository:"
                echo "1. Go to https://github.com/new"
                echo "2. Create repository: $repo"
                echo "3. Push your code: git push -u origin main"
                exit 1
            fi
            
            local label_count=$(echo "$labels_json" | jq length)
            print_success "Found $label_count labels"
            
            # Save to file
            local output_file="existing_labels.json"
            echo "$labels_json" | jq '.' > "$output_file"
            print_success "Labels saved to: $output_file"
            
            # Create a summary
            local summary_file="label_summary.md"
            {
                echo "# GitHub Labels Summary"
                echo ""
                echo "Repository: $owner/$repo"
                echo "Total Labels: $label_count"
                echo "Exported: $(date)"
                echo ""
                echo "## Labels by Category"
                echo ""
                
                # Categorize labels
                echo "### Priority/Severity"
                echo "$labels_json" | jq -r '.[] | select(.name | test("critical|high|medium|low|urgent|important|minor|trivial|priority"; "i")) | "- \(.name) (#\(.color))"' | sort
                echo ""
                
                echo "### Status/Workflow"
                echo "$labels_json" | jq -r '.[] | select(.name | test("open|closed|pending|resolved|in-progress|blocked|review|status"; "i")) | "- \(.name) (#\(.color))"' | sort
                echo ""
                
                echo "### Type/Category"
                echo "$labels_json" | jq -r '.[] | select(.name | test("bug|feature|enhancement|documentation|security|type"; "i")) | "- \(.name) (#\(.color))"' | sort
                echo ""
                
                echo "### Platform"
                echo "$labels_json" | jq -r '.[] | select(.name | test("windows|mac|linux|platform|cross"; "i")) | "- \(.name) (#\(.color))"' | sort
                echo ""
                
                echo "### Component/Area"
                echo "$labels_json" | jq -r '.[] | select(.name | test("agent|memory|tools|setup|ui|ux|frontend|backend|api|database|component"; "i")) | "- \(.name) (#\(.color))"' | sort
                echo ""
                
                echo "### Other"
                echo "$labels_json" | jq -r '.[] | select(.name | test("^(?!.*(critical|high|medium|low|urgent|important|minor|trivial|priority|open|closed|pending|resolved|in-progress|blocked|review|status|bug|feature|enhancement|documentation|security|type|windows|mac|linux|platform|cross|agent|memory|tools|setup|ui|ux|frontend|backend|api|database|component)).*$"; "i")) | "- \(.name) (#\(.color))"' | sort
                echo ""
                
                echo "## Full Label List"
                echo ""
                echo "$labels_json" | jq -r '.[] | "- \(.name) (#\(.color)) - \(.description // "No description")"' | sort
                
            } > "$summary_file"
            
            print_success "Summary saved to: $summary_file"
            
            # Show quick stats
            echo ""
            echo "📊 Quick Stats:"
            echo "  Total Labels: $label_count"
            echo "  JSON File: $output_file"
            echo "  Summary: $summary_file"
            echo ""
            echo "Next steps:"
            echo "1. Review $summary_file for categorized labels"
            echo "2. Run: python label_comparison.py"
            echo "3. Follow LABEL_MANAGEMENT.md for consolidation strategy"
            
        else
            print_error "Invalid JSON response from GitHub API"
            echo "Response: $labels_json"
            exit 1
        fi
    else
        print_error "Failed to fetch labels from GitHub API"
        echo ""
        echo "Possible causes:"
        echo "1. Repository doesn't exist or is private"
        echo "2. No authentication token provided"
        echo "3. Network connectivity issues"
        echo "4. Rate limiting (try again later)"
        exit 1
    fi
}

# Run main function
main "$@" 
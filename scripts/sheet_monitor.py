#!/usr/bin/env python3
"""
Google Sheet Monitor for GitHub Issues
Monitors a public Google Sheet for changes in the paper_id column and creates new GitHub issues.
Automatically adds issues to a GitHub Project board.
"""

import os
import json
import requests
from datetime import datetime

class SheetMonitor:
    def __init__(self):
        self.sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.github_repo = os.environ.get('GITHUB_REPOSITORY')
        self.project_number = '6'  # Store project number
        self.project_id = None  # Will be set in run() method
        self.state_file = 'sheet_state.json'
        
    def _get_project_id_by_number(self, project_number):
        """Get the actual project ID from GitHub using project number."""
        try:
            url = "https://api.github.com/graphql"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Content-Type': 'application/json'
            }
            
            # Extract owner and repo from GITHUB_REPOSITORY
            owner, repo = self.github_repo.split('/')
            
            query = """
            query GetProject($owner: String!, $repo: String!, $number: Int!) {
                repository(owner: $owner, name: $repo) {
                    projectV2(number: $number) {
                        id
                        title
                    }
                }
            }
            """
            
            variables = {
                "owner": owner,
                "repo": repo,
                "number": int(project_number)
            }
            
            data = {
                "query": query,
                "variables": variables
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'errors' in result:
                    print(f"⚠️ GraphQL errors getting project: {result['errors']}")
                    return None
                
                project = result['data']['repository']['projectV2']
                if project:
                    print(f"📋 Found project: {project['title']} (ID: {project['id']})")
                    return project['id']
                else:
                    print(f"❌ Project with number {project_number} not found")
                    return None
            else:
                print(f"❌ Failed to get project: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting project ID: {e}")
            return None
        
    def _load_state(self):
        """Load the previous state of processed paper_ids."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
        return {'processed_paper_ids': []}
    
    def _save_state(self, state):
        """Save the current state of processed paper_ids."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def _get_sheet_data(self):
        """Fetch data from public Google Sheet."""
        try:
            # Convert sheet ID to CSV export URL
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv"
            
            response = requests.get(csv_url)
            response.raise_for_status()
            
            # Parse CSV data
            lines = response.text.strip().split('\n')
            if not lines:
                print("No data found in sheet.")
                return []
            
            # Extract paper_ids (skip header row if exists)
            paper_ids = []
            for line in lines[1:]:  # Skip first row if it's a header
                if line.strip():
                    # Split by comma and take the first column (paper_id)
                    columns = line.split(',')
                    if columns and columns[0].strip():
                        paper_id = columns[0].strip().strip('"')  # Remove quotes if present
                        paper_ids.append(paper_id)
            
            return paper_ids
            
        except requests.RequestException as e:
            print(f"Error fetching sheet data: {e}")
            return []
        except Exception as e:
            print(f"Error parsing sheet data: {e}")
            return []
    
    def _create_github_issue(self, paper_id):
        """Create a new GitHub issue for the given paper_id."""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/issues"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            data = {
                'title': f'Paper Review: {paper_id}',
                'body': f'''## Paper Review Request

**Paper ID:** {paper_id}

**Date Added:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

### Tasks
- [ ] Review paper content
- [ ] Analyze methodology
- [ ] Check results and conclusions
- [ ] Prepare review summary

### Notes
This issue was automatically created from Google Sheet monitoring.
''',
                'labels': ['paper-review', 'automated']
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                issue_data = response.json()
                issue_id = issue_data['id']  # Get the issue ID for project board
                issue_number = issue_data['number']
                print(f"✅ Created issue #{issue_number} for paper_id: {paper_id}")
                
                # Add to project board if project ID is configured
                if self.project_id:
                    self._add_issue_to_project(issue_id, paper_id)
                
                return True
            else:
                print(f"❌ Failed to create issue for {paper_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating GitHub issue for {paper_id}: {e}")
            return False
    
    def _add_issue_to_project(self, issue_id, paper_id):
        """Add an issue to the GitHub Project board."""
        try:
            # GitHub GraphQL API endpoint
            url = "https://api.github.com/graphql"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Content-Type': 'application/json'
            }
            
            # GraphQL mutation to add item to project
            query = """
            mutation AddIssueToProject($projectId: ID!, $contentId: ID!) {
                addProjectV2Item(input: {
                    projectId: $projectId
                    contentId: $contentId
                }) {
                    item {
                        id
                        content {
                            ... on Issue {
                                title
                                number
                            }
                        }
                    }
                }
            }
            """
            
            variables = {
                "projectId": self.project_id,
                "contentId": issue_id
            }
            
            data = {
                "query": query,
                "variables": variables
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                print(f"🔍 GraphQL Response: {result}")  # Debug line
                if 'errors' in result:
                    print(f"⚠️ GraphQL errors adding to project: {result['errors']}")
                    # Try alternative approach - create a draft issue
                    self._create_draft_issue_in_project(paper_id, f"Paper Review: {paper_id}")
                else:
                    item_data = result['data']['addProjectV2Item']['item']
                    if item_data and item_data.get('content'):
                        issue_title = item_data['content']['title']
                        issue_number = item_data['content']['number']
                        print(f"✅ Added issue #{issue_number} to project board: '{issue_title}'")
                    else:
                        print(f"✅ Added issue to project board for paper_id: {paper_id}")
            else:
                print(f"❌ Failed to add issue to project: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error adding issue to project: {e}")
    
    def _create_draft_issue_in_project(self, paper_id, issue_title):
        """Create a draft issue in the project as fallback."""
        try:
            url = "https://api.github.com/graphql"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Content-Type': 'application/json'
            }
            
            query = """
            mutation CreateDraftIssue($projectId: ID!, $title: String!) {
                addProjectV2DraftIssue(input: {
                    projectId: $projectId
                    title: $title
                }) {
                    projectItem {
                        id
                    }
                }
            }
            """
            
            # Use the same title format as the actual issue
            # issue_title = f"Paper Review: {paper_id}" # This line is now passed as an argument
            
            variables = {
                "projectId": self.project_id,
                "title": issue_title
            }
            
            data = {
                "query": query,
                "variables": variables
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'errors' in result:
                    print(f"⚠️ GraphQL errors creating draft issue: {result['errors']}")
                else:
                    print(f"✅ Created draft issue in project: '{issue_title}'")
            else:
                print(f"❌ Failed to create draft issue: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error creating draft issue: {e}")
    
    def _check_existing_issues(self, paper_id):
        """Check if an issue already exists for this paper_id."""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/issues"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            params = {
                'state': 'all',
                'labels': 'paper-review',
                'search': f'repo:{self.github_repo} "{paper_id}"'
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                issues = response.json()
                for issue in issues:
                    if paper_id in issue['title']:
                        return True
            return False
            
        except Exception as e:
            print(f"Error checking existing issues: {e}")
            return False
    
    def _validate_environment(self):
        """Validate that all required environment variables are set."""
        missing_vars = []
        
        if not self.sheet_id:
            missing_vars.append('GOOGLE_SHEET_ID')
        
        if not self.github_token:
            missing_vars.append('GITHUB_TOKEN')
            
        if not self.github_repo:
            missing_vars.append('GITHUB_REPOSITORY')
        
        if missing_vars:
            print("❌ Missing required environment variables:")
            for var in missing_vars:
                print(f"   - {var}")
            
            print("\n🔧 Setup Instructions:")
            print("1. For local testing:")
            print(f"   export GOOGLE_SHEET_ID='your_sheet_id'")
            print(f"   export GITHUB_TOKEN='your_personal_access_token'")
            print(f"   export GITHUB_REPOSITORY='your_username/your_repo'")
            print(f"   export PROJECT_ID='your_project_id' (optional)")
            print("\n2. For GitHub Actions:")
            print("   - Add GOOGLE_SHEET_ID as a repository secret")
            print("   - Add PERSONAL_ACCESS_TOKEN as a repository secret")
            print("   - Add PROJECT_ID as a repository secret (optional)")
            print("   - GITHUB_REPOSITORY is automatically set")
            
            return False
        
        return True
    
    def run(self):
        """Main execution method."""
        print(f"🔄 Starting sheet monitor at {datetime.now()}")
        
        # Validate environment
        if not self._validate_environment():
            return
        
        # Get project ID based on the stored project number
        self.project_id = self._get_project_id_by_number(self.project_number)
        
        # Show project board status
        if self.project_id:
            print(f"📋 Project board ID: {self.project_id}")
        else:
            print("ℹ️ No project board configured (GITHUB_PROJECT_ID not set)")
        
        # Load previous state
        state = self._load_state()
        processed_ids = set(state.get('processed_paper_ids', []))
        
        # Get current sheet data
        current_paper_ids = self._get_sheet_data()
        
        if not current_paper_ids:
            print("No paper IDs found in sheet")
            return
        
        print(f"📊 Found {len(current_paper_ids)} paper IDs in sheet")
        
        # Process new paper_ids
        new_issues_created = 0
        for paper_id in current_paper_ids:
            if paper_id not in processed_ids:
                # Check if issue already exists
                if not self._check_existing_issues(paper_id):
                    if self._create_github_issue(paper_id):
                        new_issues_created += 1
                        processed_ids.add(paper_id)
                else:
                    print(f"⚠️ Issue already exists for paper_id: {paper_id}")
                    processed_ids.add(paper_id)
        
        # Save updated state
        state['processed_paper_ids'] = list(processed_ids)
        self._save_state(state)
        
        print(f"✅ Monitoring complete. Created {new_issues_created} new issues.")

if __name__ == "__main__":
    monitor = SheetMonitor()
    monitor.run() 

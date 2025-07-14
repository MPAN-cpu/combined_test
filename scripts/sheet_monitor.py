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
        self.state_file = 'sheet_state.json'
        
        # Define all available statuses with their colors
        self.status_labels = {
            'ready-to-code': {'name': 'Ready to Code', 'color': '0e8a16', 'description': 'Ready for development'},
            'supervisor-check': {'name': 'Supervisor Check', 'color': 'fbca04', 'description': 'Awaiting supervisor review'},
            'done': {'name': 'Done', 'color': '28a745', 'description': 'Task completed'},
            'on-hold': {'name': 'On hold', 'color': 'd93f0b', 'description': 'Temporarily paused'},
            'remove-from-pilot': {'name': 'Remove from Pilot', 'color': 'b60205', 'description': 'Remove from pilot program'}
        }
        
    def _create_status_labels(self):
        """Create all status labels if they don't exist."""
        print("🏷️ Creating status labels...")
        
        for label_id, label_info in self.status_labels.items():
            self._create_label_if_not_exists(label_id, label_info)
    
    def _create_label_if_not_exists(self, label_id, label_info):
        """Create a label if it doesn't already exist."""
        try:
            # First, check if the label already exists
            url = f"https://api.github.com/repos/{self.github_repo}/labels/{label_id}"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                print(f"   ✅ Label '{label_info['name']}' already exists")
                return
            elif response.status_code == 404:
                # Label doesn't exist, create it
                create_url = f"https://api.github.com/repos/{self.github_repo}/labels"
                
                create_data = {
                    'name': label_id,
                    'color': label_info['color'],
                    'description': label_info['description']
                }
                
                create_response = requests.post(create_url, headers=headers, json=create_data)
                
                if create_response.status_code == 201:
                    print(f"   ✅ Created label '{label_info['name']}'")
                else:
                    print(f"   ❌ Failed to create label '{label_info['name']}': {create_response.status_code}")
            else:
                print(f"   ⚠️ Error checking label '{label_info['name']}': {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error with label '{label_info['name']}': {e}")
    
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

**Status:** {self.status_labels['ready-to-code']['name']}

### Tasks
- [ ] Review paper content
- [ ] Analyze methodology
- [ ] Check results and conclusions
- [ ] Prepare review summary

### Notes
This issue was automatically created from Google Sheet monitoring.

**To add to project board:**
1. Go to your project board
2. Click "Add items" 
3. Select "Issues from this repository"
4. Find and select this issue

**Available Statuses:**
- {self.status_labels['ready-to-code']['name']}
- {self.status_labels['supervisor-check']['name']}
- {self.status_labels['done']['name']}
- {self.status_labels['on-hold']['name']}
- {self.status_labels['remove-from-pilot']['name']}
''',
                'labels': ['paper-review', 'automated', 'ready-to-code']
            }
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                issue_data = response.json()
                issue_number = issue_data['number']
                print(f"✅ Created issue #{issue_number} for paper_id: {paper_id}")
                print(f"   📋 To add to project: Go to project → Add items → Issues → Select #{issue_number}")
                return True
            else:
                print(f"❌ Failed to create issue for {paper_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error creating GitHub issue for {paper_id}: {e}")
            return False
    
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
            print("\n2. For GitHub Actions:")
            print("   - Add GOOGLE_SHEET_ID as a repository secret")
            print("   - Add PERSONAL_ACCESS_TOKEN as a repository secret")
            print("   - GITHUB_REPOSITORY is automatically set")
            
            return False
        
        return True
    
    def run(self):
        """Main execution method."""
        print(f"🔄 Starting sheet monitor at {datetime.now()}")
        
        # Validate environment
        if not self._validate_environment():
            return
        
        # Create status labels if they don't exist
        self._create_status_labels()

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

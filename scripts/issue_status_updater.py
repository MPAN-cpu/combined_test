#!/usr/bin/env python3
"""
Issue Status Updater
Updates GitHub issue statuses based on data from Google Sheet.
Expects sheet columns: paper_id, status, reviewer, notes
"""

import os
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional

class IssueStatusUpdater:
    def __init__(self):
        self.sheet_id = os.environ.get('GOOGLE_SHEET_ID')
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.github_repo = os.environ.get('GITHUB_REPOSITORY')
        self.state_file = 'issue_status_state.json'
        
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
        
    def _load_state(self):
        """Load the previous state of issue updates."""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading state: {e}")
        return {'last_updated': {}, 'issue_mapping': {}}
    
    def _save_state(self, state):
        """Save the current state of issue updates."""
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")
    
    def _get_sheet_data(self):
        """Fetch data from public Google Sheet."""
        try:
            csv_url = f"https://docs.google.com/spreadsheets/d/{self.sheet_id}/export?format=csv"
            response = requests.get(csv_url)
            response.raise_for_status()
            
            lines = response.text.strip().split('\n')
            if not lines:
                print("No data found in sheet.")
                return []
            
            # Parse CSV data with multiple columns
            data = []
            for i, line in enumerate(lines[1:], 1):  # Skip header, start from row 2
                if line.strip():
                    columns = [col.strip().strip('"') for col in line.split(',')]
                    if len(columns) >= 4:  # Expect at least 4 columns
                        row_data = {
                            'paper_id': columns[0],
                            'status': columns[1],
                            'reviewer': columns[2],
                            'notes': columns[3] if len(columns) > 3 else ''
                        }
                        data.append(row_data)
            
            return data
            
        except requests.RequestException as e:
            print(f"Error fetching sheet data: {e}")
            return []
        except Exception as e:
            print(f"Error parsing sheet data: {e}")
            return []
    
    def _get_existing_issues(self):
        """Get all existing issues with paper-review label."""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/issues"
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            params = {
                'state': 'all',
                'labels': 'paper-review',
                'per_page': 100
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                issues = response.json()
                issue_mapping = {}
                for issue in issues:
                    # Extract paper_id from title (format: "Paper Review: {paper_id}")
                    title = issue['title']
                    if title.startswith('Paper Review: '):
                        paper_id = title.replace('Paper Review: ', '').strip()
                        issue_mapping[paper_id] = {
                            'number': issue['number'],
                            'title': issue['title'],
                            'state': issue['state'],
                            'labels': [label['name'] for label in issue['labels']],
                            'body': issue['body']
                        }
                return issue_mapping
            else:
                print(f"Failed to fetch issues: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"Error fetching existing issues: {e}")
            return {}
    
    def _update_issue_labels(self, issue_number: int, current_labels: List[str], new_status: str):
        """Update issue labels based on status."""
        try:
            # Define status to label mapping
            status_labels = {
                'pending': 'status-pending',
                'in_progress': 'status-in-progress',
                'reviewing': 'status-reviewing',
                'completed': 'status-completed',
                'rejected': 'status-rejected',
                'approved': 'status-approved'
            }
            
            # Remove old status labels
            status_label_names = list(status_labels.values())
            updated_labels = [label for label in current_labels if label not in status_label_names]
            
            # Add new status label
            if new_status.lower() in status_labels:
                new_label = status_labels[new_status.lower()]
                if new_label not in updated_labels:
                    updated_labels.append(new_label)
            
            # Keep essential labels
            essential_labels = ['paper-review', 'automated']
            for label in essential_labels:
                if label not in updated_labels:
                    updated_labels.append(label)
            
            return updated_labels
            
        except Exception as e:
            print(f"Error updating labels: {e}")
            return current_labels
    
    def _add_status_comment(self, issue_number: int, status: str, reviewer: str, notes: str):
        """Add a comment to the issue with status update."""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/issues/{issue_number}/comments"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            comment_body = f"""## Status Update

**Status:** {status}
**Reviewer:** {reviewer}
**Updated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

"""
            
            if notes.strip():
                comment_body += f"**Notes:** {notes}\n"
            
            data = {'body': comment_body}
            
            response = requests.post(url, headers=headers, json=data)
            
            if response.status_code == 201:
                print(f"✅ Added status comment to issue #{issue_number}")
                return True
            else:
                print(f"❌ Failed to add comment to issue #{issue_number}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error adding comment to issue #{issue_number}: {e}")
            return False
    
    def _update_issue(self, issue_number: int, labels: List[str], status: str, reviewer: str, notes: str):
        """Update an issue with new labels and add a comment."""
        try:
            url = f"https://api.github.com/repos/{self.github_repo}/issues/{issue_number}"
            
            headers = {
                'Authorization': f'token {self.github_token}',
                'Accept': 'application/vnd.github.v3+json',
                'Content-Type': 'application/json'
            }
            
            # Update labels
            data = {'labels': labels}
            
            response = requests.patch(url, headers=headers, json=data)
            
            if response.status_code == 200:
                print(f"✅ Updated labels for issue #{issue_number}")
                
                # Add status comment
                self._add_status_comment(issue_number, status, reviewer, notes)
                return True
            else:
                print(f"❌ Failed to update issue #{issue_number}: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Error updating issue #{issue_number}: {e}")
            return False
    
    def _create_status_labels(self):
        """Create status labels if they don't exist."""
        status_labels = {
            'status-pending': 'FFA500',      # Orange
            'status-in-progress': '0366d6',  # Blue
            'status-reviewing': '6f42c1',    # Purple
            'status-completed': '28a745',    # Green
            'status-rejected': 'd73a4a',     # Red
            'status-approved': '28a745'      # Green
        }
        
        for label_name, color in status_labels.items():
            try:
                url = f"https://api.github.com/repos/{self.github_repo}/labels"
                
                headers = {
                    'Authorization': f'token {self.github_token}',
                    'Accept': 'application/vnd.github.v3+json',
                    'Content-Type': 'application/json'
                }
                
                data = {
                    'name': label_name,
                    'color': color,
                    'description': f'Status: {label_name.replace("status-", "").replace("_", " ").title()}'
                }
                
                response = requests.post(url, headers=headers, json=data)
                
                if response.status_code == 201:
                    print(f"✅ Created label: {label_name}")
                elif response.status_code == 422:
                    print(f"ℹ️ Label already exists: {label_name}")
                else:
                    print(f"⚠️ Could not create label {label_name}: {response.status_code}")
                    
            except Exception as e:
                print(f"Error creating label {label_name}: {e}")
    
    def run(self):
        """Main execution method."""
        print(f"🔄 Starting issue status updater at {datetime.now()}")
        
        # Validate environment
        if not self._validate_environment():
            return
        
        # Create status labels
        print("🏷️ Creating status labels...")
        self._create_status_labels()
        
        # Load previous state
        state = self._load_state()
        last_updated = state.get('last_updated', {})
        
        # Get current sheet data
        sheet_data = self._get_sheet_data()
        
        if not sheet_data:
            print("No data found in sheet")
            return
        
        print(f"📊 Found {len(sheet_data)} rows in sheet")
        
        # Get existing issues
        issue_mapping = self._get_existing_issues()
        print(f"📋 Found {len(issue_mapping)} existing issues")
        
        # Process updates
        updates_made = 0
        for row in sheet_data:
            paper_id = row['paper_id']
            status = row['status']
            reviewer = row['reviewer']
            notes = row['notes']
            
            if paper_id in issue_mapping:
                issue = issue_mapping[paper_id]
                issue_number = issue['number']
                
                # Check if update is needed
                last_update = last_updated.get(paper_id, '')
                current_data = f"{status}|{reviewer}|{notes}"
                
                if current_data != last_update:
                    # Update labels
                    new_labels = self._update_issue_labels(issue_number, issue['labels'], status)
                    
                    # Update issue
                    if self._update_issue(issue_number, new_labels, status, reviewer, notes):
                        last_updated[paper_id] = current_data
                        updates_made += 1
                else:
                    print(f"ℹ️ No changes for paper_id: {paper_id}")
            else:
                print(f"⚠️ No issue found for paper_id: {paper_id}")
        
        # Save updated state
        state['last_updated'] = last_updated
        self._save_state(state)
        
        print(f"✅ Status update complete. Updated {updates_made} issues.")

if __name__ == "__main__":
    updater = IssueStatusUpdater()
    updater.run() 

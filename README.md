# Google Sheets to GitHub Issues Automation

This GitHub Action automatically monitors a **public** Google Sheet for changes in the "paper_id" column and creates new GitHub issues for each unique paper ID. It also includes a status updater that keeps issue statuses synchronized with your Google Sheet.

## Features

- 🔄 **Automated Monitoring**: Runs every 5 minutes via GitHub Actions
- 📊 **Public Google Sheets Integration**: Reads data from your public Google Sheet
- 🎯 **Smart Issue Creation**: Creates GitHub issues with structured templates
- 🔍 **Duplicate Prevention**: Checks for existing issues before creating new ones
- 📝 **State Management**: Tracks processed paper IDs to avoid duplicates
- 🔓 **No Authentication Required**: Works with public sheets without API keys
- 🏷️ **Status Synchronization**: Updates issue labels and comments based on sheet data
- 📋 **Review Tracking**: Tracks reviewers, status, and notes for each paper

## Workflows

### 1. Sheet Monitor (Creates Issues)
- **File**: `.github/workflows/sheet-monitor.yml`
- **Frequency**: Every 5 minutes
- **Purpose**: Creates new GitHub issues for new paper IDs

### 2. Issue Status Updater (Updates Issues)
- **File**: `.github/workflows/issue-status-updater.yml`
- **Frequency**: Every 10 minutes
- **Purpose**: Updates existing issues with status, reviewer, and notes

## Setup Instructions

### 1. Google Sheets Setup

1. **Make Your Sheet Public**:
   - Open your Google Sheet
   - Click "Share" in the top right
   - Click "Change to anyone with the link"
   - Set permissions to "Viewer"
   - Copy the sharing link

2. **Prepare Your Sheet Structure**:
   The sheet should have these columns:
   
   | paper_id | status      | reviewer | notes                    |
   |----------|-------------|----------|--------------------------|
   | P1       | pending     | John     | Waiting for assignment   |
   | P2       | in_progress | Alice    | Currently reviewing      |
   | P3       | reviewing   | Bob      | Final review stage       |
   | P4       | completed   | Carol    | Review finished          |
   | P5       | rejected    | David    | Does not meet criteria   |

   **Column Descriptions**:
   - `paper_id`: Unique identifier (must match issue titles)
   - `status`: Current status (pending, in_progress, reviewing, completed, rejected, approved)
   - `reviewer`: Name of the person assigned to review
   - `notes`: Additional notes or comments

3. **Get Your Sheet ID**:
   - From your sharing link: `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit`
   - Copy the `YOUR_SHEET_ID_HERE` part

### 2. GitHub Repository Setup

1. **Add Repository Secrets**:
   Go to your repository → Settings → Secrets and variables → Actions, and add:

   - `GOOGLE_SHEET_ID`: Your Google Sheet ID (from the URL)
   - `PERSONAL_ACCESS_TOKEN`: Your GitHub personal access token with `repo` permissions

2. **Create Personal Access Token**:
   - Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   - Click "Generate new token (classic)"
   - Give it a name like "Sheet Monitor"
   - Select scopes: `repo` (full control of private repositories)
   - Copy the generated token

3. **Create Labels** (Optional):
   The action creates issues with labels `paper-review` and `automated`. Status labels are created automatically:
   - `status-pending` (Orange)
   - `status-in-progress` (Blue)
   - `status-reviewing` (Purple)
   - `status-completed` (Green)
   - `status-rejected` (Red)
   - `status-approved` (Green)

### 3. Customization

#### Adjust Sheet Columns
If your columns are in different positions, modify the parsing in the scripts:

**For Issue Creation** (`scripts/sheet_monitor.py`):
```python
# Change the column index (0 = first column, 1 = second column, etc.)
columns = line.split(',')
if columns and columns[0].strip():  # Change [0] to [1] for second column
    paper_id = columns[0].strip().strip('"')
```

**For Status Updates** (`scripts/issue_status_updater.py`):
```python
# Adjust column positions as needed
row_data = {
    'paper_id': columns[0],    # Change index as needed
    'status': columns[1],      # Change index as needed
    'reviewer': columns[2],    # Change index as needed
    'notes': columns[3]        # Change index as needed
}
```

#### Modify Issue Template
Edit the issue template in the `_create_github_issue` method in `scripts/sheet_monitor.py`.

#### Change Monitoring Frequency
Modify the cron schedules in the workflow files:

```yaml
# In sheet-monitor.yml
schedule:
  - cron: '*/5 * * * *'  # Every 5 minutes

# In issue-status-updater.yml  
schedule:
  - cron: '*/10 * * * *'  # Every 10 minutes
```

## How It Works

### Issue Creation Process
1. **Scheduled Execution**: Runs every 5 minutes
2. **Sheet Reading**: Fetches data from your public Google Sheet using CSV export
3. **State Check**: Compares current paper IDs with previously processed ones
4. **Duplicate Prevention**: Checks if an issue already exists for each paper ID
5. **Issue Creation**: Creates new GitHub issues with structured templates
6. **State Update**: Saves the list of processed paper IDs

### Status Update Process
1. **Scheduled Execution**: Runs every 10 minutes
2. **Sheet Reading**: Fetches status data from your Google Sheet
3. **Issue Mapping**: Finds existing issues by paper ID
4. **Status Comparison**: Checks if status has changed since last update
5. **Label Updates**: Updates issue labels based on new status
6. **Comment Addition**: Adds status update comments to issues
7. **State Tracking**: Saves update state to avoid duplicates

## Issue Template

Each created issue includes:
- **Title**: "Paper Review: {paper_id}"
- **Labels**: `paper-review`, `automated`, `status-{status}`
- **Body**: Structured template with tasks and metadata

## Status Updates

When you update the status in your Google Sheet, the system will:
- ✅ Update issue labels (e.g., `status-in-progress`)
- ✅ Add a status update comment with reviewer and notes
- ✅ Track changes to avoid duplicate updates

## Testing

### Test Sheet Connection
```bash
python test_sheet_connection.py
```

### Test Status Updater
```bash
python test_status_updater.py
```

### Manual Workflow Trigger
1. Go to Actions tab in your repository
2. Select either workflow
3. Click "Run workflow"

## Troubleshooting

### Common Issues

1. **"No data found in sheet"**:
   - Ensure your sheet is public and accessible
   - Check that the sheet ID is correct
   - Verify the sheet has data in the expected columns

2. **"Failed to create issue"**:
   - Verify `PERSONAL_ACCESS_TOKEN` has issue creation permissions
   - Check repository permissions

3. **"Error fetching sheet data"**:
   - Make sure your sheet is public
   - Check the sheet ID format

4. **"No issue found for paper_id"**:
   - Ensure the paper_id in the sheet matches the issue title format
   - Check that the issue was created by the first workflow

### Logs

Check the workflow logs in the Actions tab to see detailed execution information and any error messages.

## Security Notes

- No authentication required for public sheets
- The action only reads your sheet and creates/updates issues
- No sensitive data is stored or transmitted
- Personal access token should have minimal required permissions

## Contributing

Feel free to submit issues and enhancement requests! 

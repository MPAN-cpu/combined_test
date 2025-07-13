#!/usr/bin/env python3
"""
Test script for the Issue Status Updater
Shows the expected Google Sheet structure and tests the updater
"""

import requests
import os

def test_status_updater(sheet_id):
    """Test the status updater functionality."""
    print(f"🔍 Testing status updater with sheet: {sheet_id}")
    
    try:
        # Test CSV export
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
        print(f"📡 Fetching data from: {csv_url}")
        
        response = requests.get(csv_url)
        response.raise_for_status()
        
        print("✅ Successfully connected to Google Sheet!")
        
        # Parse and display data
        lines = response.text.strip().split('\n')
        print(f"\n📊 Found {len(lines)} rows in sheet")
        
        if len(lines) > 0:
            print("\n📋 Expected Sheet Structure:")
            print("=" * 60)
            print("| paper_id | status      | reviewer | notes                    |")
            print("|----------|-------------|----------|--------------------------|")
            
            for i, line in enumerate(lines[:5]):  # Show first 5 rows
                if line.strip():
                    columns = [col.strip().strip('"') for col in line.split(',')]
                    if len(columns) >= 4:
                        paper_id = columns[0]
                        status = columns[1]
                        reviewer = columns[2]
                        notes = columns[3] if len(columns) > 3 else ""
                        print(f"| {paper_id:<8} | {status:<11} | {reviewer:<8} | {notes:<24} |")
            
            if len(lines) > 5:
                print(f"| ...      | ...         | ...      | ...                      |")
                print(f"| (and {len(lines) - 5} more rows)                                    |")
        
        # Show status label mapping
        print("\n🏷️ Status Label Mapping:")
        print("-" * 40)
        status_mapping = {
            'pending': 'status-pending (Orange)',
            'in_progress': 'status-in-progress (Blue)',
            'reviewing': 'status-reviewing (Purple)',
            'completed': 'status-completed (Green)',
            'rejected': 'status-rejected (Red)',
            'approved': 'status-approved (Green)'
        }
        
        for status, label in status_mapping.items():
            print(f"  {status:<12} → {label}")
        
        print("\n📝 What the updater does:")
        print("- Updates issue labels based on status")
        print("- Adds status update comments to issues")
        print("- Tracks changes to avoid duplicate updates")
        print("- Creates status labels automatically")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Error connecting to sheet: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure your sheet is public")
        print("2. Check that the sheet ID is correct")
        print("3. Verify the sheet has the expected columns")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def show_example_sheet_structure():
    """Show an example of the expected sheet structure."""
    print("\n📋 Example Google Sheet Structure:")
    print("=" * 60)
    print("| paper_id | status      | reviewer | notes                    |")
    print("|----------|-------------|----------|--------------------------|")
    print("| P1       | pending     | John     | Waiting for assignment   |")
    print("| P2       | in_progress | Alice    | Currently reviewing      |")
    print("| P3       | reviewing   | Bob      | Final review stage       |")
    print("| P4       | completed   | Carol    | Review finished          |")
    print("| P5       | rejected    | David    | Does not meet criteria   |")
    print("=" * 60)
    
    print("\n📝 Column Descriptions:")
    print("- paper_id: The unique identifier (must match issue titles)")
    print("- status: Current status (pending, in_progress, reviewing, completed, rejected, approved)")
    print("- reviewer: Name of the person assigned to review")
    print("- notes: Additional notes or comments")

if __name__ == "__main__":
    # Get sheet ID from user or environment
    sheet_id = os.environ.get('GOOGLE_SHEET_ID')
    
    if not sheet_id:
        sheet_id = input("Enter your Google Sheet ID: ").strip()
    
    if sheet_id:
        test_status_updater(sheet_id)
    else:
        print("❌ No sheet ID provided")
        show_example_sheet_structure()
        print("\nTo get your sheet ID:")
        print("1. Open your Google Sheet")
        print("2. Copy the ID from the URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit") 
#!/usr/bin/env python3
"""
Test script to verify Google Sheet connection and data retrieval
Run this locally to test your setup before using the GitHub Action
"""

import requests
import os

def test_sheet_connection(sheet_id):
    """Test connection to Google Sheet and display data."""
    print(f"🔍 Testing connection to sheet: {sheet_id}")
    
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
            print("\n📋 Sheet contents:")
            print("-" * 50)
            for i, line in enumerate(lines[:10]):  # Show first 10 rows
                if line.strip():
                    columns = line.split(',')
                    paper_id = columns[0].strip().strip('"') if columns else ""
                    print(f"Row {i+1}: {paper_id}")
            
            if len(lines) > 10:
                print(f"... and {len(lines) - 10} more rows")
        
        # Extract paper IDs (skip header)
        paper_ids = []
        for line in lines[1:]:  # Skip first row if it's a header
            if line.strip():
                columns = line.split(',')
                if columns and columns[0].strip():
                    paper_id = columns[0].strip().strip('"')
                    paper_ids.append(paper_id)
        
        print(f"\n🎯 Found {len(paper_ids)} paper IDs:")
        for paper_id in paper_ids[:5]:  # Show first 5
            print(f"  - {paper_id}")
        
        if len(paper_ids) > 5:
            print(f"  ... and {len(paper_ids) - 5} more")
        
        return True
        
    except requests.RequestException as e:
        print(f"❌ Error connecting to sheet: {e}")
        print("\n🔧 Troubleshooting tips:")
        print("1. Make sure your sheet is public (Share → Anyone with link → Viewer)")
        print("2. Check that the sheet ID is correct")
        print("3. Verify the sheet has data in the first column")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    # Get sheet ID from user or environment
    sheet_id = os.environ.get('GOOGLE_SHEET_ID')
    
    if not sheet_id:
        sheet_id = input("Enter your Google Sheet ID: ").strip()
    
    if sheet_id:
        test_sheet_connection(sheet_id)
    else:
        print("❌ No sheet ID provided")
        print("\nTo get your sheet ID:")
        print("1. Open your Google Sheet")
        print("2. Copy the ID from the URL: https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit") 
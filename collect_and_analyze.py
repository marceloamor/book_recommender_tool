#!/usr/bin/env python3
"""
Data Collection and Analysis Script

This script collects data from Goodreads and analyzes it.
"""

import os
import argparse
from dotenv import load_dotenv
from scraper import GoodreadsScraper
from data_storage import DataStorage
from analyze_data import analyze_data

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Collect and analyze Goodreads data")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--shelf", choices=["read", "to-read", "currently-reading", "all"], 
                        default="all", help="Which shelf to scrape")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information")
    args = parser.parse_args()
    
    # Use environment variable if no user_id provided
    user_id = args.user_id or os.getenv("GOODREADS_USER_ID")
    
    if not user_id:
        print("Error: Goodreads user ID is required. Provide it with --user_id or set GOODREADS_USER_ID environment variable.")
        return
    
    # Step 1: Scrape data
    print("\n=== STEP 1: COLLECTING DATA ===")
    scraper = GoodreadsScraper(user_id)
    books = scraper.scrape_shelves(args.shelf)
    
    if books is None or books.empty:
        print("No books found. Check your user ID and try again.")
        return
    
    print(f"Found {len(books)} books in your Goodreads shelves.")
    
    # Step 2: Save data
    print("\n=== STEP 2: SAVING DATA ===")
    storage = DataStorage()
    storage.save_books(books, user_id)
    
    # Step 3: Analyze data
    print("\n=== STEP 3: ANALYZING DATA ===")
    analyze_data(user_id, args.verbose)
    
    print("\nData collection and analysis complete.")
    print("To generate recommendations, run: python main.py --use_saved")

if __name__ == "__main__":
    main() 
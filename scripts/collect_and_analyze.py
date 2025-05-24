#!/usr/bin/env python3
"""
Collect and analyze data from Goodreads.

This script combines scraping and analysis into a single command.
"""

import os
import sys
import argparse
from dotenv import load_dotenv

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scraper import GoodreadsScraper
from data_storage import DataStorage
from analyze_data import analyze_data

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Collect and analyze Goodreads data")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--shelf", choices=["read", "to-read", "currently-reading", "all"], 
                        default="all", help="Which shelf to scrape")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed information")
    args = parser.parse_args()
    
    # Use environment variable if no user_id provided
    user_id = args.user_id or os.getenv("GOODREADS_USER_ID")
    
    if not user_id:
        print("Error: Goodreads user ID is required. Provide it with --user_id or set GOODREADS_USER_ID environment variable.")
        return
    
    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)
    
    # Scrape books from Goodreads
    print(f"Scraping books for user {user_id}...")
    scraper = GoodreadsScraper(user_id)
    books = scraper.scrape_shelves(args.shelf)
    
    if books is None or books.empty:
        print("No books found. Check your user ID and try again.")
        return
    
    print(f"Found {len(books)} books in your Goodreads shelves.")
    
    # Save the data
    print("Saving data for future use...")
    storage = DataStorage()
    storage.save_books(books, user_id)
    
    # Analyze the data
    print("\nAnalyzing data structure...")
    analyze_data(user_id, args.verbose)
    
    print("\nCollection and analysis complete.")
    print("You can now generate recommendations with: python main.py --use_saved")

if __name__ == "__main__":
    main() 
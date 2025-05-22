#!/usr/bin/env python3
"""
Goodreads Book Recommender Tool

This tool scrapes your Goodreads account for books you've read, want to read, 
and are currently reading, then provides personalized book recommendations.
"""

import os
import argparse
from dotenv import load_dotenv
from scraper import GoodreadsScraper
from recommender import BookRecommender
from data_storage import DataStorage

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Goodreads Book Recommender Tool")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--shelf", choices=["read", "to-read", "currently-reading", "all"], 
                        default="all", help="Which shelf to scrape")
    parser.add_argument("--num_recommendations", type=int, default=10,
                        help="Number of book recommendations to generate")
    parser.add_argument("--use_saved", action="store_true",
                        help="Use saved data instead of scraping")
    parser.add_argument("--save_data", action="store_true",
                        help="Save scraped data for future use")
    parser.add_argument("--list_saved", action="store_true",
                        help="List saved data files")
    args = parser.parse_args()
    
    # Initialize data storage
    storage = DataStorage()
    
    # List saved data if requested
    if args.list_saved:
        saved_files = storage.list_saved_data()
        if saved_files:
            print("Saved data files:")
            for file in saved_files:
                print(f"  - {file}")
        else:
            print("No saved data files found.")
        return
    
    # Use environment variable if no user_id provided
    user_id = args.user_id or os.getenv("GOODREADS_USER_ID")
    
    if not user_id:
        print("Error: Goodreads user ID is required. Provide it with --user_id or set GOODREADS_USER_ID environment variable.")
        return
    
    # Get books data
    books = None
    
    if args.use_saved:
        # Load books from saved data
        books = storage.load_books(user_id=user_id)
        if books is None:
            print("No saved data found. Scraping from Goodreads instead.")
            args.use_saved = False
    
    if not args.use_saved:
        # Scrape books from Goodreads
        scraper = GoodreadsScraper(user_id)
        books = scraper.scrape_shelves(args.shelf)
        
        # Save data if requested
        if args.save_data and books is not None:
            storage.save_books(books, user_id)
    
    if books is None or books.empty:
        print("No books found. Check your user ID and try again.")
        return
    
    print(f"Found {len(books)} books in your Goodreads shelves.")
    
    # Generate recommendations
    recommender = BookRecommender(books)
    recommendations = recommender.get_recommendations(args.num_recommendations)
    
    if not recommendations:
        print("Could not generate recommendations. Try scraping more books or different shelves.")
        return
    
    # Display recommendations
    print("\nRecommended Books:")
    for i, book in enumerate(recommendations, 1):
        print(f"{i}. {book['title']} by {book['author']}")
        print(f"   Genre: {book['genre']}")
        print(f"   Rating: {book['rating']}/5.0")
        print(f"   Link: {book['link']}\n")

if __name__ == "__main__":
    main() 
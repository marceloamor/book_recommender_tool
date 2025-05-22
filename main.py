#!/usr/bin/env python3
"""
Goodreads Book Recommender Tool

This tool scrapes your Goodreads account for books you've read, want to read, 
and are currently reading, then provides personalized book recommendations.
"""

import os
import argparse
import textwrap
from dotenv import load_dotenv
from scraper import GoodreadsScraper
from recommender import BookRecommender
from data_storage import DataStorage
from analyze_data import analyze_data

def display_recommendations(recommendations):
    """Display book recommendations in a nicely formatted way"""
    if not recommendations:
        print("No recommendations available.")
        return
        
    print("\n" + "=" * 80)
    print("RECOMMENDED BOOKS FOR YOU")
    print("=" * 80)
    
    for i, book in enumerate(recommendations, 1):
        title = book.get("title", "Unknown Title")
        author = book.get("author", "Unknown Author")
        genre = book.get("genre", "")
        rating = book.get("rating", 0.0)
        link = book.get("link", "")
        score = book.get("score", 0.0)
        
        print(f"\n{i}. {title} by {author}")
        print(f"   Genre: {genre}")
        print(f"   Rating: {rating:.1f}/5.0")
        if score:
            print(f"   Match Score: {score:.2f}")
        if link:
            print(f"   Link: {link}")
        print("-" * 80)

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
    parser.add_argument("--analyze_data", action="store_true",
                        help="Analyze saved data structure")
    parser.add_argument("--scrape_only", action="store_true",
                        help="Only scrape and save data, don't generate recommendations")
    parser.add_argument("--verbose", action="store_true",
                        help="Show detailed information")
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
    
    # Analyze data if requested
    if args.analyze_data:
        analyze_data(args.user_id, args.verbose)
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
    
    # If scrape_only flag is set, exit here
    if args.scrape_only:
        print("Scraping completed. Data saved successfully.")
        return
    
    # Generate recommendations
    print("\nGenerating recommendations...")
    recommender = BookRecommender(books)
    recommendations = recommender.get_recommendations(args.num_recommendations)
    
    if not recommendations:
        print("Could not generate recommendations. Try scraping more books or different shelves.")
        return
    
    # Display recommendations
    display_recommendations(recommendations)

if __name__ == "__main__":
    main() 
#!/usr/bin/env python3
"""
Fix Genres Script

This script fixes missing genres in existing saved data.
"""

import os
import argparse
import pandas as pd
from dotenv import load_dotenv
from tqdm import tqdm
import time
import logging
from scraper import GoodreadsScraper
from data_storage import DataStorage
from recommender import BookRecommender

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/fix_genres.log"),
    ]
)
logger = logging.getLogger(__name__)

def fix_genres(user_id=None, verbose=False):
    """Fix missing genres in saved data"""
    if not user_id:
        user_id = os.getenv("GOODREADS_USER_ID")
        if not user_id:
            logger.error("No user ID provided or found in environment variables")
            return False
    
    # Load saved data
    storage = DataStorage()
    books_df = storage.load_books(user_id=user_id)
    
    if books_df is None or books_df.empty:
        logger.error("No saved data found")
        return False
    
    # Check for missing genres
    if "genres" not in books_df.columns:
        books_df["genres"] = [[] for _ in range(len(books_df))]
        
    missing_genres = books_df["genres"].apply(lambda x: not x or len(x) == 0).sum()
    
    if missing_genres == 0:
        logger.info("No missing genres found")
        return True
    
    logger.info(f"Found {missing_genres} books with missing genres")
    
    # Step 1: Try to fetch genres from Goodreads
    scraper = GoodreadsScraper("")
    
    books_with_urls = books_df[books_df["url"].str.len() > 0].copy()
    updated_count = 0
    
    for idx, row in tqdm(books_with_urls.iterrows(), total=len(books_with_urls), desc="Fetching genres"):
        if row["url"] and (not row["genres"] or len(row["genres"]) == 0):
            try:
                details = scraper.get_book_details(row["url"])
                
                if details and details.get("genres"):
                    books_df.at[idx, "genres"] = details.get("genres", [])
                    updated_count += 1
                    
                # Be nice to Goodreads servers
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error fetching details for book {row['title']}: {e}")
    
    logger.info(f"Updated {updated_count} books with genres from Goodreads")
    
    # Step 2: Apply fallback genre extraction
    recommender = BookRecommender(books_df)
    recommender._apply_fallback_genre_extraction()
    
    # Get the updated DataFrame
    books_df = recommender.user_books_df
    
    # Step 3: Save the updated data
    storage.save_books(books_df, user_id)
    logger.info("Saved updated data with fixed genres")
    
    # Step 4: Print summary
    if verbose:
        genre_counts = {}
        for _, row in books_df.iterrows():
            for genre in row["genres"]:
                if genre in genre_counts:
                    genre_counts[genre] += 1
                else:
                    genre_counts[genre] = 1
        
        print("\n=== GENRE DISTRIBUTION ===")
        for genre, count in sorted(genre_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{genre}: {count} books")
    
    return True

def main():
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Fix missing genres in saved data")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information")
    args = parser.parse_args()
    
    fix_genres(args.user_id, args.verbose)

if __name__ == "__main__":
    main() 
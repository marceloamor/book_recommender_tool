#!/usr/bin/env python3
"""
Data Analysis Script

This script analyzes the structure of saved book data to help debug and improve the recommendation system.
"""

import argparse
import json
import pandas as pd
import os
from data_storage import DataStorage

def analyze_data(user_id=None, verbose=False):
    """Analyze saved book data structure"""
    storage = DataStorage()
    
    # Get data structure info
    info = storage.analyze_data_structure(user_id)
    
    if "error" in info:
        print(f"Error: {info['error']}")
        return
    
    # Display basic info
    print(f"\n=== DATA STRUCTURE ANALYSIS ===")
    print(f"Number of books: {info['num_books']}")
    print(f"Columns: {', '.join(info['columns'])}")
    print(f"Missing values: {json.dumps(info['missing_values'], indent=2)}")
    
    # Check for critical columns
    critical_columns = ["title", "author", "genres", "avg_rating", "user_rating", "url"]
    missing_columns = [col for col in critical_columns if col not in info["columns"]]
    
    if missing_columns:
        print(f"\n⚠️ WARNING: Missing critical columns: {', '.join(missing_columns)}")
    
    # Check genres structure
    if "genres_samples" in info:
        print("\n=== GENRES STRUCTURE ===")
        for i, genre in enumerate(info["genres_samples"][:5]):
            print(f"Book {i+1} genres: {genre}")
    
    # Show sample data
    if verbose:
        print("\n=== SAMPLE BOOKS ===")
        for i, book in enumerate(info["sample_rows"]):
            print(f"\nBook {i+1}:")
            for key, value in book.items():
                print(f"  {key}: {value}")
    
    # Check for potential issues
    print("\n=== POTENTIAL ISSUES ===")
    
    # Check for missing titles
    if "title_samples" in info:
        missing_titles = sum(1 for title in info["title_samples"] if not title or title == "Unknown Title")
        if missing_titles > 0:
            print(f"⚠️ {missing_titles} out of 10 sample books have missing titles")
    
    # Check for missing authors
    if "author_samples" in info:
        missing_authors = sum(1 for author in info["author_samples"] if not author or author == "Unknown Author")
        if missing_authors > 0:
            print(f"⚠️ {missing_authors} out of 10 sample books have missing authors")
    
    # Check for missing genres
    if "genres_samples" in info:
        missing_genres = sum(1 for genres in info["genres_samples"] if not genres or len(genres) == 0)
        if missing_genres > 0:
            print(f"⚠️ {missing_genres} out of 10 sample books have missing genres")
    
    # Check for missing ratings
    if "avg_rating_samples" in info:
        missing_ratings = sum(1 for rating in info["avg_rating_samples"] if rating == 0)
        if missing_ratings > 0:
            print(f"⚠️ {missing_ratings} out of 10 sample books have missing average ratings")
    
    # Check for missing user ratings
    if "user_rating_samples" in info:
        missing_user_ratings = sum(1 for rating in info["user_rating_samples"] if rating == 0)
        if missing_user_ratings > 0:
            print(f"⚠️ {missing_user_ratings} out of 10 sample books have missing user ratings")
    
    # Provide recommendations
    print("\n=== RECOMMENDATIONS ===")
    if missing_columns:
        print("1. Update the scraper to extract missing columns")
    
    if "genres_samples" in info and missing_genres > 5:
        print("2. Improve genre extraction in the scraper")
    
    if "avg_rating_samples" in info and missing_ratings > 5:
        print("3. Fix average rating extraction in the scraper")
    
    print("4. Consider running a full scrape with --save_data to create a fresh dataset")
    
    return info

def main():
    parser = argparse.ArgumentParser(description="Analyze saved book data structure")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--verbose", action="store_true", help="Show detailed information")
    args = parser.parse_args()
    
    analyze_data(args.user_id, args.verbose)

if __name__ == "__main__":
    main() 
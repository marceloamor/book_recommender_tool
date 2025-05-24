#!/usr/bin/env python3
"""
Test Genre Extraction

This script tests the improved genre extraction on several books.
"""

import logging
from scraper import GoodreadsScraper

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def test_genre_extraction():
    """Test genre extraction on several books"""
    # Create a scraper instance
    scraper = GoodreadsScraper("")
    
    # List of book URLs to test
    test_urls = [
        "https://www.goodreads.com/book/show/13707738-boomerang",
        "https://www.goodreads.com/book/show/10669.When_Genius_Failed",
        "https://www.goodreads.com/book/show/58784475-tomorrow-and-tomorrow-and-tomorrow",
        "https://www.goodreads.com/book/show/7865083-liar-s-poker",
        "https://www.goodreads.com/book/show/24724602-flash-boys"
    ]
    
    print("\n=== TESTING GENRE EXTRACTION ===\n")
    
    for url in test_urls:
        print(f"\nTesting URL: {url}")
        details = scraper.get_book_details(url)
        
        if details:
            title = details.get("title", "Unknown Title")
            genres = details.get("genres", [])
            
            print(f"Title: {title}")
            print(f"Genres: {', '.join(genres) if genres else 'None found'}")
        else:
            print("Failed to get book details")

if __name__ == "__main__":
    test_genre_extraction() 
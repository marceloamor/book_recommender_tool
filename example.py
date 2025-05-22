#!/usr/bin/env python3
"""
Example script for Goodreads Book Recommender Tool

This example shows how to use the tool to scrape a Goodreads account and generate recommendations.
"""

from scraper import GoodreadsScraper
from recommender import BookRecommender

def main():
    # Replace with your Goodreads user ID
    # You can find it in your profile URL: https://www.goodreads.com/user/show/XXXXXXX-username
    user_id = "11111111"  # Example user ID, replace with your own
    
    print(f"Scraping Goodreads shelves for user {user_id}...")
    
    # Create a scraper instance
    scraper = GoodreadsScraper(user_id)
    
    # Scrape books from the "read" shelf
    books = scraper.scrape_shelves(shelf="read")
    
    if books is None or books.empty:
        print("No books found. Check your user ID and try again.")
        return
    
    print(f"Found {len(books)} books in your 'read' shelf.")
    
    # Display a sample of books
    print("\nSample of books from your shelf:")
    for i, (_, book) in enumerate(books.head(5).iterrows(), 1):
        print(f"{i}. {book['title']} by {book['author']} - Your rating: {book['user_rating']}/5")
    
    # Generate recommendations
    print("\nGenerating book recommendations...")
    recommender = BookRecommender(books)
    recommendations = recommender.get_recommendations(num_recommendations=5)
    
    # Display recommendations
    print("\nRecommended Books:")
    for i, book in enumerate(recommendations, 1):
        print(f"{i}. {book['title']} by {book['author']}")
        print(f"   Genre: {book['genre']}")
        print(f"   Rating: {book['rating']}/5.0")
        print(f"   Link: {book['link']}\n")
    
    print("Done! Try running the main.py script with your own user ID for more options.")

if __name__ == "__main__":
    main() 
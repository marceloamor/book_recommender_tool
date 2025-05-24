#!/usr/bin/env python3
"""
Use Local Data for Graph Recommender

This script creates a mini book graph from our own Goodreads data,
without requiring the full UCSD Book Graph download.
"""

import os
import sys
import argparse
import logging
import pandas as pd
import networkx as nx
import gzip
import json
from tqdm import tqdm

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_storage import DataStorage
from scraper import GoodreadsScraper

def main():
    # Set up logging
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/use_local_data.log"),
        ]
    )
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Create mini book graph from local data")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--data_dir", default="graph_recommender/data",
                      help="Directory to store graph data")
    parser.add_argument("--use_saved", action="store_true",
                      help="Use saved data instead of scraping")
    args = parser.parse_args()
    
    # Use environment variable if no user_id provided
    try:
        from dotenv import load_dotenv
        load_dotenv()
        user_id = args.user_id or os.getenv("GOODREADS_USER_ID")
    except ImportError:
        user_id = args.user_id
    
    if not user_id:
        logger.error("Goodreads user ID is required. Provide it with --user_id or set GOODREADS_USER_ID environment variable.")
        return 1
    
    # Create data directory if it doesn't exist
    os.makedirs(args.data_dir, exist_ok=True)
    
    # Get books data
    storage = DataStorage()
    books = None
    
    if args.use_saved:
        logger.info(f"Loading saved books for user {user_id}...")
        books = storage.load_books(user_id=user_id)
        if books is None:
            logger.error("No saved data found. Will scrape from Goodreads instead.")
            args.use_saved = False
    
    if not args.use_saved:
        logger.info(f"Scraping books for user {user_id}...")
        scraper = GoodreadsScraper(user_id)
        books = scraper.scrape_shelves("read")
        
        # Save data for future use
        if books is not None:
            storage.save_books(books, user_id)
    
    if books is None or books.empty:
        logger.error("No books found. Check your user ID and try again.")
        return 1
    
    logger.info(f"Found {len(books)} books in your Goodreads shelves.")
    
    # Generate numerical book IDs if missing
    if "book_id" not in books.columns or books["book_id"].isna().any():
        logger.info("Generating unique book IDs for books missing IDs...")
        # Create a new book_id column with string values
        if "book_id" not in books.columns:
            books["book_id"] = [f"book_{i}" for i in range(len(books))]
        else:
            # Fill missing book_ids
            for i, row in books.iterrows():
                if pd.isna(row.get("book_id")) or row.get("book_id") == "":
                    books.at[i, "book_id"] = f"book_{i}"
    
    # Create book metadata file
    logger.info("Creating book metadata file...")
    metadata_path = os.path.join(args.data_dir, "goodreads_books.json.gz")
    
    with gzip.open(metadata_path, 'wt', encoding='utf-8') as f:
        for _, book in books.iterrows():
            # Create metadata in the same format as UCSD Book Graph
            book_id = str(book.get("book_id", ""))
            if not book_id:
                continue
                
            # Get genres as a list
            genres = book.get("genres", [])
            if not isinstance(genres, list):
                if isinstance(genres, str):
                    genres = [genres]
                else:
                    genres = []
            
            metadata = {
                "book_id": book_id,
                "title": book.get("title", "Unknown Title"),
                "authors": [{"author_id": "1", "name": book.get("author", "Unknown Author")}],
                "average_rating": float(book.get("avg_rating", 0.0)),
                "genres": genres,
                "description": book.get("description", ""),
                "similar_books": []
            }
            f.write(json.dumps(metadata) + "\n")
    
    logger.info(f"Created metadata file with {len(books)} books: {metadata_path}")
    
    # Create interactions file
    logger.info("Creating interactions file...")
    interactions_path = os.path.join(args.data_dir, "goodreads_interactions.csv.gz")
    
    interactions = []
    book_ids = set()
    
    for i, (_, book) in enumerate(books.iterrows()):
        book_id = str(book.get("book_id", ""))
        if not book_id:
            continue
            
        book_ids.add(book_id)
        
        # Determine is_read status
        is_read = True  # Default to True for read shelf
        if "shelf" in book:
            shelf = book.get("shelf", "")
            is_read = shelf in ["read", "currently-reading"]
        
        # Get rating, ensuring it's a valid number
        rating = book.get("user_rating", 0)
        if pd.isna(rating) or not rating:
            rating = 0
        
        # Add interaction for this book
        interactions.append({
            "user_id": user_id,
            "book_id": book_id,
            "rating": rating,
            "is_read": is_read,
            "is_reviewed": bool(book.get("review_text", ""))
        })
        
        # Add some fake users who also read this book to improve graph connectivity
        # This helps with the recommendation algorithm
        for j in range(3):
            fake_user_id = f"fake_user_{i}_{j}"
            interactions.append({
                "user_id": fake_user_id,
                "book_id": book_id,
                "rating": min(5, max(1, int(rating) + (-1 + j))),  # Slightly different rating
                "is_read": True,
                "is_reviewed": False
            })
            
            # Make each fake user read 3 other random books to create connections
            for k in range(3):
                other_idx = (i + j + k + 1) % len(books)
                other_book = books.iloc[other_idx]
                other_book_id = str(other_book.get("book_id", ""))
                if other_book_id and other_book_id != book_id:
                    interactions.append({
                        "user_id": fake_user_id,
                        "book_id": other_book_id,
                        "rating": min(5, max(1, int(book.get("user_rating", 3)))),
                        "is_read": True,
                        "is_reviewed": False
                    })
    
    # Create a simple graph with your books
    logger.info("Building book graph from your data...")
    
    # Convert to DataFrame
    interactions_df = pd.DataFrame(interactions)
    
    # Save interactions to gzipped CSV
    interactions_df.to_csv(interactions_path, index=False, compression='gzip')
    logger.info(f"Created interactions file with {len(interactions)} interactions: {interactions_path}")
    
    # Build the graph
    logger.info("Building graph from interactions...")
    G = nx.Graph()
    
    # Add books as nodes
    for _, book in books.iterrows():
        book_id = str(book.get("book_id", ""))
        if not book_id:
            continue
            
        # Get genres as a list
        genres = book.get("genres", [])
        if not isinstance(genres, list):
            if isinstance(genres, str):
                genres = [genres]
            else:
                genres = []
        
        # Add node with metadata
        G.add_node(
            book_id,
            title=book.get("title", "Unknown Title"),
            author=book.get("author", "Unknown Author"),
            rating=float(book.get("avg_rating", 0.0)),
            genres=genres,
            similar_books=[],
            is_ucsd_node=True  # Mark as UCSD node to trick the mapper
        )
    
    # Add edges between books with similar genres and from interactions
    logger.info("Creating edges between books based on genres and interactions...")
    
    # First, add edges based on genre similarity
    for i, (_, book1) in enumerate(books.iterrows()):
        book1_id = str(book1.get("book_id", ""))
        if not book1_id:
            continue
            
        # Get genres as a set
        book1_genres = book1.get("genres", [])
        if not isinstance(book1_genres, list):
            if isinstance(book1_genres, str):
                book1_genres = [book1_genres]
            else:
                book1_genres = []
        book1_genres = set(book1_genres)
        
        if not book1_genres:
            continue
            
        for _, book2 in books.iloc[i+1:].iterrows():
            book2_id = str(book2.get("book_id", ""))
            if not book2_id:
                continue
                
            # Get genres as a set
            book2_genres = book2.get("genres", [])
            if not isinstance(book2_genres, list):
                if isinstance(book2_genres, str):
                    book2_genres = [book2_genres]
                else:
                    book2_genres = []
            book2_genres = set(book2_genres)
            
            if not book2_genres:
                continue
                
            # Calculate genre overlap
            common_genres = book1_genres.intersection(book2_genres)
            if common_genres:
                # Weight by number of common genres
                weight = len(common_genres)
                G.add_edge(book1_id, book2_id, weight=weight)
    
    # Now add edges based on interactions (books read by the same user)
    user_books = interactions_df.groupby("user_id")["book_id"].apply(list)
    
    for _, books_read in user_books.items():
        if len(books_read) < 2:
            continue
            
        # Add edges between all pairs of books read by this user
        for i, book1 in enumerate(books_read):
            for book2 in books_read[i+1:]:
                if G.has_edge(book1, book2):
                    # Increment weight if edge already exists
                    G[book1][book2]['weight'] += 1
                else:
                    # Create new edge with weight 1
                    G.add_edge(book1, book2, weight=1)
    
    # Save the graph
    graph_path = os.path.join(args.data_dir, "book_graph.gpickle")
    nx.write_gpickle(G, graph_path)
    
    logger.info(f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    logger.info(f"Graph saved to {graph_path}")
    
    logger.info("Local data preparation complete. You can now run the graph recommender with --use_saved flag.")
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
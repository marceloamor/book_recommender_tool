#!/usr/bin/env python3
"""
Add External Books to Recommendations

This script downloads the Book-Crossing dataset and integrates it with your 
local book graph to provide recommendations for books you haven't read.
"""

import os
import sys
import argparse
import logging
import pandas as pd
import networkx as nx
import gzip
import json
import requests
import zipfile
import io
from tqdm import tqdm
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import shutil

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from data_storage import DataStorage
from scraper import GoodreadsScraper

# Book-Crossing dataset URL (GitHub alternative)
BOOKCROSSING_GITHUB_URL = "https://github.com/ashwanidv100/Recommendation-System---Book-Crossing-Dataset/archive/refs/heads/master.zip"

def download_bookcrossing():
    """Download and extract the Book-Crossing dataset from GitHub"""
    logger = logging.getLogger(__name__)
    
    data_dir = "graph_recommender/data/bookcrossing"
    os.makedirs(data_dir, exist_ok=True)
    
    books_path = os.path.join(data_dir, "BX-Books.csv")
    ratings_path = os.path.join(data_dir, "BX-Book-Ratings.csv")
    
    # Skip if already downloaded
    if os.path.exists(books_path) and os.path.exists(ratings_path):
        logger.info("Book-Crossing dataset already exists. Skipping download.")
        return books_path, ratings_path
    
    logger.info(f"Downloading Book-Crossing dataset from GitHub...")
    
    try:
        response = requests.get(BOOKCROSSING_GITHUB_URL, stream=True)
        response.raise_for_status()
        
        # Extract ZIP file to temporary directory
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            z.extractall(data_dir)
            
        # Move files from nested directory to data_dir
        github_dir = os.path.join(data_dir, "Recommendation-System---Book-Crossing-Dataset-master", "BX-CSV-Dump")
        if os.path.exists(github_dir):
            for file in os.listdir(github_dir):
                if file.endswith(".csv"):
                    src = os.path.join(github_dir, file)
                    dst = os.path.join(data_dir, file)
                    shutil.copy(src, dst)
                    logger.info(f"Copied {file} to {data_dir}")
        
        logger.info(f"Downloaded and extracted Book-Crossing dataset to {data_dir}")
        return books_path, ratings_path
    except Exception as e:
        logger.error(f"Error downloading Book-Crossing dataset: {e}")
        return None, None

def load_bookcrossing_data(books_path, ratings_path):
    """Load the Book-Crossing dataset"""
    logger = logging.getLogger(__name__)
    
    try:
        # Load books with proper encoding
        logger.info(f"Loading books from {books_path}")
        books_df = pd.read_csv(books_path, sep=';', encoding='latin1', 
                             escapechar='\\', quotechar='"', on_bad_lines='skip')
        
        # Load ratings with proper encoding
        logger.info(f"Loading ratings from {ratings_path}")
        ratings_df = pd.read_csv(ratings_path, sep=';', encoding='latin1',
                               escapechar='\\', quotechar='"', on_bad_lines='skip')
        
        # Clean up column names
        books_df.columns = [col.strip('"') for col in books_df.columns]
        ratings_df.columns = [col.strip('"') for col in ratings_df.columns]
        
        # Rename columns for consistency
        books_df = books_df.rename(columns={
            'ISBN': 'isbn',
            'Book-Title': 'title',
            'Book-Author': 'author',
            'Year-Of-Publication': 'year',
            'Publisher': 'publisher',
            'Image-URL-S': 'image_url_small',
            'Image-URL-M': 'image_url_medium',
            'Image-URL-L': 'image_url_large'
        })
        
        ratings_df = ratings_df.rename(columns={
            'User-ID': 'user_id',
            'ISBN': 'isbn',
            'Book-Rating': 'rating'
        })
        
        logger.info(f"Loaded {len(books_df)} books and {len(ratings_df)} ratings")
        return books_df, ratings_df
    
    except Exception as e:
        logger.error(f"Error loading Book-Crossing dataset: {e}")
        return None, None

def find_similar_books(your_books, external_books, n_similar=5):
    """Find books similar to your collection from the external dataset"""
    logger = logging.getLogger(__name__)
    
    # Extract features from your books
    your_features = []
    for _, book in your_books.iterrows():
        title = str(book.get('title', ''))
        author = str(book.get('author', ''))
        genres = ' '.join(book.get('genres', [])) if isinstance(book.get('genres', []), list) else ''
        features = f"{title} {author} {genres}".lower()
        your_features.append(features)
    
    # Extract features from external books
    external_features = []
    for _, book in external_books.iterrows():
        title = str(book.get('title', ''))
        author = str(book.get('author', ''))
        features = f"{title} {author}".lower()
        external_features.append(features)
    
    # Combine features for vectorization
    all_features = your_features + external_features
    
    # Create TF-IDF vectors
    vectorizer = TfidfVectorizer(min_df=2, max_df=0.95, stop_words='english')
    tfidf_matrix = vectorizer.fit_transform(all_features)
    
    # Split the matrix
    your_tfidf = tfidf_matrix[:len(your_features)]
    external_tfidf = tfidf_matrix[len(your_features):]
    
    # Calculate similarities between your books and external books
    logger.info("Calculating similarities between your books and external books...")
    similarities = cosine_similarity(your_tfidf, external_tfidf)
    
    # Find most similar external books for each of your books
    similar_indices = []
    for i in range(similarities.shape[0]):
        # Get indices of the most similar external books
        similar_idx = similarities[i].argsort()[-n_similar:][::-1]
        similar_indices.extend(similar_idx)
    
    # Remove duplicates
    similar_indices = list(set(similar_indices))
    
    # Get the similar books
    similar_books = external_books.iloc[similar_indices].copy()
    logger.info(f"Found {len(similar_books)} similar books from the external dataset")
    
    return similar_books

def integrate_with_graph(your_books, similar_books, graph_path):
    """Integrate external books with your book graph"""
    logger = logging.getLogger(__name__)
    
    # Load existing graph
    G = nx.read_gpickle(graph_path)
    logger.info(f"Loaded existing graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    # Get existing book IDs
    existing_ids = set(G.nodes())
    
    # Add similar books as new nodes
    new_books_added = 0
    
    for i, (_, book) in enumerate(similar_books.iterrows()):
        # Create a unique book ID for the external book
        book_id = f"external_{book['isbn']}"
        
        # Skip if already in graph
        if book_id in existing_ids:
            continue
        
        # Add node with metadata
        G.add_node(
            book_id,
            title=book.get('title', 'Unknown Title'),
            author=book.get('author', 'Unknown Author'),
            rating=float(book.get('avg_rating', 3.5)), # Default rating if not available
            genres=[],  # External books might not have genres
            similar_books=[],
            is_ucsd_node=True,  # Trick the mapper
            read_by_user=False  # Mark as not read by user
        )
        new_books_added += 1
    
    # Connect external books to your books based on similarity
    logger.info("Connecting external books to your books based on similarity...")
    
    # Prepare feature vectors for similarity calculation
    book_features = {}
    
    # Extract features from your books
    for _, book in your_books.iterrows():
        book_id = str(book.get('book_id', ''))
        if not book_id or book_id not in existing_ids:
            continue
            
        title = str(book.get('title', ''))
        author = str(book.get('author', ''))
        genres = ' '.join(book.get('genres', [])) if isinstance(book.get('genres', []), list) else ''
        features = f"{title} {author} {genres}".lower()
        book_features[book_id] = features
    
    # Extract features from external books
    for _, book in similar_books.iterrows():
        book_id = f"external_{book['isbn']}"
        if book_id not in G:
            continue
            
        title = str(book.get('title', ''))
        author = str(book.get('author', ''))
        features = f"{title} {author}".lower()
        book_features[book_id] = features
    
    # Calculate pairwise similarities and add edges
    vectorizer = TfidfVectorizer(min_df=1, max_df=0.95, stop_words='english')
    all_features = list(book_features.values())
    feature_ids = list(book_features.keys())
    
    if len(all_features) > 1:  # Need at least 2 books for vectorization
        tfidf_matrix = vectorizer.fit_transform(all_features)
        
        # Calculate pairwise similarities
        pairwise_similarities = cosine_similarity(tfidf_matrix)
        
        # Add edges for similar books
        edges_added = 0
        for i in range(len(feature_ids)):
            for j in range(i+1, len(feature_ids)):
                book1_id = feature_ids[i]
                book2_id = feature_ids[j]
                
                # Skip if not in graph
                if book1_id not in G or book2_id not in G:
                    continue
                
                # Only connect your books to external books
                is_your_book1 = not book1_id.startswith("external_")
                is_your_book2 = not book2_id.startswith("external_")
                
                # Skip connections between two of your books or two external books
                if (is_your_book1 and is_your_book2) or (not is_your_book1 and not is_your_book2):
                    continue
                
                similarity = pairwise_similarities[i, j]
                
                # Only add edge if similarity is high enough
                if similarity > 0.1:
                    weight = similarity * 5  # Scale to be similar to existing weights
                    G.add_edge(book1_id, book2_id, weight=weight)
                    edges_added += 1
    
    logger.info(f"Added {new_books_added} new books and {edges_added} new connections to the graph")
    
    # Save the updated graph
    nx.write_gpickle(G, graph_path)
    logger.info(f"Saved updated graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
    
    return G

def update_metadata_file(similar_books, metadata_path):
    """Update the metadata file with external books"""
    logger = logging.getLogger(__name__)
    
    # Read existing metadata
    existing_books = []
    with gzip.open(metadata_path, 'rt', encoding='utf-8') as f:
        for line in f:
            existing_books.append(json.loads(line))
    
    # Get existing book IDs
    existing_ids = set(book['book_id'] for book in existing_books)
    
    # Add external books
    new_books = []
    for _, book in similar_books.iterrows():
        book_id = f"external_{book['isbn']}"
        
        # Skip if already in metadata
        if book_id in existing_ids:
            continue
        
        # Create metadata in the same format as UCSD Book Graph
        metadata = {
            "book_id": book_id,
            "title": book.get('title', 'Unknown Title'),
            "authors": [{"author_id": "ext", "name": book.get('author', 'Unknown Author')}],
            "average_rating": 3.5,  # Default rating
            "genres": [],  # External books might not have genres
            "description": "",
            "similar_books": []
        }
        new_books.append(metadata)
    
    # Write updated metadata
    with gzip.open(metadata_path, 'wt', encoding='utf-8') as f:
        for book in existing_books:
            f.write(json.dumps(book) + "\n")
        for book in new_books:
            f.write(json.dumps(book) + "\n")
    
    logger.info(f"Added {len(new_books)} external books to metadata file")

def update_interactions_file(similar_books, interactions_path):
    """Update the interactions file with external books"""
    logger = logging.getLogger(__name__)
    
    # Read existing interactions
    interactions_df = pd.read_csv(interactions_path, compression='gzip')
    
    # Create fake interactions for external books
    new_interactions = []
    for _, book in similar_books.iterrows():
        book_id = f"external_{book['isbn']}"
        
        # Create interactions with fake users
        for i in range(3):
            fake_user_id = f"external_user_{i}_{book['isbn']}"
            
            new_interactions.append({
                "user_id": fake_user_id,
                "book_id": book_id,
                "rating": 4,  # Good rating but not perfect
                "is_read": True,
                "is_reviewed": False
            })
    
    # Add interactions between external books and existing books to create connections
    if not new_interactions:
        logger.info("No new interactions to add")
        return
    
    # Convert to DataFrame
    new_interactions_df = pd.DataFrame(new_interactions)
    
    # Combine with existing interactions
    combined_df = pd.concat([interactions_df, new_interactions_df], ignore_index=True)
    
    # Save updated interactions
    combined_df.to_csv(interactions_path, index=False, compression='gzip')
    
    logger.info(f"Added {len(new_interactions)} new interactions to interactions file")

def main():
    # Set up logging
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/add_external_books.log"),
        ]
    )
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Add external books to your local book graph")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--data_dir", default="graph_recommender/data",
                      help="Directory to store graph data")
    parser.add_argument("--use_saved", action="store_true",
                      help="Use saved data instead of scraping")
    parser.add_argument("--similar_per_book", type=int, default=5,
                      help="Number of similar books to find per book in your collection")
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
    
    # Get your books data
    storage = DataStorage()
    your_books = None
    
    if args.use_saved:
        logger.info(f"Loading saved books for user {user_id}...")
        your_books = storage.load_books(user_id=user_id)
        if your_books is None:
            logger.error("No saved data found. Use --use_saved only if you have previously saved data.")
            return 1
    else:
        logger.info(f"Scraping books for user {user_id}...")
        scraper = GoodreadsScraper(user_id)
        your_books = scraper.scrape_shelves("all")
        
        # Save data for future use
        if your_books is not None:
            storage.save_books(your_books, user_id)
    
    if your_books is None or your_books.empty:
        logger.error("No books found. Check your user ID and try again.")
        return 1
    
    logger.info(f"Found {len(your_books)} books in your Goodreads shelves.")
    
    # Download Book-Crossing dataset
    books_path, ratings_path = download_bookcrossing()
    if books_path is None or ratings_path is None:
        logger.error("Failed to download Book-Crossing dataset.")
        return 1
    
    # Load Book-Crossing dataset
    books_df, ratings_df = load_bookcrossing_data(books_path, ratings_path)
    if books_df is None or ratings_df is None:
        logger.error("Failed to load Book-Crossing dataset.")
        return 1
    
    # Find books similar to your collection
    similar_books = find_similar_books(your_books, books_df, n_similar=args.similar_per_book)
    
    # Paths to the files
    graph_path = os.path.join(args.data_dir, "book_graph.gpickle")
    metadata_path = os.path.join(args.data_dir, "goodreads_books.json.gz")
    interactions_path = os.path.join(args.data_dir, "goodreads_interactions.csv.gz")
    
    # Check if graph exists
    if not os.path.exists(graph_path):
        logger.error(f"Graph file not found: {graph_path}")
        logger.info("Run use_local_data.py first to create your local book graph.")
        return 1
    
    # Integrate similar books with your graph
    integrate_with_graph(your_books, similar_books, graph_path)
    
    # Update metadata file
    update_metadata_file(similar_books, metadata_path)
    
    # Update interactions file
    update_interactions_file(similar_books, interactions_path)
    
    logger.info("Successfully integrated external books with your local book graph.")
    logger.info("You can now run the graph recommender to get recommendations for books you haven't read.")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 
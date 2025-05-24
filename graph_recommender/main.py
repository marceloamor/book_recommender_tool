"""
Main module for the graph-based book recommender.

This module provides a command-line interface to the graph-based book recommender,
which uses the UCSD Book Graph to generate personalized book recommendations.
"""

import os
import argparse
import logging
import pandas as pd
from dotenv import load_dotenv

from graph_recommender.graph.load_ucsd_graph import UCSDBookGraph
from graph_recommender.goodreads.map_books_to_ucsd import BookMapper
from graph_recommender.graph.build_personal_subgraph import PersonalSubgraph
from graph_recommender.graph.recommend import GraphRecommender

# Try to import scraper from parent project
try:
    from scraper import GoodreadsScraper
    from data_storage import DataStorage
except ImportError:
    print("Warning: Couldn't import scraper from parent project. Using stub implementation.")
    # Stub implementation for standalone use
    class GoodreadsScraper:
        def __init__(self, user_id):
            self.user_id = user_id
        
        def scrape_shelves(self, shelf="read"):
            print(f"Please install and use the original scraper to get real data for user {self.user_id}")
            return pd.DataFrame()
    
    class DataStorage:
        def load_books(self, user_id):
            return None
        
        def save_books(self, books, user_id):
            pass

def setup_logging(verbose=False):
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filename='logs/graph_recommender.log'
    )
    
    # Also log to console
    console = logging.StreamHandler()
    console.setLevel(log_level)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console.setFormatter(formatter)
    logging.getLogger('').addHandler(console)

def display_recommendations(recommendations):
    """Display book recommendations in a nicely formatted way"""
    if not recommendations:
        print("No recommendations available.")
        return
        
    print("\n" + "=" * 80)
    print("RECOMMENDED BOOKS FOR YOU (GRAPH-BASED)")
    print("=" * 80)
    
    for i, book in enumerate(recommendations, 1):
        title = book.get("title", "Unknown Title")
        author = book.get("author", "Unknown Author")
        genres = book.get("genres", [])
        if isinstance(genres, list):
            genres = ", ".join(genres[:3])  # Show top 3 genres
        rating = book.get("rating", 0.0)
        score = book.get("score", 0.0)
        algorithm = book.get("algorithm", "unknown")
        connected_to = book.get("connected_to", [])
        
        print(f"\n{i}. {title} by {author}")
        print(f"   Genre: {genres}")
        print(f"   Rating: {rating:.1f}/5.0")
        print(f"   Match Score: {score:.4f}")
        print(f"   Algorithm: {algorithm}")
        
        if connected_to:
            print(f"   Similar to: {', '.join(connected_to[:3])}")
            
        print("-" * 80)

def main():
    """Main entry point for the graph-based book recommender."""
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Graph-based Goodreads Book Recommender")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--use_saved", action="store_true",
                      help="Use saved data instead of scraping")
    parser.add_argument("--shelf", choices=["read", "to-read", "currently-reading", "all"], 
                      default="read", help="Which shelf to use (default: read)")
    parser.add_argument("--num_recommendations", type=int, default=10,
                      help="Number of book recommendations to generate")
    parser.add_argument("--method", choices=["personalized_pagerank", "node2vec", "heuristic", "ensemble"],
                      default="personalized_pagerank", help="Recommendation method")
    parser.add_argument("--hops", type=int, default=2,
                      help="Number of hops for subgraph extraction")
    parser.add_argument("--min_edge_weight", type=int, default=1,
                      help="Minimum edge weight for subgraph extraction")
    parser.add_argument("--min_rating", type=float, default=3.5,
                      help="Minimum book rating to include in recommendations")
    parser.add_argument("--visualize", action="store_true",
                      help="Generate visualization of personal subgraph")
    parser.add_argument("--data_dir", default="graph_recommender/data",
                      help="Directory for UCSD Book Graph data")
    parser.add_argument("--download", action="store_true",
                      help="Download UCSD Book Graph data")
    parser.add_argument("--verbose", action="store_true",
                      help="Show detailed logs")
    args = parser.parse_args()
    
    # Set up logging
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Use environment variable if no user_id provided
    user_id = args.user_id or os.getenv("GOODREADS_USER_ID")
    
    if not user_id:
        logger.error("Goodreads user ID is required. Provide it with --user_id or set GOODREADS_USER_ID environment variable.")
        return
    
    # Initialize UCSD Book Graph
    ucsd_graph = UCSDBookGraph(data_dir=args.data_dir)
    
    # Download data if requested
    if args.download:
        logger.info("Downloading UCSD Book Graph data...")
        ucsd_graph.download_data()
    
    # Load UCSD Book Graph metadata
    logger.info("Loading UCSD Book Graph metadata...")
    ucsd_graph.load_book_metadata()
    
    # Get Goodreads books
    storage = DataStorage()
    books = None
    
    if args.use_saved:
        logger.info(f"Loading saved books for user {user_id}...")
        books = storage.load_books(user_id=user_id)
        
        if books is None or books.empty:
            logger.warning("No saved data found. Scraping from Goodreads instead.")
            args.use_saved = False
    
    if not args.use_saved:
        logger.info(f"Scraping Goodreads shelves for user {user_id}...")
        scraper = GoodreadsScraper(user_id)
        books = scraper.scrape_shelves(args.shelf)
    
    if books is None or books.empty:
        logger.error("No books found. Check your user ID and try again.")
        return
    
    logger.info(f"Found {len(books)} books in your Goodreads shelves.")
    
    # Map Goodreads books to UCSD Book Graph
    logger.info("Mapping Goodreads books to UCSD Book Graph...")
    mapper = BookMapper(ucsd_graph)
    mapped_books = mapper.map_goodreads_books(books)
    
    matched_count = mapped_books['ucsd_book_id'].notna().sum()
    logger.info(f"Mapped {matched_count}/{len(books)} books to UCSD Book Graph.")
    
    if matched_count == 0:
        logger.error("No books could be mapped to UCSD Book Graph. Cannot generate recommendations.")
        return
    
    # Load or build graph
    graph = ucsd_graph.get_graph()
    if graph is None:
        logger.error("Failed to load or build UCSD Book Graph.")
        return
    
    # Add user's books to graph
    graph = mapper.add_mapped_books_to_graph(mapped_books, graph)
    
    # Build personal subgraph
    logger.info(f"Building personal subgraph (hops={args.hops}, min_edge_weight={args.min_edge_weight})...")
    subgraph_builder = PersonalSubgraph(graph=graph)
    personal_graph = subgraph_builder.extract_k_hop_subgraph(
        k=args.hops,
        min_edge_weight=args.min_edge_weight
    )
    
    if personal_graph is None:
        logger.error("Failed to build personal subgraph.")
        return
    
    # Filter by rating
    if args.min_rating > 0:
        logger.info(f"Filtering personal subgraph by rating (min={args.min_rating})...")
        personal_graph = subgraph_builder.filter_by_rating(args.min_rating)
    
    # Visualize graph if requested
    if args.visualize:
        logger.info("Generating graph visualization...")
        visualization_path = subgraph_builder.visualize_graph("personal_graph.html")
        if visualization_path:
            logger.info(f"Graph visualization saved to {visualization_path}")
    
    # Generate recommendations
    logger.info(f"Generating recommendations using {args.method} method...")
    recommender = GraphRecommender(personal_graph)
    
    if args.method == "node2vec":
        # Pre-compute embeddings for node2vec
        recommender.compute_node2vec_embeddings()
    
    recommendations = recommender.get_recommendations(
        num_recommendations=args.num_recommendations,
        method=args.method
    )
    
    # Display recommendations
    display_recommendations(recommendations)

if __name__ == "__main__":
    main() 
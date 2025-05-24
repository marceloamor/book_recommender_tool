"""
Module for loading and processing the UCSD Book Graph.

The UCSD Book Graph dataset contains book metadata and book interactions
(co-purchasing, co-reading, etc.) from Amazon and Goodreads.
"""

import os
import json
import gzip
import logging
import networkx as nx
import pandas as pd
from tqdm import tqdm

logger = logging.getLogger(__name__)

class UCSDBookGraph:
    """Handles loading and processing of the UCSD Book Graph dataset."""
    
    def __init__(self, data_dir="graph_recommender/data"):
        """
        Initialize the UCSD Book Graph loader.
        
        Args:
            data_dir (str): Directory to store and load UCSD Book Graph data.
        """
        self.data_dir = data_dir
        self.graph = None
        self.book_metadata = {}
        
        # Create data directory if it doesn't exist
        os.makedirs(data_dir, exist_ok=True)
    
    def download_data(self):
        """
        Download UCSD Book Graph data if not already present.
        
        This will download the following files:
        - goodreads_books.json.gz: Book metadata
        - goodreads_interactions.csv.gz: User-book interactions
        """
        import requests
        
        # Updated URL - the dataset has moved from snap.stanford.edu to cseweb.ucsd.edu
        base_url = "https://cseweb.ucsd.edu/~jmcauley/datasets/goodreads/"
        files_to_download = [
            "goodreads_books.json.gz",
            "goodreads_interactions.csv.gz"
        ]
        
        for filename in files_to_download:
            output_path = os.path.join(self.data_dir, filename)
            
            # Skip if file already exists
            if os.path.exists(output_path):
                logger.info(f"File {filename} already exists, skipping download.")
                continue
            
            url = f"{base_url}{filename}"
            logger.info(f"Downloading {url} to {output_path}...")
            
            try:
                with requests.get(url, stream=True) as response:
                    response.raise_for_status()
                    total_size = int(response.headers.get('content-length', 0))
                    
                    with open(output_path, 'wb') as f, tqdm(
                        total=total_size, unit='B', unit_scale=True,
                        desc=filename
                    ) as progress_bar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                progress_bar.update(len(chunk))
            except requests.exceptions.HTTPError as e:
                logger.error(f"HTTP error downloading {url}: {e}")
                # Try alternative URL
                alt_base_url = "https://sites.google.com/eng.ucsd.edu/ucsdbookgraph/books"
                alt_url = f"{alt_base_url}/{filename}"
                logger.info(f"Trying alternative URL: {alt_url}")
                
                try:
                    with requests.get(alt_url, stream=True) as response:
                        response.raise_for_status()
                        total_size = int(response.headers.get('content-length', 0))
                        
                        with open(output_path, 'wb') as f, tqdm(
                            total=total_size, unit='B', unit_scale=True,
                            desc=filename
                        ) as progress_bar:
                            for chunk in response.iter_content(chunk_size=8192):
                                if chunk:
                                    f.write(chunk)
                                    progress_bar.update(len(chunk))
                except requests.exceptions.HTTPError as e2:
                    logger.error(f"Failed to download {filename} from alternative URL: {e2}")
                    logger.error("Please download the file manually from https://cseweb.ucsd.edu/~jmcauley/datasets/goodreads.html")
                    logger.error("and place it in the data directory: {self.data_dir}")
    
    def load_book_metadata(self):
        """
        Load book metadata from the goodreads_books.json.gz file.
        
        Returns:
            dict: Dictionary mapping book IDs to book metadata.
        """
        metadata_path = os.path.join(self.data_dir, "goodreads_books.json.gz")
        
        if not os.path.exists(metadata_path):
            logger.error(f"Metadata file not found: {metadata_path}")
            logger.info("Run download_data() to download the required files.")
            return {}
        
        logger.info(f"Loading book metadata from {metadata_path}...")
        book_data = {}
        
        with gzip.open(metadata_path, 'rt', encoding='utf-8') as f:
            for i, line in enumerate(tqdm(f)):
                try:
                    # Each line is a JSON object
                    book = json.loads(line.strip())
                    book_id = book.get('book_id')
                    if book_id:
                        book_data[book_id] = book
                    
                    # Process only a subset for testing (comment out for full dataset)
                    # if i >= 10000:
                    #     break
                        
                except json.JSONDecodeError:
                    logger.warning(f"Error decoding JSON on line {i+1}")
                except Exception as e:
                    logger.warning(f"Error processing line {i+1}: {e}")
        
        logger.info(f"Loaded metadata for {len(book_data)} books")
        self.book_metadata = book_data
        return book_data
    
    def build_graph(self, min_rating=3.5, max_books=None):
        """
        Build a graph from user-book interactions.
        
        Two books are connected if the same user has read and rated both positively.
        
        Args:
            min_rating (float): Minimum rating to consider a positive interaction
            max_books (int, optional): Maximum number of books to include (for testing)
            
        Returns:
            nx.Graph: The book graph
        """
        interactions_path = os.path.join(self.data_dir, "goodreads_interactions.csv.gz")
        
        if not os.path.exists(interactions_path):
            logger.error(f"Interactions file not found: {interactions_path}")
            logger.info("Run download_data() to download the required files.")
            return None
        
        logger.info(f"Loading user-book interactions from {interactions_path}...")
        
        # Load interactions
        # user_id,book_id,rating,is_read,is_reviewed
        interactions_df = pd.read_csv(interactions_path, compression='gzip')
        
        # Filter by minimum rating and is_read
        positive_interactions = interactions_df[
            (interactions_df['rating'] >= min_rating) & 
            (interactions_df['is_read'] == True)
        ]
        
        if max_books:
            # Limit to most popular books for testing
            top_books = interactions_df['book_id'].value_counts().head(max_books).index
            positive_interactions = positive_interactions[
                positive_interactions['book_id'].isin(top_books)
            ]
        
        logger.info(f"Creating graph from {len(positive_interactions)} positive interactions...")
        
        # Create an undirected graph
        G = nx.Graph()
        
        # Add books as nodes with metadata if available
        book_ids = positive_interactions['book_id'].unique()
        for book_id in book_ids:
            metadata = self.book_metadata.get(str(book_id), {})
            G.add_node(
                book_id,
                title=metadata.get('title', ''),
                author=metadata.get('authors', ''),
                rating=metadata.get('average_rating', 0.0),
                genres=metadata.get('genres', []),
                similar_books=metadata.get('similar_books', []),
                is_ucsd_node=True
            )
        
        # Group interactions by user to find co-read books
        user_books = positive_interactions.groupby('user_id')['book_id'].apply(list)
        
        # Add edges between books read by the same user
        for user_id, books in tqdm(user_books.items(), desc="Building edges"):
            if len(books) < 2:
                continue
                
            # Add edges between all pairs of books read by this user
            for i, book1 in enumerate(books):
                for book2 in books[i+1:]:
                    if G.has_edge(book1, book2):
                        # Increment weight if edge already exists
                        G[book1][book2]['weight'] += 1
                    else:
                        # Create new edge with weight 1
                        G.add_edge(book1, book2, weight=1)
        
        logger.info(f"Created graph with {G.number_of_nodes()} nodes and {G.number_of_edges()} edges")
        self.graph = G
        return G
    
    def save_graph(self, filename='book_graph.gpickle'):
        """Save the graph to a file."""
        if self.graph is None:
            logger.error("No graph to save. Call build_graph() first.")
            return False
            
        output_path = os.path.join(self.data_dir, filename)
        nx.write_gpickle(self.graph, output_path)
        logger.info(f"Graph saved to {output_path}")
        return True
    
    def load_graph(self, filename='book_graph.gpickle'):
        """Load the graph from a file."""
        input_path = os.path.join(self.data_dir, filename)
        
        if not os.path.exists(input_path):
            logger.error(f"Graph file not found: {input_path}")
            return None
            
        self.graph = nx.read_gpickle(input_path)
        logger.info(f"Loaded graph with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")
        return self.graph
    
    def get_graph(self):
        """Get the current graph or load it if not loaded."""
        if self.graph is None:
            # Try to load from file first
            graph_path = os.path.join(self.data_dir, 'book_graph.gpickle')
            if os.path.exists(graph_path):
                return self.load_graph()
            else:
                # Build from scratch if no saved graph
                self.load_book_metadata()
                return self.build_graph()
        return self.graph

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Example usage
    ucsd_graph = UCSDBookGraph()
    ucsd_graph.download_data()
    metadata = ucsd_graph.load_book_metadata()
    graph = ucsd_graph.build_graph(max_books=1000)  # Use a small subset for testing
    ucsd_graph.save_graph() 
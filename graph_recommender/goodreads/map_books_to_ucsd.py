"""
Module for mapping Goodreads books to UCSD Book Graph nodes.

This module helps match books from a user's Goodreads shelves to
nodes in the UCSD Book Graph using fuzzy matching on titles and authors.
"""

import logging
import pandas as pd
from fuzzywuzzy import fuzz
from tqdm import tqdm

logger = logging.getLogger(__name__)

class BookMapper:
    """Maps books from Goodreads to UCSD Book Graph nodes."""
    
    def __init__(self, ucsd_graph):
        """
        Initialize the book mapper.
        
        Args:
            ucsd_graph: UCSDBookGraph instance with loaded metadata
        """
        self.ucsd_graph = ucsd_graph
        self.title_to_id_map = {}
        self._build_title_map()
    
    def _build_title_map(self):
        """Build a map of normalized titles to book IDs for faster lookup."""
        if not self.ucsd_graph.book_metadata:
            logger.error("UCSD book metadata not loaded. Call ucsd_graph.load_book_metadata() first.")
            return
            
        logger.info("Building title-to-ID map for faster lookups...")
        
        for book_id, metadata in tqdm(self.ucsd_graph.book_metadata.items(), desc="Building title map"):
            # Skip if book_id is not a string
            if not isinstance(book_id, str):
                book_id = str(book_id)
                
            # Skip if metadata is not a dictionary
            if not isinstance(metadata, dict):
                continue
                
            title = metadata.get('title', '')
            if title:
                # Normalize the title
                title = self._normalize_title(title)
                
                # If multiple books have the same title, we'll keep all of them
                if title in self.title_to_id_map:
                    self.title_to_id_map[title].append(book_id)
                else:
                    self.title_to_id_map[title] = [book_id]
        
        logger.info(f"Built title map with {len(self.title_to_id_map)} unique titles")
        
        # If title map is empty, this might be local data, so add all nodes directly
        if not self.title_to_id_map and self.ucsd_graph.graph:
            logger.info("Title map is empty. Using graph nodes as fallback...")
            for node in self.ucsd_graph.graph.nodes():
                book_id = str(node)
                attrs = self.ucsd_graph.graph.nodes[node]
                title = attrs.get('title', '')
                if title:
                    title = self._normalize_title(title)
                    if title in self.title_to_id_map:
                        self.title_to_id_map[title].append(book_id)
                    else:
                        self.title_to_id_map[title] = [book_id]
            
            logger.info(f"Built fallback title map with {len(self.title_to_id_map)} unique titles from graph nodes")
    
    def _normalize_title(self, title):
        """Normalize a title for better matching."""
        if not title:
            return ""
        return title.lower().strip()
    
    def match_by_exact_title(self, goodreads_book):
        """
        Find UCSD book by exact title match.
        
        Args:
            goodreads_book: Book dict or Series from pandas DataFrame
            
        Returns:
            list: Matching UCSD book IDs or empty list if no match
        """
        if isinstance(goodreads_book, pd.Series):
            title = goodreads_book.get('title', '')
        else:
            title = goodreads_book.get('title', '')
            
        normalized_title = self._normalize_title(title)
        return self.title_to_id_map.get(normalized_title, [])
    
    def match_by_fuzzy_title(self, goodreads_book, threshold=85):
        """
        Find UCSD book by fuzzy title match.
        
        Args:
            goodreads_book: Book dict or Series from pandas DataFrame
            threshold: Minimum score (0-100) to consider a match
            
        Returns:
            list: List of (book_id, score) tuples for matches above threshold
        """
        if isinstance(goodreads_book, pd.Series):
            title = goodreads_book.get('title', '')
            author = goodreads_book.get('author', '')
        else:
            title = goodreads_book.get('title', '')
            author = goodreads_book.get('author', '')
            
        normalized_title = self._normalize_title(title)
        if not normalized_title:
            return []
            
        # First try to find exact match
        exact_matches = self.match_by_exact_title(goodreads_book)
        if exact_matches:
            # Return with perfect score
            return [(book_id, 100) for book_id in exact_matches]
        
        # If no exact match, try fuzzy matching
        matches = []
        
        # To avoid checking all titles, we'll use some heuristics
        # e.g., checking if first 3 characters match
        prefix = normalized_title[:3] if len(normalized_title) >= 3 else normalized_title
        
        for ucsd_title, book_ids in self.title_to_id_map.items():
            if not ucsd_title.startswith(prefix):
                continue
                
            # Calculate fuzzy match score
            score = fuzz.ratio(normalized_title, ucsd_title)
            
            if score >= threshold:
                # If we also have author information, use it to refine matches
                if author:
                    for book_id in book_ids:
                        metadata = self.ucsd_graph.book_metadata.get(book_id, {})
                        ucsd_author = metadata.get('authors', '')
                        if isinstance(ucsd_author, list):
                            ucsd_author = ', '.join(ucsd_author)
                        
                        # Boost score if author also matches
                        author_score = fuzz.partial_ratio(author.lower(), ucsd_author.lower())
                        combined_score = (score * 0.7) + (author_score * 0.3)
                        
                        if combined_score >= threshold:
                            matches.append((book_id, combined_score))
                else:
                    # Without author, just use title score
                    for book_id in book_ids:
                        matches.append((book_id, score))
        
        # Sort by score descending
        return sorted(matches, key=lambda x: x[1], reverse=True)
    
    def map_goodreads_books(self, goodreads_books, threshold=85):
        """
        Map books from Goodreads to UCSD Book Graph nodes.
        
        Args:
            goodreads_books: DataFrame of books from Goodreads
            threshold: Minimum score (0-100) to consider a match
            
        Returns:
            DataFrame: Original DataFrame with 'ucsd_book_id' and 'match_score' columns
        """
        if goodreads_books.empty:
            logger.warning("No Goodreads books to map")
            return goodreads_books
        
        # If the title map is empty but we have books, assume this is local data
        # In this case, just use the book_id directly as the ucsd_book_id
        if not self.title_to_id_map and not goodreads_books.empty:
            logger.info("No title map found. Using direct mapping for local data...")
            
            # Add columns for UCSD book ID and match score
            result_df = goodreads_books.copy()
            result_df['ucsd_book_id'] = None
            result_df['match_score'] = 0.0
            
            # For local data, just use the book_id as the ucsd_book_id
            for idx, book in goodreads_books.iterrows():
                book_id = book.get('book_id')
                if book_id:
                    result_df.at[idx, 'ucsd_book_id'] = str(book_id)
                    result_df.at[idx, 'match_score'] = 100.0
                    
            # Count matches
            matched_count = result_df['ucsd_book_id'].notna().sum()
            logger.info(f"Directly mapped {matched_count}/{len(goodreads_books)} books ({matched_count/len(goodreads_books)*100:.1f}%)")
            
            return result_df
        
        # Add columns for UCSD book ID and match score
        result_df = goodreads_books.copy()
        result_df['ucsd_book_id'] = None
        result_df['match_score'] = 0.0
        
        logger.info(f"Mapping {len(goodreads_books)} Goodreads books to UCSD Book Graph...")
        
        for idx, book in tqdm(goodreads_books.iterrows(), total=len(goodreads_books), desc="Mapping books"):
            matches = self.match_by_fuzzy_title(book, threshold)
            
            if matches:
                # Take the best match
                best_match = matches[0]
                result_df.at[idx, 'ucsd_book_id'] = best_match[0]
                result_df.at[idx, 'match_score'] = best_match[1]
        
        # Count matches
        matched_count = result_df['ucsd_book_id'].notna().sum()
        logger.info(f"Mapped {matched_count}/{len(goodreads_books)} books ({matched_count/len(goodreads_books)*100:.1f}%)")
        
        return result_df
    
    def add_mapped_books_to_graph(self, mapped_books, graph=None):
        """
        Add mapped Goodreads books to the graph.
        
        Args:
            mapped_books: DataFrame with 'ucsd_book_id' column
            graph: NetworkX graph to add books to (or use ucsd_graph.graph if None)
            
        Returns:
            NetworkX graph with added nodes
        """
        if graph is None:
            graph = self.ucsd_graph.get_graph()
            
        if graph is None:
            logger.error("No graph available. Load or build the graph first.")
            return None
            
        # Filter to books with valid UCSD book IDs
        valid_mapped = mapped_books[mapped_books['ucsd_book_id'].notna()]
        
        logger.info(f"Adding {len(valid_mapped)} mapped books to graph")
        
        # Add edges between the user's books
        user_read_books = set()
        
        for _, book in valid_mapped.iterrows():
            ucsd_id = book['ucsd_book_id']
            
            # If the book is already in the graph, update its attributes
            if graph.has_node(ucsd_id):
                # Mark as read by user
                graph.nodes[ucsd_id]['read_by_user'] = True
                graph.nodes[ucsd_id]['user_rating'] = float(book.get('rating', 0))
                
                # Use original book metadata but add user's data
                user_read_books.add(ucsd_id)
            else:
                # Book not in UCSD graph, add as new node
                graph.add_node(
                    ucsd_id,
                    title=book.get('title', ''),
                    author=book.get('author', ''),
                    rating=float(book.get('rating', 0)),
                    read_by_user=True,
                    user_rating=float(book.get('rating', 0)),
                    is_ucsd_node=False
                )
                user_read_books.add(ucsd_id)
        
        # Add edges between all books read by the user (if not already connected)
        book_list = list(user_read_books)
        for i, book1 in enumerate(book_list):
            for book2 in book_list[i+1:]:
                if not graph.has_edge(book1, book2):
                    graph.add_edge(book1, book2, weight=1, co_read_by_user=True)
                else:
                    # Update existing edge
                    graph[book1][book2]['co_read_by_user'] = True
                    # Increase weight to reflect user connection
                    graph[book1][book2]['weight'] += 2
        
        logger.info(f"Graph now has {graph.number_of_nodes()} nodes and {graph.number_of_edges()} edges")
        return graph 
"""
Module for generating book recommendations from a personal subgraph.

This module implements several graph-based recommendation algorithms:
1. Personalized PageRank
2. Node2Vec embeddings + cosine similarity
3. Simple heuristic recommender
"""

import logging
import numpy as np
import pandas as pd
import networkx as nx
from collections import defaultdict
from tqdm import tqdm
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)

class GraphRecommender:
    """Recommends books based on a personal subgraph."""
    
    def __init__(self, graph=None):
        """
        Initialize the graph recommender.
        
        Args:
            graph: NetworkX graph to use for recommendations
        """
        self.graph = graph
        self.embeddings = None
    
    def set_graph(self, graph):
        """Set the graph to use for recommendations."""
        self.graph = graph
        self.embeddings = None  # Reset embeddings if graph changes
    
    def _get_user_books(self):
        """Get books read by the user from the graph."""
        if self.graph is None:
            logger.error("No graph available. Set a graph first.")
            return []
            
        return [
            node for node, attrs in self.graph.nodes(data=True)
            if attrs.get('read_by_user', False)
        ]
    
    def recommend_personalized_pagerank(self, num_recommendations=10, alpha=0.85):
        """
        Generate recommendations using Personalized PageRank.
        
        Args:
            num_recommendations: Number of recommendations to generate
            alpha: PageRank damping parameter
            
        Returns:
            List of recommended books with scores
        """
        if self.graph is None:
            logger.error("No graph available. Set a graph first.")
            return []
            
        # Get user's books for personalization
        user_books = self._get_user_books()
        
        if not user_books:
            logger.warning("No user books found in the graph")
            return []
            
        # Create personalization dict (uniform across user's books)
        personalization = {}
        for book in user_books:
            personalization[book] = 1.0
            
        # For weighted PageRank, we'll use the edge weights
        # However, we need to convert to a dict format for nx.pagerank
        edge_weights = {}
        for u, v, data in self.graph.edges(data=True):
            weight = data.get('weight', 1.0)
            edge_weights[(u, v)] = weight
        
        logger.info("Running Personalized PageRank...")
        pagerank_scores = nx.pagerank(
            self.graph,
            alpha=alpha,
            personalization=personalization,
            weight='weight'
        )
        
        # Filter out books the user has already read
        user_books_set = set(user_books)
        recommendations = [
            (node, score) for node, score in pagerank_scores.items()
            if node not in user_books_set
        ]
        
        # Sort by score (descending)
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        # Convert to list of dictionaries with metadata
        result = []
        for book_id, score in recommendations[:num_recommendations]:
            book_data = self.graph.nodes[book_id]
            result.append({
                'book_id': book_id,
                'title': book_data.get('title', 'Unknown'),
                'author': book_data.get('author', 'Unknown'),
                'rating': book_data.get('rating', 0.0),
                'genres': book_data.get('genres', []),
                'score': score,
                'algorithm': 'personalized_pagerank'
            })
        
        return result
    
    def compute_node2vec_embeddings(self, dimensions=64, walk_length=30, num_walks=200, p=1, q=1):
        """
        Compute Node2Vec embeddings for the graph.
        
        Args:
            dimensions: Embedding dimensions
            walk_length: Length of each random walk
            num_walks: Number of random walks per node
            p: Return parameter (1 = neutral)
            q: In-out parameter (1 = neutral)
            
        Returns:
            Dictionary mapping node IDs to embeddings
        """
        try:
            from node2vec import Node2Vec
        except ImportError:
            logger.error("node2vec is required. Install with: pip install node2vec")
            return None
            
        if self.graph is None:
            logger.error("No graph available. Set a graph first.")
            return None
            
        logger.info(f"Computing Node2Vec embeddings (dim={dimensions}, walks={num_walks})")
        
        # Initialize Node2Vec
        node2vec = Node2Vec(
            self.graph,
            dimensions=dimensions,
            walk_length=walk_length,
            num_walks=num_walks,
            p=p,
            q=q,
            weight_key='weight',
            workers=4
        )
        
        # Train model
        model = node2vec.fit(window=10, min_count=1)
        
        # Extract embeddings
        embeddings = {}
        for node in self.graph.nodes():
            try:
                # Convert node to string for node2vec if needed
                node_key = str(node) if type(node) != str else node
                embeddings[node] = model.wv[node_key]
            except KeyError:
                logger.warning(f"No embedding found for node {node}")
        
        logger.info(f"Computed embeddings for {len(embeddings)} nodes")
        self.embeddings = embeddings
        return embeddings
    
    def recommend_node2vec(self, num_recommendations=10, compute_if_missing=True):
        """
        Generate recommendations using Node2Vec embeddings and cosine similarity.
        
        Args:
            num_recommendations: Number of recommendations to generate
            compute_if_missing: Whether to compute embeddings if not already available
            
        Returns:
            List of recommended books with scores
        """
        if self.graph is None:
            logger.error("No graph available. Set a graph first.")
            return []
            
        # Get user's books
        user_books = self._get_user_books()
        
        if not user_books:
            logger.warning("No user books found in the graph")
            return []
            
        # Compute embeddings if needed
        if self.embeddings is None:
            if compute_if_missing:
                self.compute_node2vec_embeddings()
            else:
                logger.error("No embeddings available. Call compute_node2vec_embeddings first.")
                return []
        
        # Compute average similarity to user's books for each candidate book
        similarities = defaultdict(float)
        candidates = set(self.graph.nodes()) - set(user_books)
        
        logger.info("Computing similarities to user books...")
        
        for candidate in tqdm(candidates):
            if candidate not in self.embeddings:
                continue
                
            candidate_embedding = self.embeddings[candidate]
            
            # Calculate average similarity to user's books
            total_similarity = 0.0
            count = 0
            
            for user_book in user_books:
                if user_book not in self.embeddings:
                    continue
                    
                user_book_embedding = self.embeddings[user_book]
                
                # Calculate cosine similarity
                similarity = cosine_similarity(
                    [candidate_embedding],
                    [user_book_embedding]
                )[0][0]
                
                total_similarity += similarity
                count += 1
            
            if count > 0:
                similarities[candidate] = total_similarity / count
        
        # Sort by similarity score (descending)
        recommendations = [
            (node, score) for node, score in similarities.items()
        ]
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        # Convert to list of dictionaries with metadata
        result = []
        for book_id, score in recommendations[:num_recommendations]:
            book_data = self.graph.nodes[book_id]
            result.append({
                'book_id': book_id,
                'title': book_data.get('title', 'Unknown'),
                'author': book_data.get('author', 'Unknown'),
                'rating': book_data.get('rating', 0.0),
                'genres': book_data.get('genres', []),
                'score': score,
                'algorithm': 'node2vec'
            })
        
        return result
    
    def recommend_heuristic(self, num_recommendations=10, rating_weight=0.3, connectivity_weight=0.7):
        """
        Generate recommendations using a simple heuristic approach.
        
        The score combines:
        1. Book rating
        2. Connectivity to user's books
        
        Args:
            num_recommendations: Number of recommendations to generate
            rating_weight: Weight for book rating in score
            connectivity_weight: Weight for connectivity in score
            
        Returns:
            List of recommended books with scores
        """
        if self.graph is None:
            logger.error("No graph available. Set a graph first.")
            return []
            
        # Get user's books
        user_books = self._get_user_books()
        
        if not user_books:
            logger.warning("No user books found in the graph")
            return []
            
        # Calculate connectivity score for each candidate book
        user_books_set = set(user_books)
        candidates = set(self.graph.nodes()) - user_books_set
        
        scores = {}
        
        for candidate in candidates:
            # Get rating score (normalized to 0-1)
            rating = self.graph.nodes[candidate].get('rating', 0.0)
            if isinstance(rating, str):
                try:
                    rating = float(rating)
                except ValueError:
                    rating = 0.0
                    
            rating_score = min(rating / 5.0, 1.0)
            
            # Calculate connectivity to user's books
            connectivity = 0.0
            
            for user_book in user_books:
                if self.graph.has_edge(candidate, user_book):
                    # Use edge weight if available
                    weight = self.graph[candidate][user_book].get('weight', 1.0)
                    connectivity += weight
            
            # Normalize connectivity (max 10 for reasonable scaling)
            connectivity_score = min(connectivity / 10.0, 1.0)
            
            # Calculate final score
            final_score = (
                rating_weight * rating_score +
                connectivity_weight * connectivity_score
            )
            
            scores[candidate] = final_score
        
        # Sort by score (descending)
        recommendations = [
            (node, score) for node, score in scores.items()
        ]
        recommendations.sort(key=lambda x: x[1], reverse=True)
        
        # Convert to list of dictionaries with metadata
        result = []
        for book_id, score in recommendations[:num_recommendations]:
            book_data = self.graph.nodes[book_id]
            
            # Find connected user books for explanation
            connected_user_books = []
            for user_book in user_books:
                if self.graph.has_edge(book_id, user_book):
                    user_book_title = self.graph.nodes[user_book].get('title', 'Unknown')
                    connected_user_books.append(user_book_title)
            
            result.append({
                'book_id': book_id,
                'title': book_data.get('title', 'Unknown'),
                'author': book_data.get('author', 'Unknown'),
                'rating': book_data.get('rating', 0.0),
                'genres': book_data.get('genres', []),
                'score': score,
                'connected_to': connected_user_books[:3],  # Top 3 connections
                'algorithm': 'heuristic'
            })
        
        return result
    
    def get_recommendations(self, num_recommendations=10, method='personalized_pagerank'):
        """
        Get book recommendations using the specified method.
        
        Args:
            num_recommendations: Number of recommendations to generate
            method: Recommendation method ('personalized_pagerank', 'node2vec', 'heuristic', or 'ensemble')
            
        Returns:
            List of recommended books with scores
        """
        if method == 'personalized_pagerank':
            return self.recommend_personalized_pagerank(num_recommendations)
        elif method == 'node2vec':
            return self.recommend_node2vec(num_recommendations)
        elif method == 'heuristic':
            return self.recommend_heuristic(num_recommendations)
        elif method == 'ensemble':
            # Get recommendations from all methods
            pagerank_recs = self.recommend_personalized_pagerank(num_recommendations * 2)
            heuristic_recs = self.recommend_heuristic(num_recommendations * 2)
            
            # Try node2vec if embeddings are available
            node2vec_recs = []
            if self.embeddings is not None:
                node2vec_recs = self.recommend_node2vec(num_recommendations * 2, compute_if_missing=False)
            
            # Combine and deduplicate
            all_recs = pagerank_recs + heuristic_recs + node2vec_recs
            book_id_seen = set()
            unique_recs = []
            
            for rec in all_recs:
                book_id = rec['book_id']
                if book_id not in book_id_seen:
                    book_id_seen.add(book_id)
                    unique_recs.append(rec)
                    
                    if len(unique_recs) >= num_recommendations:
                        break
            
            return unique_recs
        else:
            logger.error(f"Unknown recommendation method: {method}")
            return [] 
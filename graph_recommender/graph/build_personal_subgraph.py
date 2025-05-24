"""
Module for building a personal subgraph from the user's books.

This module extracts a k-hop subgraph from the user's read books
to create a personalized book graph for recommendations.
"""

import logging
import networkx as nx
from tqdm import tqdm

logger = logging.getLogger(__name__)

class PersonalSubgraph:
    """Builds a personal subgraph from user's books in the UCSD Book Graph."""
    
    def __init__(self, ucsd_graph=None, graph=None):
        """
        Initialize the personal subgraph builder.
        
        Args:
            ucsd_graph: UCSDBookGraph instance
            graph: Existing NetworkX graph (if already loaded)
        """
        self.ucsd_graph = ucsd_graph
        self.graph = graph
        self.personal_graph = None
    
    def get_base_graph(self):
        """Get the base graph from either provided graph or UCSD graph."""
        if self.graph is not None:
            return self.graph
        elif self.ucsd_graph is not None:
            return self.ucsd_graph.get_graph()
        else:
            logger.error("No graph available. Initialize with either ucsd_graph or graph.")
            return None
    
    def extract_k_hop_subgraph(self, k=2, min_edge_weight=1, max_nodes=1000):
        """
        Extract a k-hop subgraph from user's read books.
        
        Args:
            k: Number of hops from seed nodes (user's books)
            min_edge_weight: Minimum edge weight to include
            max_nodes: Maximum number of nodes in the subgraph
            
        Returns:
            NetworkX subgraph
        """
        base_graph = self.get_base_graph()
        if base_graph is None:
            return None
            
        # Find seed nodes (books read by the user)
        seed_nodes = [
            node for node, attrs in base_graph.nodes(data=True)
            if attrs.get('read_by_user', False)
        ]
        
        if not seed_nodes:
            logger.warning("No seed nodes (books read by user) found in the graph")
            return None
            
        logger.info(f"Found {len(seed_nodes)} seed nodes (books read by user)")
        
        # Extract the k-hop subgraph
        nodes_to_keep = set(seed_nodes)
        frontier = set(seed_nodes)
        
        for i in range(k):
            hop = i + 1
            new_frontier = set()
            
            logger.info(f"Expanding to hop {hop}...")
            
            for node in tqdm(frontier, desc=f"Hop {hop}"):
                neighbors = set(base_graph.neighbors(node))
                
                # Filter neighbors by edge weight
                if min_edge_weight > 1:
                    neighbors = {
                        neighbor for neighbor in neighbors
                        if base_graph[node][neighbor].get('weight', 0) >= min_edge_weight
                    }
                
                new_frontier.update(neighbors - nodes_to_keep)
                nodes_to_keep.update(neighbors)
                
                # Limit size of subgraph if needed
                if len(nodes_to_keep) >= max_nodes:
                    logger.info(f"Reached maximum nodes ({max_nodes}), stopping expansion")
                    break
            
            frontier = new_frontier
            
            if len(nodes_to_keep) >= max_nodes:
                break
                
            if not frontier:
                logger.info(f"No more nodes to expand at hop {hop}")
                break
        
        # Extract subgraph with these nodes
        subgraph = base_graph.subgraph(nodes_to_keep).copy()
        
        # Remove edges with weight below threshold
        if min_edge_weight > 1:
            edges_to_remove = [
                (u, v) for u, v, w in subgraph.edges(data='weight')
                if w is not None and w < min_edge_weight
            ]
            subgraph.remove_edges_from(edges_to_remove)
        
        logger.info(f"Created personal subgraph with {subgraph.number_of_nodes()} nodes and {subgraph.number_of_edges()} edges")
        self.personal_graph = subgraph
        return subgraph
    
    def filter_by_genre(self, genre_list, min_genre_match=1):
        """
        Filter the personal subgraph by genres.
        
        Args:
            genre_list: List of genres to filter by
            min_genre_match: Minimum number of matching genres required
            
        Returns:
            Filtered NetworkX subgraph
        """
        if self.personal_graph is None:
            logger.error("No personal graph available. Call extract_k_hop_subgraph first.")
            return None
            
        if not genre_list:
            logger.warning("No genres provided for filtering")
            return self.personal_graph
            
        # Normalize genres for case-insensitive matching
        normalized_genres = [g.lower() for g in genre_list]
        
        # Filter nodes by genre
        nodes_to_keep = []
        
        for node, attrs in self.personal_graph.nodes(data=True):
            # Always keep user's read books
            if attrs.get('read_by_user', False):
                nodes_to_keep.append(node)
                continue
                
            # Check genres
            node_genres = attrs.get('genres', [])
            if isinstance(node_genres, str):
                node_genres = [node_genres]
                
            normalized_node_genres = [g.lower() for g in node_genres]
            
            # Count matches
            matches = sum(1 for g in normalized_genres if g in normalized_node_genres)
            
            if matches >= min_genre_match:
                nodes_to_keep.append(node)
        
        # Extract subgraph with these nodes
        filtered_graph = self.personal_graph.subgraph(nodes_to_keep).copy()
        
        logger.info(f"Filtered personal subgraph to {filtered_graph.number_of_nodes()} nodes and {filtered_graph.number_of_edges()} edges")
        self.personal_graph = filtered_graph
        return filtered_graph
    
    def filter_by_rating(self, min_rating=3.5):
        """
        Filter the personal subgraph by book ratings.
        
        Args:
            min_rating: Minimum average rating required
            
        Returns:
            Filtered NetworkX subgraph
        """
        if self.personal_graph is None:
            logger.error("No personal graph available. Call extract_k_hop_subgraph first.")
            return None
            
        # Filter nodes by rating
        nodes_to_keep = []
        
        for node, attrs in self.personal_graph.nodes(data=True):
            # Always keep user's read books
            if attrs.get('read_by_user', False):
                nodes_to_keep.append(node)
                continue
                
            # Check rating
            rating = attrs.get('rating', 0.0)
            if isinstance(rating, str):
                try:
                    rating = float(rating)
                except ValueError:
                    rating = 0.0
            
            if rating >= min_rating:
                nodes_to_keep.append(node)
        
        # Extract subgraph with these nodes
        filtered_graph = self.personal_graph.subgraph(nodes_to_keep).copy()
        
        logger.info(f"Filtered personal subgraph to {filtered_graph.number_of_nodes()} nodes and {filtered_graph.number_of_edges()} edges")
        self.personal_graph = filtered_graph
        return filtered_graph
    
    def visualize_graph(self, output_file="personal_graph.html", max_nodes=100):
        """
        Visualize the personal subgraph using pyvis.
        
        Args:
            output_file: Path to save the HTML visualization
            max_nodes: Maximum number of nodes to visualize
            
        Returns:
            Path to the saved visualization
        """
        try:
            from pyvis.network import Network
        except ImportError:
            logger.error("pyvis is required for visualization. Install with: pip install pyvis")
            return None
            
        if self.personal_graph is None:
            logger.error("No personal graph available. Call extract_k_hop_subgraph first.")
            return None
            
        graph = self.personal_graph
        
        # If graph is too large, take a subset
        if graph.number_of_nodes() > max_nodes:
            logger.info(f"Graph has {graph.number_of_nodes()} nodes, limiting visualization to {max_nodes}")
            
            # Prioritize user's books and their immediate neighbors
            user_books = [
                node for node, attrs in graph.nodes(data=True)
                if attrs.get('read_by_user', False)
            ]
            
            # Add immediate neighbors of user's books
            neighbors = set()
            for book in user_books:
                neighbors.update(graph.neighbors(book))
            
            # Create subset of nodes
            nodes_to_keep = set(user_books)
            nodes_to_keep.update(list(neighbors)[:max_nodes - len(user_books)])
            
            # Limit to max_nodes
            if len(nodes_to_keep) > max_nodes:
                nodes_to_keep = list(nodes_to_keep)[:max_nodes]
                
            graph = graph.subgraph(nodes_to_keep).copy()
        
        # Create network
        net = Network(height="750px", width="100%", notebook=False)
        
        # Add nodes
        for node, attrs in graph.nodes(data=True):
            title = attrs.get('title', str(node))
            author = attrs.get('author', '')
            if isinstance(author, list):
                author = ', '.join(author)
                
            # Node properties
            node_title = f"{title} by {author}"
            color = "#ff5733" if attrs.get('read_by_user', False) else "#3388ff"
            size = 20 if attrs.get('read_by_user', False) else 10
            
            net.add_node(node, title=node_title, label=title, color=color, size=size)
        
        # Add edges
        for u, v, attrs in graph.edges(data=True):
            weight = attrs.get('weight', 1)
            width = min(weight, 10) / 2  # Scale for visualization
            net.add_edge(u, v, width=width, title=f"Weight: {weight}")
        
        # Generate and save the visualization
        try:
            net.save_graph(output_file)
            logger.info(f"Graph visualization saved to {output_file}")
            return output_file
        except Exception as e:
            logger.error(f"Error saving graph visualization: {e}")
            return None 
# Graph-Based Book Recommender

This module provides a graph-based approach to book recommendations using the UCSD Book Graph dataset. It extends the content-based recommender with more sophisticated graph algorithms for better recommendations.

## Key Features

- Uses the UCSD Book Graph with 1.5+ million books and user interactions
- Maps your Goodreads books to nodes in the graph
- Builds a personalized subgraph from your reading history
- Implements multiple recommendation algorithms:
  - Personalized PageRank
  - Node2Vec embeddings with cosine similarity
  - Heuristic recommendations based on connectivity
- Optional visualization of your book graph

## Usage

You can use this module in two ways:

### 1. As part of the main recommender

```bash
# Use graph-based recommendations instead of content-based
python main.py --user_id YOUR_USER_ID --graph

# Use a specific algorithm
python main.py --user_id YOUR_USER_ID --graph --method personalized_pagerank

# Visualize your book graph
python main.py --user_id YOUR_USER_ID --graph --visualize
```

### 2. Standalone usage

```bash
# Basic usage
python -m graph_recommender.main --user_id YOUR_USER_ID

# Download UCSD data (first time only)
python -m graph_recommender.main --user_id YOUR_USER_ID --download

# Advanced options
python -m graph_recommender.main --user_id YOUR_USER_ID --method node2vec --hops 3 --min_edge_weight 2
```

## Recommendation Methods

- **personalized_pagerank**: Uses Personalized PageRank to find important nodes in your book neighborhood
- **node2vec**: Creates embeddings for books and finds similar ones using cosine similarity
- **heuristic**: Uses a simple heuristic based on ratings and connectivity
- **ensemble**: Combines all methods for best results

## Requirements

- NetworkX
- Node2Vec
- PyVis (for visualization)
- FuzzyWuzzy (for title matching)
- All requirements from the main project

## Data

The UCSD Book Graph dataset will be downloaded automatically when needed. The data includes:

- Book metadata (title, author, genres, etc.)
- User-book interactions (ratings, reviews, etc.)

## How It Works

1. **Data Loading**: Downloads and processes the UCSD Book Graph dataset
2. **Book Mapping**: Maps your Goodreads books to nodes in the graph
3. **Subgraph Building**: Creates a personal subgraph from your books
4. **Recommendation**: Applies graph algorithms to find new books

## Visualization

The `--visualize` option creates an interactive HTML visualization of your book graph, showing:

- Your read books (highlighted)
- Related books from the graph
- Connections between books

## Performance Considerations

- The full UCSD dataset is large (several GB)
- Initial processing may take time
- Graph data is cached for faster subsequent runs 
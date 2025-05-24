# Goodreads Book Recommender Tool

This tool scrapes your Goodreads account for books you've read, want to read, and are currently reading, and uses that data to generate personalized book recommendations.

## Features

- Scrapes books from your Goodreads shelves (read, to-read, currently-reading)
- Analyzes your reading preferences based on your ratings and shelves
- Offers two recommendation approaches:
  - **Content-based filtering** (default): Recommends books similar to ones you've rated highly
  - **Graph-based recommendations**: Uses the UCSD Book Graph for more sophisticated recommendations
- Saves your book data locally to avoid repeated scraping
- Analyzes data structure to identify potential issues
- Optional visualization of your personal book graph

## Requirements

- Python 3.6+
- Goodreads account and user ID

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/goodreads-book-recommender.git
   cd goodreads-book-recommender
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## How to Find Your Goodreads User ID

1. Go to your Goodreads profile page
2. Look at the URL, which will be in the format: `https://www.goodreads.com/user/show/XXXXXXX-username`
3. The number (XXXXXXX) is your user ID

## Setting Up

Create a `.env` file in the project directory with your Goodreads user ID:
```
GOODREADS_USER_ID=YOUR_USER_ID
```

## Recommendation Approaches

This tool offers two different recommendation approaches:

### 1. Content-Based Filtering (Default)

- Uses TF-IDF and cosine similarity on book features (title, author, genres, description)
- Recommends books similar to ones you've rated highly
- Fast and works entirely with your own data
- Good for initial recommendations

### 2. Graph-Based Recommendations

- Uses the UCSD Book Graph with 1.5+ million books and their interactions
- Maps your Goodreads books to nodes in the graph
- Builds a personalized subgraph from your reading history
- Implements multiple recommendation algorithms:
  - Personalized PageRank
  - Node2Vec embeddings with cosine similarity
  - Heuristic recommendations based on connectivity
- More powerful and can find hidden gems
- See the [graph_recommender/README.md](graph_recommender/README.md) for more details

## Recommended Workflow

For the best experience, follow this workflow:

1. **Collect and analyze data** (takes time but only needs to be done once):
   ```
   python collect_and_analyze.py
   ```
   This will:
   - Scrape your Goodreads shelves
   - Save the data locally
   - Analyze the data structure

2. **Generate recommendations** using the saved data:
   ```
   # Content-based recommendations (default)
   python main.py --use_saved
   
   # OR Graph-based recommendations
   python main.py --use_saved --graph
   ```

## Usage Options

### Main Script

```
python main.py [options]
```

Common Options:
- `--user_id YOUR_USER_ID`: Your Goodreads user ID (optional if set in .env file)
- `--shelf SHELF`: Which shelf to scrape ("read", "to-read", "currently-reading", or "all")
- `--num_recommendations N`: Number of book recommendations to generate (default: 10)
- `--use_saved`: Use previously saved data instead of scraping again
- `--save_data`: Save scraped data for future use
- `--verbose`: Show detailed information

Graph-Based Options:
- `--graph`: Use graph-based recommender instead of content-based
- `--method METHOD`: Algorithm to use ("personalized_pagerank", "node2vec", "heuristic", or "ensemble")
- `--hops N`: Number of hops for subgraph extraction (default: 2)
- `--visualize`: Generate visualization of your personal book graph

### Graph-Based Recommender (Direct)

```
# Using the convenience wrapper script
python graph_recommender_cli.py [options]

# Or using the module directly
python -m graph_recommender.main [options]
```

Options:
- `--user_id YOUR_USER_ID`: Your Goodreads user ID (optional if set in .env file)
- `--use_saved`: Use saved data instead of scraping
- `--shelf SHELF`: Which shelf to use (default: "read")
- `--num_recommendations N`: Number of recommendations to generate
- `--method METHOD`: Recommendation method
- `--hops N`: Number of hops for subgraph extraction
- `--min_edge_weight N`: Minimum edge weight for subgraph
- `--min_rating N`: Minimum rating to include in recommendations
- `--visualize`: Generate visualization of personal subgraph
- `--download`: Download UCSD Book Graph data
- `--verbose`: Show detailed logs

### Data Collection and Analysis

```
python scripts/collect_and_analyze.py [options]
```

Options:
- `--user_id YOUR_USER_ID`: Your Goodreads user ID (optional if set in .env file)
- `--shelf SHELF`: Which shelf to scrape
- `--verbose`: Show detailed information

### Data Analysis Only

```
python scripts/analyze_data.py [options]
```

Options:
- `--user_id YOUR_USER_ID`: Your Goodreads user ID (optional if set in .env file)
- `--verbose`: Show detailed information

## How It Works

### Content-Based Filtering

1. The tool scrapes your Goodreads shelves to collect information about books.
2. It enriches this data by fetching additional details like genres and descriptions.
3. It creates feature vectors for each book based on title, author, genres, and description.
4. It calculates similarity between books using TF-IDF and cosine similarity.
5. It recommends books similar to ones you've rated highly but haven't read yet.

### Graph-Based Recommendations

1. Downloads and processes the UCSD Book Graph dataset
2. Maps your Goodreads books to nodes in the graph
3. Creates a personal subgraph from your books
4. Applies graph algorithms to find new books
5. Optional: Generates a visualization of your book graph

## Graph-Based Recommender Usage

The graph-based recommender has been updated to work more reliably with your own Goodreads data. There are now three approaches to using it:

### Option 1: Local Data with External Book Recommendations (Recommended)

This approach uses your own Goodreads data plus the Book-Crossing dataset to recommend books you haven't read yet:

```bash
# First, create the local book graph from your data
python scripts/use_local_data.py --use_saved

# Then add external books for better recommendations
python scripts/add_external_books.py --use_saved

# Now run the graph recommender to get recommendations
python main.py --graph --use_saved
```

This method:
1. Uses your existing Goodreads data to create a small graph
2. Downloads the Book-Crossing dataset to find similar books to those in your collection
3. Integrates these external books into your graph
4. Recommends new books you haven't read based on your preferences

### Option 2: Using Local Data Only

If you just want to explore your own book collection without external data:

```bash
# Create the local book graph from your data
python scripts/use_local_data.py --use_saved

# Run the graph recommender
python main.py --graph --use_saved
```

This approach works with your data only, but may show books you've already read if no new books are available.

### Option 3: Using a Small Test Dataset

For quick testing without downloading large datasets:

```bash
python scripts/download_ucsd_data.py --small
python main.py --graph --use_saved
```

This creates a tiny test graph for development and testing purposes.

### Option 4: Downloading the UCSD Book Graph Dataset

If you want to use the full UCSD Book Graph dataset, you can download a specific genre subset:

```bash
# Download the fantasy-paranormal genre subset
python scripts/download_ucsd_data.py --genre fantasy-paranormal

# Run the graph recommender with the downloaded data
python main.py --graph --use_saved
```

### Advanced Options

The graph recommender supports several algorithms:

```bash
# Use node2vec embeddings (requires more memory)
python main.py --graph --use_saved --method node2vec

# Use personalized PageRank 
python main.py --graph --use_saved --method personalized_pagerank

# Use heuristic approach (default, works best with small graphs)
python main.py --graph --use_saved --method heuristic

# Combine all approaches
python main.py --graph --use_saved --method ensemble
```

You can also adjust the number of recommendations and other parameters:

```bash
python main.py --graph --use_saved --num_recommendations 20 --min_rating 4.0 --hops 3
```

## Notes

- This tool respects Goodreads servers by adding delays between requests.
- The tool uses web scraping since Goodreads no longer provides a public API.
- The graph-based recommender works best with the local data approach for most users.
- First-time setup for the graph-based recommender takes time but subsequent runs are faster.
- The full UCSD Book Graph dataset is quite large (several GB) if you choose to download it.

## Project Structure

```
book_recommender_tool/
│
├── data/                    # Storage for book data
├── logs/                    # Log files
├── scripts/                 # Utility scripts
│   ├── collect_and_analyze.py  # Data collection and analysis
│   ├── fix_genres.py           # Genre correction script
│   └── ...                     # Other utility scripts
│
├── graph_recommender/       # Graph-based recommendation system
│   ├── data/                # UCSD Book Graph data
│   ├── goodreads/           # Goodreads integration
│   └── graph/               # Graph algorithms
│
├── main.py                  # Main CLI for content-based recommender
├── graph_recommender_cli.py # CLI for graph-based recommender
├── recommender.py           # Content-based recommendation system
├── scraper.py               # Goodreads scraper
└── data_storage.py          # Data storage utilities
```

## Troubleshooting

If you encounter issues:

1. Run `python scripts/collect_and_analyze.py --verbose` to check your data structure
2. Check the log files in the `logs/` directory
3. Make sure your `.env` file has your Goodreads user ID set correctly

## License

MIT 
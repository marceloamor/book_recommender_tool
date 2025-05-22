# Goodreads Book Recommender Tool

This tool scrapes your Goodreads account for books you've read, want to read, and are currently reading, and uses that data to generate personalized book recommendations.

## Features

- Scrapes books from your Goodreads shelves (read, to-read, currently-reading)
- Analyzes your reading preferences based on your ratings and shelves
- Generates personalized book recommendations using content-based filtering
- Supplements recommendations with popular books from Goodreads
- Saves your book data locally to avoid repeated scraping
- Analyzes data structure to identify potential issues

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
   python main.py --use_saved
   ```

## Usage Options

### Main Script

```
python main.py [options]
```

Options:
- `--user_id YOUR_USER_ID`: Your Goodreads user ID (optional if set in .env file)
- `--shelf SHELF`: Which shelf to scrape ("read", "to-read", "currently-reading", or "all")
- `--num_recommendations N`: Number of book recommendations to generate (default: 10)
- `--use_saved`: Use previously saved data instead of scraping again
- `--save_data`: Save scraped data for future use
- `--list_saved`: List all saved data files
- `--analyze_data`: Analyze saved data structure
- `--scrape_only`: Only scrape and save data, don't generate recommendations
- `--verbose`: Show detailed information

### Data Collection and Analysis

```
python collect_and_analyze.py [options]
```

Options:
- `--user_id YOUR_USER_ID`: Your Goodreads user ID (optional if set in .env file)
- `--shelf SHELF`: Which shelf to scrape
- `--verbose`: Show detailed information

### Data Analysis Only

```
python analyze_data.py [options]
```

Options:
- `--user_id YOUR_USER_ID`: Your Goodreads user ID (optional if set in .env file)
- `--verbose`: Show detailed information

## How It Works

1. The tool scrapes your Goodreads shelves to collect information about books you've read, want to read, and are currently reading.
2. It enriches this data by fetching additional details like genres and descriptions.
3. It creates feature vectors for each book based on title, author, genres, and description.
4. It calculates similarity between books using TF-IDF and cosine similarity.
5. It recommends books similar to ones you've rated highly but haven't read yet.

## Notes

- This tool respects Goodreads servers by adding delays between requests.
- The tool uses web scraping since Goodreads no longer provides a public API.
- This is for personal use only and should be used responsibly.
- The first run will take time as it needs to fetch details for each book.
- Subsequent runs using `--use_saved` will be much faster.

## Troubleshooting

If you encounter issues:

1. Run `python analyze_data.py --verbose` to check your data structure
2. Check the log files (`scraper.log` and `recommender.log`) for error messages
3. Try running `python collect_and_analyze.py` to refresh your data

## License

MIT 
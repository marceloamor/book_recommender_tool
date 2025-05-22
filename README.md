# Goodreads Book Recommender Tool

This tool scrapes your Goodreads account for books you've read, want to read, and are currently reading, and uses that data to generate personalized book recommendations.

## Features

- Scrapes books from your Goodreads shelves (read, to-read, currently-reading)
- Analyzes your reading preferences based on your ratings and shelves
- Generates personalized book recommendations using content-based filtering
- Supplements recommendations with popular books from Goodreads

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

## Usage

Run the tool with your Goodreads user ID:

```
python main.py --user_id YOUR_USER_ID
```

### Options

- `--user_id`: Your Goodreads user ID (required unless set in environment variable)
- `--shelf`: Which shelf to scrape ("read", "to-read", "currently-reading", or "all" for all shelves)
- `--num_recommendations`: Number of book recommendations to generate (default: 10)

### Using Environment Variables

You can also set your Goodreads user ID as an environment variable:

1. Create a `.env` file in the project directory:
   ```
   GOODREADS_USER_ID=YOUR_USER_ID
   ```

2. Then run the tool without the `--user_id` parameter:
   ```
   python main.py
   ```

## How It Works

1. The tool scrapes your Goodreads shelves to collect information about books you've read, want to read, and are currently reading.
2. It enriches this data by fetching additional details like genres and descriptions.
3. It creates feature vectors for each book based on title, author, and genres.
4. It calculates similarity between books using TF-IDF and cosine similarity.
5. It recommends books similar to ones you've rated highly but haven't read yet.

## Notes

- This tool respects Goodreads servers by adding delays between requests.
- The tool uses web scraping since Goodreads no longer provides a public API.
- This is for personal use only and should be used responsibly.

## License

MIT 
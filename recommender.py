"""
Book Recommender Module

This module handles generating book recommendations based on user's reading history.
"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("recommender.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BookRecommender:
    def __init__(self, user_books_df):
        """
        Initialize the recommender with user's book data
        
        Args:
            user_books_df: DataFrame containing user's books
        """
        self.user_books_df = user_books_df
        self.book_features_df = None
        self.similarity_matrix = None
        
    def get_recommendations(self, num_recommendations=10):
        """
        Generate book recommendations based on user's reading history
        
        Args:
            num_recommendations: Number of recommendations to generate
            
        Returns:
            List of recommended books
        """
        # Prepare the data
        self._prepare_data()
        
        # Find similar books
        if self.user_books_df.empty or self.book_features_df is None:
            logger.warning("No user books or feature data available")
            return []
            
        # Get books the user has read and rated highly (4+ stars)
        highly_rated = self.user_books_df[
            (self.user_books_df["shelf"] == "read") & 
            (self.user_books_df["user_rating"] >= 4)
        ]
        
        if highly_rated.empty:
            logger.info("No highly rated books found, using all read books")
            # If no highly rated books, use all read books
            highly_rated = self.user_books_df[self.user_books_df["shelf"] == "read"]
            
        if highly_rated.empty:
            logger.info("No read books found, using all books")
            # If no read books, use all books
            highly_rated = self.user_books_df
            
        logger.info(f"Using {len(highly_rated)} books as basis for recommendations")
            
        # Get recommendations based on each highly rated book
        all_recommendations = []
        
        for _, book in tqdm(highly_rated.iterrows(), total=len(highly_rated), desc="Finding similar books"):
            similar_books = self._find_similar_books(book, num_recommendations * 2)
            all_recommendations.extend(similar_books)
            
        # Remove duplicates and sort by similarity score
        unique_recommendations = {}
        for rec in all_recommendations:
            if rec["title"] not in unique_recommendations:
                unique_recommendations[rec["title"]] = rec
                
        # Sort by score and take top N
        sorted_recommendations = sorted(
            unique_recommendations.values(), 
            key=lambda x: x["score"], 
            reverse=True
        )
        
        # Filter out books the user has already read/added
        user_book_titles = set(self.user_books_df["title"].str.lower())
        filtered_recommendations = [
            rec for rec in sorted_recommendations 
            if rec["title"].lower() not in user_book_titles
        ]
        
        logger.info(f"Generated {len(filtered_recommendations)} unique recommendations")
        return filtered_recommendations[:num_recommendations]
    
    def _prepare_data(self):
        """Prepare book data for recommendation"""
        if self.user_books_df.empty:
            logger.warning("User books DataFrame is empty")
            return
            
        # Enrich data with additional book details
        self._enrich_book_data()
        
        # Fetch popular books to supplement recommendations
        popular_books = self._fetch_popular_books()
        
        # Combine user books with popular books
        all_books = pd.concat([self.user_books_df, popular_books], ignore_index=True)
        
        # Ensure all necessary columns exist
        if "title" not in all_books.columns:
            all_books["title"] = ""
            
        if "author" not in all_books.columns:
            all_books["author"] = ""
            
        if "genres" not in all_books.columns:
            all_books["genres"] = [[] for _ in range(len(all_books))]
            
        if "description" not in all_books.columns:
            all_books["description"] = ""
        
        # Create feature vectors for books
        all_books["features"] = all_books["title"].fillna("") + " " + all_books["author"].fillna("")
        
        # Add genres if available with higher weight (repeat 3 times)
        all_books["features"] = all_books.apply(
            lambda row: row["features"] + " " + 
                        (" ".join(row.get("genres", [])) + " ") * 3
            if isinstance(row.get("genres"), list) else row["features"], 
            axis=1
        )
        
        # Add description if available (with lower weight)
        all_books["features"] = all_books.apply(
            lambda row: row["features"] + " " + 
                        (str(row.get("description", ""))[:500] if row.get("description") else ""),
            axis=1
        )
        
        logger.info("Creating TF-IDF vectors")
        # Create TF-IDF vectors
        tfidf = TfidfVectorizer(
            stop_words="english", 
            max_features=5000,
            ngram_range=(1, 2)  # Use both unigrams and bigrams
        )
        
        # Handle empty features
        all_books["features"] = all_books["features"].fillna("")
        
        # Transform features to TF-IDF matrix
        try:
            tfidf_matrix = tfidf.fit_transform(all_books["features"])
            
            # Calculate similarity matrix
            logger.info("Calculating similarity matrix")
            self.similarity_matrix = cosine_similarity(tfidf_matrix)
            self.book_features_df = all_books
            
        except Exception as e:
            logger.error(f"Error creating TF-IDF matrix: {e}")
        
    def _enrich_book_data(self):
        """Fetch additional details for books"""
        logger.info("Enriching book data with additional details...")
        
        # Only process books with URLs
        books_with_urls = self.user_books_df[self.user_books_df["url"].str.len() > 0].copy()
        
        if books_with_urls.empty:
            logger.warning("No books with URLs found")
            return
            
        # Add genres column if it doesn't exist
        if "genres" not in books_with_urls.columns:
            books_with_urls["genres"] = [[] for _ in range(len(books_with_urls))]
            
        # Add description column if it doesn't exist
        if "description" not in books_with_urls.columns:
            books_with_urls["description"] = ""
            
        # Ensure these columns exist in the main DataFrame too
        if "genres" not in self.user_books_df.columns:
            self.user_books_df["genres"] = [[] for _ in range(len(self.user_books_df))]
            
        if "description" not in self.user_books_df.columns:
            self.user_books_df["description"] = ""
            
        # Fetch details for each book
        from scraper import GoodreadsScraper
        scraper = GoodreadsScraper("")  # Empty user_id as we're just using the get_book_details method
        
        # Check if we already have genre data
        missing_genres = books_with_urls["genres"].apply(lambda x: not x or len(x) == 0).sum()
        
        if missing_genres > 0:
            logger.info(f"Fetching details for {missing_genres} books missing genre data")
            
            for idx, row in tqdm(books_with_urls.iterrows(), total=len(books_with_urls), desc="Fetching book details"):
                if row["url"] and (not row["genres"] or len(row["genres"]) == 0):
                    try:
                        details = scraper.get_book_details(row["url"])
                        
                        if details:
                            books_with_urls.at[idx, "genres"] = details.get("genres", [])
                            books_with_urls.at[idx, "description"] = details.get("description", "")
                            
                        # Be nice to Goodreads servers
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"Error fetching details for book {row['title']}: {e}")
                
            # Update the main DataFrame
            for idx, row in books_with_urls.iterrows():
                try:
                    self.user_books_df.at[idx, "genres"] = row["genres"]
                    self.user_books_df.at[idx, "description"] = row["description"]
                except Exception as e:
                    logger.error(f"Error updating book data: {e}")
        else:
            logger.info("All books already have genre data")
            
        # Apply fallback genre extraction for books still missing genres
        self._apply_fallback_genre_extraction()
            
    def _apply_fallback_genre_extraction(self):
        """Extract genres from book titles and descriptions when missing"""
        missing_genres = self.user_books_df["genres"].apply(lambda x: not x or len(x) == 0).sum()
        
        if missing_genres == 0:
            return
            
        logger.info(f"Applying fallback genre extraction for {missing_genres} books")
        
        # Common genre keywords to look for
        genre_keywords = {
            "Fiction": ["novel", "fiction", "story"],
            "Fantasy": ["fantasy", "magic", "wizard", "dragon", "mythical", "myth", "fairy"],
            "Science Fiction": ["sci-fi", "science fiction", "scifi", "space", "futuristic", "alien"],
            "Mystery": ["mystery", "detective", "crime", "thriller", "suspense"],
            "Romance": ["romance", "love story", "romantic"],
            "Horror": ["horror", "scary", "ghost", "haunted", "terror"],
            "Biography": ["biography", "memoir", "autobiography", "life story"],
            "History": ["history", "historical", "ancient", "medieval"],
            "Philosophy": ["philosophy", "philosophical", "ethics", "metaphysics"],
            "Self-Help": ["self-help", "personal development", "self improvement"],
            "Business": ["business", "management", "leadership", "entrepreneur"],
            "Travel": ["travel", "adventure", "journey", "expedition"],
            "Poetry": ["poetry", "poem", "verse", "sonnet"],
            "Cooking": ["cooking", "cookbook", "recipe", "food", "baking"],
            "Art": ["art", "painting", "drawing", "artist"],
            "Young Adult": ["young adult", "ya", "teen", "teenage"],
            "Children's": ["children", "kids", "picture book"],
            "Classic": ["classic", "classics"],
            "Non-fiction": ["non-fiction", "nonfiction", "true story", "factual"]
        }
        
        for idx, row in self.user_books_df.iterrows():
            if not row["genres"] or len(row["genres"]) == 0:
                extracted_genres = []
                
                # Combine title and description for analysis
                text_to_analyze = (row["title"] + " " + row.get("description", "")).lower()
                
                # Check for genre keywords
                for genre, keywords in genre_keywords.items():
                    for keyword in keywords:
                        if keyword.lower() in text_to_analyze:
                            extracted_genres.append(genre)
                            break
                
                # If we found any genres, update the DataFrame
                if extracted_genres:
                    self.user_books_df.at[idx, "genres"] = extracted_genres
                    logger.info(f"Extracted fallback genres for '{row['title']}': {extracted_genres}")
                else:
                    # If no genres found, assign a generic "Fiction" or "Non-fiction" based on shelf
                    if row["shelf"] == "read":
                        self.user_books_df.at[idx, "genres"] = ["Fiction"]
                    else:
                        self.user_books_df.at[idx, "genres"] = ["Unknown"]
                    
        # Log the results
        still_missing = self.user_books_df["genres"].apply(lambda x: not x or len(x) == 0).sum()
        logger.info(f"After fallback extraction: {still_missing} books still missing genres")
            
    def _fetch_popular_books(self, num_books=100):
        """
        Fetch popular books from Goodreads to supplement recommendations
        
        Returns:
            DataFrame with popular books
        """
        logger.info("Fetching popular books to improve recommendations...")
        
        try:
            popular_books = []
            base_url = "https://www.goodreads.com/shelf/show/popular"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Fetch first page of popular books
            response = requests.get(base_url, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Error fetching popular books. Status code: {response.status_code}")
                return pd.DataFrame()
                
            soup = BeautifulSoup(response.text, "html.parser")
            book_elements = soup.select("div.elementList")
            
            for book_elem in book_elements[:num_books]:
                try:
                    title_elem = book_elem.select_one("a.bookTitle span")
                    title = title_elem.text.strip() if title_elem else "Unknown Title"
                    
                    author_elem = book_elem.select_one("a.authorName span")
                    author = author_elem.text.strip() if author_elem else "Unknown Author"
                    
                    url_elem = book_elem.select_one("a.bookTitle")
                    url = "https://www.goodreads.com" + url_elem["href"] if url_elem and "href" in url_elem.attrs else ""
                    
                    rating_elem = book_elem.select_one("span.greyText.smallText.rating")
                    avg_rating = 0.0
                    if rating_elem:
                        rating_text = rating_elem.text.strip()
                        rating_parts = rating_text.split("avg rating")
                        if len(rating_parts) > 1:
                            try:
                                avg_rating = float(rating_parts[0].strip())
                            except ValueError:
                                avg_rating = 0.0
                    
                    popular_books.append({
                        "title": title,
                        "author": author,
                        "url": url,
                        "avg_rating": avg_rating,
                        "user_rating": 0,  # No user rating for popular books
                        "shelf": "popular",  # Mark as popular shelf
                        "genres": []  # Will be populated later if needed
                    })
                    
                except Exception as e:
                    logger.error(f"Error extracting popular book: {e}")
                    continue
                    
            logger.info(f"Fetched {len(popular_books)} popular books")
            return pd.DataFrame(popular_books)
            
        except Exception as e:
            logger.error(f"Error fetching popular books: {e}")
            return pd.DataFrame()
            
    def _find_similar_books(self, book, num_similar=10):
        """
        Find books similar to the given book
        
        Args:
            book: Book to find similar books for
            num_similar: Number of similar books to find
            
        Returns:
            List of similar books
        """
        if self.book_features_df is None or self.similarity_matrix is None:
            logger.warning("Feature data or similarity matrix not available")
            return []
            
        # Find the index of the book
        book_indices = self.book_features_df[self.book_features_df["title"] == book["title"]].index
        
        if len(book_indices) == 0:
            logger.warning(f"Book '{book['title']}' not found in feature data")
            return []
            
        book_idx = book_indices[0]
        
        # Get similarity scores
        similarity_scores = list(enumerate(self.similarity_matrix[book_idx]))
        
        # Sort by similarity
        similarity_scores = sorted(similarity_scores, key=lambda x: x[1], reverse=True)
        
        # Get top similar books (excluding the book itself)
        similar_books = []
        for idx, score in similarity_scores[1:num_similar+1]:
            try:
                similar_book = self.book_features_df.iloc[idx]
                
                # Get genres safely
                genres = similar_book.get("genres", [])
                if isinstance(genres, list) and genres:
                    genre_str = ", ".join(genres[:3])
                else:
                    genre_str = ""
                
                similar_books.append({
                    "title": similar_book.get("title", "Unknown Title"),
                    "author": similar_book.get("author", "Unknown Author"),
                    "genre": genre_str,
                    "rating": similar_book.get("avg_rating", 0.0),
                    "link": similar_book.get("url", ""),
                    "score": float(score)
                })
            except Exception as e:
                logger.error(f"Error processing similar book: {e}")
                continue
            
        return similar_books 
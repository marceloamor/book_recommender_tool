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
            return []
            
        # Get books the user has read and rated highly (4+ stars)
        highly_rated = self.user_books_df[
            (self.user_books_df["shelf"] == "read") & 
            (self.user_books_df["user_rating"] >= 4)
        ]
        
        if highly_rated.empty:
            # If no highly rated books, use all read books
            highly_rated = self.user_books_df[self.user_books_df["shelf"] == "read"]
            
        if highly_rated.empty:
            # If no read books, use all books
            highly_rated = self.user_books_df
            
        # Get recommendations based on each highly rated book
        all_recommendations = []
        
        for _, book in highly_rated.iterrows():
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
        
        return filtered_recommendations[:num_recommendations]
    
    def _prepare_data(self):
        """Prepare book data for recommendation"""
        if self.user_books_df.empty:
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
        
        # Create feature vectors for books
        all_books["features"] = all_books["title"].fillna("") + " " + all_books["author"].fillna("")
        
        # Add genres if available
        all_books["features"] = all_books.apply(
            lambda row: row["features"] + " " + " ".join(row.get("genres", [])) 
            if isinstance(row.get("genres"), list) else row["features"], 
            axis=1
        )
        
        # Create TF-IDF vectors
        tfidf = TfidfVectorizer(stop_words="english")
        tfidf_matrix = tfidf.fit_transform(all_books["features"])
        
        # Calculate similarity matrix
        self.similarity_matrix = cosine_similarity(tfidf_matrix)
        self.book_features_df = all_books
        
    def _enrich_book_data(self):
        """Fetch additional details for books"""
        print("Enriching book data with additional details...")
        
        # Only process books with URLs
        books_with_urls = self.user_books_df[self.user_books_df["url"].str.len() > 0].copy()
        
        if books_with_urls.empty:
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
        
        for idx, row in tqdm(books_with_urls.iterrows(), total=len(books_with_urls), desc="Fetching book details"):
            if row["url"]:
                details = scraper.get_book_details(row["url"])
                
                if details:
                    books_with_urls.at[idx, "genres"] = details.get("genres", [])
                    books_with_urls.at[idx, "description"] = details.get("description", "")
                    
                # Be nice to Goodreads servers
                time.sleep(1)
                
        # Update the main DataFrame
        for idx, row in books_with_urls.iterrows():
            self.user_books_df.at[idx, "genres"] = row["genres"]
            self.user_books_df.at[idx, "description"] = row["description"]
            
    def _fetch_popular_books(self, num_books=100):
        """
        Fetch popular books from Goodreads to supplement recommendations
        
        Returns:
            DataFrame with popular books
        """
        print("Fetching popular books to improve recommendations...")
        
        try:
            popular_books = []
            base_url = "https://www.goodreads.com/shelf/show/popular"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            # Fetch first page of popular books
            response = requests.get(base_url, headers=headers)
            
            if response.status_code != 200:
                print(f"Error fetching popular books. Status code: {response.status_code}")
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
                    print(f"Error extracting popular book: {e}")
                    continue
                    
            return pd.DataFrame(popular_books)
            
        except Exception as e:
            print(f"Error fetching popular books: {e}")
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
            return []
            
        # Find the index of the book
        book_indices = self.book_features_df[self.book_features_df["title"] == book["title"]].index
        
        if len(book_indices) == 0:
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
                print(f"Error processing similar book: {e}")
                continue
            
        return similar_books 
"""
Goodreads Scraper Module

This module handles scraping book data from Goodreads shelves.
"""

import requests
import time
import re
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/scraper.log"),
    ]
)
logger = logging.getLogger(__name__)

class GoodreadsScraper:
    def __init__(self, user_id):
        self.user_id = user_id
        self.base_url = "https://www.goodreads.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
    def scrape_shelves(self, shelf="all"):
        """
        Scrape books from specified Goodreads shelf(s)
        
        Args:
            shelf: Which shelf to scrape ("read", "to-read", "currently-reading", or "all")
            
        Returns:
            DataFrame containing book information
        """
        all_books = []
        
        shelves_to_scrape = ["read", "to-read", "currently-reading"] if shelf == "all" else [shelf]
        
        for current_shelf in shelves_to_scrape:
            logger.info(f"Scraping '{current_shelf}' shelf...")
            page = 1
            while True:
                url = f"{self.base_url}/review/list/{self.user_id}?shelf={current_shelf}&page={page}"
                try:
                    response = requests.get(url, headers=self.headers)
                    
                    if response.status_code != 200:
                        logger.error(f"Error accessing page {page} of {current_shelf} shelf. Status code: {response.status_code}")
                        break
                    
                    soup = BeautifulSoup(response.text, "html.parser")
                    book_rows = soup.select("tr.bookalike")
                    
                    if not book_rows:
                        logger.info(f"No more books found on page {page} of {current_shelf} shelf")
                        break
                        
                    for book_row in book_rows:
                        book_data = self._extract_book_data(book_row, current_shelf)
                        all_books.append(book_data)
                    
                    # Check if there's a next page
                    next_button = soup.select_one("a.next_page")
                    if not next_button:
                        logger.info(f"No more pages for {current_shelf} shelf")
                        break
                        
                    page += 1
                    # Be nice to Goodreads servers
                    time.sleep(1)
                except Exception as e:
                    logger.error(f"Error scraping page {page} of {current_shelf} shelf: {e}")
                    break
        
        if not all_books:
            logger.warning("No books found across all shelves")
            return None
            
        # Convert to DataFrame
        books_df = pd.DataFrame(all_books)
        
        # Initialize genres column as empty lists
        if "genres" not in books_df.columns:
            books_df["genres"] = [[] for _ in range(len(books_df))]
            
        # Initialize description column as empty strings
        if "description" not in books_df.columns:
            books_df["description"] = ""
            
        logger.info(f"Successfully scraped {len(books_df)} books in total")
        return books_df
    
    def _extract_book_data(self, book_row, shelf):
        """Extract book information from a table row"""
        try:
            # Extract basic book info
            title_element = book_row.select_one("td.title a")
            title = title_element.text.strip() if title_element else "Unknown Title"
            book_url = title_element["href"] if title_element else ""
            
            # Clean up title (remove series info in parentheses)
            title = re.sub(r'\s*\([^)]*\)\s*$', '', title)
            
            author_element = book_row.select_one("td.author a")
            author = author_element.text.strip() if author_element else "Unknown Author"
            
            isbn_element = book_row.select_one("td.isbn div.value")
            isbn = isbn_element.text.strip() if isbn_element else ""
            
            # Extract average rating
            rating_element = book_row.select_one("td.avg_rating div.value")
            avg_rating = 0.0
            if rating_element:
                try:
                    avg_rating = float(rating_element.text.strip())
                except ValueError:
                    logger.warning(f"Could not parse average rating for '{title}'")
            
            # Extract user rating if available
            user_rating_element = book_row.select_one("td.rating div.value")
            user_rating = 0
            if user_rating_element:
                stars = user_rating_element.select("span.staticStar.p10")
                user_rating = len(stars) if stars else 0
                if user_rating == 0:
                    # Try alternative method
                    rating_text = user_rating_element.text.strip()
                    if rating_text and rating_text[0].isdigit():
                        try:
                            user_rating = int(rating_text[0])
                        except ValueError:
                            pass
            
            # Extract date read if available
            date_read_element = book_row.select_one("td.date_read div.value")
            date_read = date_read_element.text.strip() if date_read_element else ""
            
            # Get full book URL
            full_url = f"{self.base_url}{book_url}" if book_url and not book_url.startswith("http") else book_url
            
            # Extract book cover image URL
            cover_element = book_row.select_one("td.cover img")
            cover_url = cover_element["src"] if cover_element and "src" in cover_element.attrs else ""
            
            return {
                "title": title,
                "author": author,
                "isbn": isbn,
                "avg_rating": avg_rating,
                "user_rating": user_rating,
                "date_read": date_read,
                "shelf": shelf,
                "url": full_url,
                "cover_url": cover_url,
                "genres": []  # Will be populated later
            }
            
        except Exception as e:
            logger.error(f"Error extracting book data: {e}")
            return {
                "title": "Error extracting data",
                "author": "",
                "isbn": "",
                "avg_rating": 0.0,
                "user_rating": 0,
                "date_read": "",
                "shelf": shelf,
                "url": "",
                "cover_url": "",
                "genres": []
            }
    
    def get_book_details(self, book_url):
        """
        Get additional book details from book page
        
        Args:
            book_url: URL of the book page
            
        Returns:
            Dictionary with additional book details
        """
        try:
            logger.info(f"Fetching details from {book_url}")
            response = requests.get(book_url, headers=self.headers)
            if response.status_code != 200:
                logger.warning(f"Failed to fetch book details: {response.status_code}")
                return {}
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract title (as a backup)
            title_element = soup.select_one("h1#bookTitle")
            title = title_element.text.strip() if title_element else ""
            
            # NEW APPROACH: Extract genres from links with "genres" in href
            genres = []
            genre_links = soup.select("a[href*='genres']")
            
            # Skip the first link if it's just the "Genres" navigation link
            start_idx = 0
            if genre_links and "nav_brws_genres" in genre_links[0].get('href', ''):
                start_idx = 1
                
            for link in genre_links[start_idx:]:
                genre_text = link.text.strip()
                if genre_text and len(genre_text) > 1 and genre_text not in genres:
                    genres.append(genre_text)
            
            # If we still don't have genres, try other methods
            if not genres:
                # Try to find links with "shelf/show" in href
                shelf_links = soup.select("a[href*='shelf/show']")
                for link in shelf_links:
                    genre_text = link.text.strip()
                    # Skip common non-genre shelves
                    if (genre_text and len(genre_text) > 1 and 
                        genre_text.lower() not in ["to-read", "currently-reading", "read", "default", "favorites"] and
                        genre_text not in genres):
                        genres.append(genre_text)
            
            # Log the result
            if genres:
                logger.info(f"Found {len(genres)} genres for book: {title or book_url}")
                for genre in genres:
                    logger.debug(f"  - {genre}")
            else:
                logger.warning(f"No genres found for book: {title or book_url}")
                
                # Last resort: Try to extract from URL
                if "genres" in book_url:
                    try:
                        url_parts = book_url.split("/")
                        for i, part in enumerate(url_parts):
                            if part == "genres" and i+1 < len(url_parts):
                                genre = url_parts[i+1].replace("-", " ").title()
                                if genre and genre not in genres:
                                    genres.append(genre)
                                    logger.info(f"Extracted genre from URL: {genre}")
                    except Exception as e:
                        logger.error(f"Error extracting genre from URL: {e}")
            
            # Extract description
            description = ""
            # Try expanded description first
            description_elem = soup.select_one("div#description span[style='display:none']")
            if not description_elem:
                # Try visible description
                description_elem = soup.select_one("div#description span")
            
            if description_elem:
                description = description_elem.text.strip()
            
            # Extract page count
            pages = "0"
            pages_elem = soup.select_one("span[itemprop='numberOfPages']")
            if pages_elem:
                pages_match = re.search(r'\d+', pages_elem.text)
                if pages_match:
                    pages = pages_match.group(0)
            
            # Extract publication info
            pub_info = ""
            pub_elem = soup.select_one("div#details")
            if pub_elem:
                pub_info = pub_elem.text.strip()
            
            # Extract series info
            series = ""
            series_elem = soup.select_one("h2#bookSeries a")
            if series_elem:
                series = series_elem.text.strip().strip('()')
            
            return {
                "title": title,
                "genres": genres,
                "description": description,
                "pages": pages,
                "publication_info": pub_info,
                "series": series
            }
            
        except Exception as e:
            logger.error(f"Error getting book details: {e}")
            return {} 
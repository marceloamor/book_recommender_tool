"""
Goodreads Scraper Module

This module handles scraping book data from Goodreads shelves.
"""

import requests
import time
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

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
            print(f"Scraping '{current_shelf}' shelf...")
            page = 1
            while True:
                url = f"{self.base_url}/review/list/{self.user_id}?shelf={current_shelf}&page={page}"
                response = requests.get(url, headers=self.headers)
                
                if response.status_code != 200:
                    print(f"Error accessing page {page} of {current_shelf} shelf. Status code: {response.status_code}")
                    break
                
                soup = BeautifulSoup(response.text, "html.parser")
                book_rows = soup.select("tr.bookalike")
                
                if not book_rows:
                    break
                    
                for book_row in book_rows:
                    book_data = self._extract_book_data(book_row, current_shelf)
                    all_books.append(book_data)
                
                # Check if there's a next page
                next_button = soup.select_one("a.next_page")
                if not next_button:
                    break
                    
                page += 1
                # Be nice to Goodreads servers
                time.sleep(1)
        
        if not all_books:
            return None
            
        return pd.DataFrame(all_books)
    
    def _extract_book_data(self, book_row, shelf):
        """Extract book information from a table row"""
        try:
            # Extract basic book info
            title_element = book_row.select_one("td.title a")
            title = title_element.text.strip() if title_element else "Unknown Title"
            book_url = title_element["href"] if title_element else ""
            
            author_element = book_row.select_one("td.author a")
            author = author_element.text.strip() if author_element else "Unknown Author"
            
            isbn_element = book_row.select_one("td.isbn div.value")
            isbn = isbn_element.text.strip() if isbn_element else ""
            
            rating_element = book_row.select_one("td.avg_rating div.value")
            avg_rating = float(rating_element.text.strip()) if rating_element else 0.0
            
            # Extract user rating if available
            user_rating_element = book_row.select_one("td.rating div.value")
            user_rating = 0
            if user_rating_element:
                stars = user_rating_element.select("span.staticStar.p10")
                user_rating = len(stars) if stars else 0
            
            # Extract date read if available
            date_read_element = book_row.select_one("td.date_read div.value")
            date_read = date_read_element.text.strip() if date_read_element else ""
            
            # Get full book URL
            full_url = f"{self.base_url}{book_url}" if book_url and not book_url.startswith("http") else book_url
            
            return {
                "title": title,
                "author": author,
                "isbn": isbn,
                "avg_rating": avg_rating,
                "user_rating": user_rating,
                "date_read": date_read,
                "shelf": shelf,
                "url": full_url
            }
            
        except Exception as e:
            print(f"Error extracting book data: {e}")
            return {
                "title": "Error extracting data",
                "author": "",
                "isbn": "",
                "avg_rating": 0.0,
                "user_rating": 0,
                "date_read": "",
                "shelf": shelf,
                "url": ""
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
            response = requests.get(book_url, headers=self.headers)
            if response.status_code != 200:
                return {}
                
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract genres/shelves
            genres = []
            genre_elements = soup.select("div.elementList div.left a.actionLinkLite.bookPageGenreLink")
            for genre_elem in genre_elements[:5]:  # Limit to first 5 genres
                genres.append(genre_elem.text.strip())
            
            # Extract description
            description_elem = soup.select_one("div#description span[style='display:none']")
            if not description_elem:
                description_elem = soup.select_one("div#description span")
            description = description_elem.text.strip() if description_elem else ""
            
            # Extract page count
            pages_elem = soup.select_one("span[itemprop='numberOfPages']")
            pages = pages_elem.text.strip().split()[0] if pages_elem else "0"
            
            return {
                "genres": genres,
                "description": description,
                "pages": pages
            }
            
        except Exception as e:
            print(f"Error getting book details: {e}")
            return {} 
#!/usr/bin/env python3
"""
Check Goodreads Page Structure

This script downloads and saves the HTML of a Goodreads book page for inspection.
"""

import requests
import os
from bs4 import BeautifulSoup

def check_goodreads_page(url):
    """Download and save the HTML of a Goodreads book page"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    print(f"Fetching URL: {url}")
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: Failed to fetch page. Status code: {response.status_code}")
        return
    
    # Save the raw HTML
    with open("goodreads_page.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print(f"Saved raw HTML to goodreads_page.html")
    
    # Parse with BeautifulSoup
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Look for genre information using various selectors
    print("\n=== LOOKING FOR GENRES ===")
    
    # Method 1: Look for genre links in elementList
    print("\nMethod 1: div.elementList div.left a.actionLinkLite.bookPageGenreLink")
    genre_elements = soup.select("div.elementList div.left a.actionLinkLite.bookPageGenreLink")
    for i, elem in enumerate(genre_elements):
        print(f"  {i+1}. {elem.text.strip()} (href: {elem.get('href', '')})")
    
    # Method 2: Look for popular shelves
    print("\nMethod 2: a.actionLinkLite.bookPageGenreLink")
    shelf_elements = soup.select("a.actionLinkLite.bookPageGenreLink")
    for i, elem in enumerate(shelf_elements):
        print(f"  {i+1}. {elem.text.strip()} (href: {elem.get('href', '')})")
    
    # Method 3: Look for genre links in bookPageGenreLink class anywhere
    print("\nMethod 3: a.bookPageGenreLink")
    genre_elements = soup.select("a.bookPageGenreLink")
    for i, elem in enumerate(genre_elements):
        print(f"  {i+1}. {elem.text.strip()} (href: {elem.get('href', '')})")
    
    # Method 4: Look for links with "genres" in href
    print("\nMethod 4: Links with 'genres' in href")
    genre_links = soup.select("a[href*='genres']")
    for i, elem in enumerate(genre_links):
        print(f"  {i+1}. {elem.text.strip()} (href: {elem.get('href', '')})")
    
    # Method 5: Look for links with "shelf/show" in href
    print("\nMethod 5: Links with 'shelf/show' in href")
    shelf_links = soup.select("a[href*='shelf/show']")
    for i, elem in enumerate(shelf_links[:20]):  # Limit to 20 to avoid too much output
        print(f"  {i+1}. {elem.text.strip()} (href: {elem.get('href', '')})")
    
    # Look at the page structure
    print("\n=== PAGE STRUCTURE ===")
    
    # Find potential containers for genre info
    print("\nPotential genre containers:")
    containers = [
        "div.featuredBoxContents",
        "div.bigBoxContent",
        "div.bigBoxBody",
        "div.elementList",
        "div.left",
        "div.bookPageGenreLink",
        "div.stacked",
        "div.bookDetails",
        "div.uitext"
    ]
    
    for selector in containers:
        elements = soup.select(selector)
        print(f"\n{selector}: {len(elements)} elements found")
        if elements and len(elements) < 5:  # Only show if not too many
            for i, elem in enumerate(elements):
                print(f"  {i+1}. {elem.text[:100].strip()}...")

if __name__ == "__main__":
    # Example book URL
    url = "https://www.goodreads.com/book/show/13707738-boomerang"
    check_goodreads_page(url) 
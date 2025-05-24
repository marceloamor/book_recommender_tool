#!/usr/bin/env python3
"""
Download UCSD Book Graph Data

This script downloads the UCSD Book Graph data directly and places it in the correct directory.
"""

import os
import sys
import argparse
import requests
from tqdm import tqdm
import logging

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def download_file(url, output_path, desc=None):
    """Download a file with progress bar"""
    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            
            with open(output_path, 'wb') as f, tqdm(
                total=total_size, unit='B', unit_scale=True,
                desc=desc or os.path.basename(output_path)
            ) as progress_bar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        progress_bar.update(len(chunk))
        return True
    except Exception as e:
        logging.error(f"Error downloading {url}: {e}")
        return False

def main():
    # Set up logging
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/download_ucsd_data.log"),
        ]
    )
    logger = logging.getLogger(__name__)
    
    parser = argparse.ArgumentParser(description="Download UCSD Book Graph data")
    parser.add_argument("--data_dir", default="graph_recommender/data",
                      help="Directory to store UCSD Book Graph data")
    parser.add_argument("--genre", choices=["fantasy_paranormal", "romance", "history_biography", 
                                          "mystery_thriller_crime", "young_adult", "comics_graphic",
                                          "poetry", "children", "all"],
                      default="all", help="Which genre subset to download (default: all)")
    args = parser.parse_args()
    
    # Create data directory if it doesn't exist
    os.makedirs(args.data_dir, exist_ok=True)
    
    # URLs for the datasets
    base_url = "https://cseweb.ucsd.edu/~jmcauley/datasets/goodreads"
    
    if args.genre == "all":
        # Download the complete datasets
        files_to_download = [
            "goodreads_books.json.gz",
            "goodreads_interactions.csv.gz"
        ]
        urls = [f"{base_url}/{file}" for file in files_to_download]
    else:
        # Download genre-specific datasets
        files_to_download = [
            f"goodreads_books_{args.genre}.json.gz",
            f"goodreads_interactions_{args.genre}.json.gz"
        ]
        urls = [f"{base_url}/{file}" for file in files_to_download]
    
    # Download each file
    for url, filename in zip(urls, files_to_download):
        output_path = os.path.join(args.data_dir, filename)
        
        # Skip if file already exists
        if os.path.exists(output_path):
            logger.info(f"File {filename} already exists, skipping download.")
            continue
        
        logger.info(f"Downloading {url} to {output_path}...")
        
        # Try primary URL
        success = download_file(url, output_path)
        
        # If primary URL failed, try alternative URLs
        if not success:
            # Alternative URL 1: UCSD Book Graph Google Site
            alt_url1 = f"https://sites.google.com/eng.ucsd.edu/ucsdbookgraph/{args.genre}/{filename}"
            logger.info(f"Trying alternative URL: {alt_url1}")
            success = download_file(alt_url1, output_path)
            
            if not success:
                # Alternative URL 2: Different pattern on cseweb
                alt_url2 = f"{base_url}/{args.genre}/{filename}"
                logger.info(f"Trying alternative URL: {alt_url2}")
                success = download_file(alt_url2, output_path)
            
            if not success:
                logger.error(f"Failed to download {filename} from all sources")
                logger.error("Please download the file manually from https://cseweb.ucsd.edu/~jmcauley/datasets/goodreads.html")
                logger.error(f"and place it in the data directory: {args.data_dir}")
                continue
        
        logger.info(f"Successfully downloaded {filename}")
    
    logger.info("Download complete.")
    
if __name__ == "__main__":
    main() 
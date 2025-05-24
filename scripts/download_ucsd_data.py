#!/usr/bin/env python3
"""
Download UCSD Book Graph Data

This script downloads the UCSD Book Graph data directly and places it in the correct directory.
Based on the official MengtingWan/goodreads repository.
"""

import os
import sys
import argparse
import requests
from tqdm import tqdm
import logging
import gzip
import zipfile
import shutil

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
    parser.add_argument("--genre", choices=["fantasy-paranormal", "romance", "history-biography", 
                                          "mystery-thriller-crime", "young-adult", "comics-graphic",
                                          "poetry", "children", "all"],
                      default="all", help="Which genre subset to download (default: all)")
    parser.add_argument("--small", action="store_true", 
                      help="Use a small subset for testing")
    args = parser.parse_args()
    
    # Create data directory if it doesn't exist
    os.makedirs(args.data_dir, exist_ok=True)
    
    # Official URLs from the MengtingWan/goodreads repository
    # Base URLs for different domains
    base_urls = {
        "cseweb": "https://cseweb.ucsd.edu/~jmcauley/datasets/goodreads",
        "drive1": "https://drive.google.com/uc?export=download&id=",
        "drive2": "https://drive.google.com/uc?export=download&confirm=t&id="
    }
    
    # Drive IDs from the repository
    drive_ids = {
        "all": {
            "books": "1CC3elHD7cGQcBoFi7-rRi7htnONrg2X3",
            "interactions": "1zmylV7XW2dfQVCLeg1LbllfQtHD2KTVn"
        },
        "children": {
            "books": "19I1JtzcNS6lLzEQk-q_D7-j1nZNhcAqx",
            "interactions": "1J3cbr_pNs-4RN33dF4TmmkKGzQgMiGbG",
            "reviews": "1na1sI5x8gCIRJd_J_708eKVfaBBT6d-B"
        },
        "comics-graphic": {
            "books": "1OWbm-Z5EHIsXcNeGYdlC9oJN_fGiBInj",
            "interactions": "1mf4aIqsZs0JZOlJQl8DZ4FDMF17416ku",
            "reviews": "1uX0Uk-Archond-BRKBtJQDcQYtAOBG6F"
        },
        "fantasy-paranormal": {
            "books": "1NNn_oZdlotLCvZA7c8P6MN0AZTZ_x0WH",
            "interactions": "18zVbHE4Sp_2YKbOBdd1vWU6R1g7MAgjo",
            "reviews": "1OlR5kHdFnuGVbXmgRnGaQFgWEPeJaNmY"
        },
        "history-biography": {
            "books": "1I-WhufJfL4_2Wl-XKouLM5CE-Uk7gGCL",
            "interactions": "1CHTAaNY-tHlNw1e4VzN85SlqQ3NLSWQ5",
            "reviews": "1U8Q5eurGcHgzXE-C8VbqT41V_l-QZvnW"
        },
        "mystery-thriller-crime": {
            "books": "1OUF4VQ5thKUkKbfAsxoZ-7XiQIgf7UIB",
            "interactions": "1yigEQO6pnK6JQsGqanNc0yGmMf745CWI",
            "reviews": "1YQEVc2liUJYHVRzXogrI-1_V_MhDZMPG"
        },
        "poetry": {
            "books": "1YG8EJ-63D8BiyyNmMkuADZlkQQL1XYXd",
            "interactions": "1XNrJMn3UZDtL7XLwRRoHKkV1iUnbpQzi",
            "reviews": "1OGNrk8kR27HVznFAqBAmMuLLfrYzR-fc"
        },
        "romance": {
            "books": "1Dr_COr8X9CUP-H-nl8COuKZukTOGBT0M",
            "interactions": "1Pp-zM-MOZiN4diOIiXmN6CLo93pAFwIZ",
            "reviews": "1WtI99ZGKEjI_fReEikGJYLHCUtoVbhJQ"
        },
        "young-adult": {
            "books": "1BftH_-hUzdIAqpFjEkYLnrAkbyRXKNIP",
            "interactions": "16lbcEztQvN3UYvGyqMKYGZgB83kFVVNM",
            "reviews": "1FNRw3uZdkOIMxXQa_OJXRoFh1g0XwXCv"
        }
    }
    
    # Define files to download based on genre
    genre = args.genre
    if genre == "all":
        files_to_download = [
            {"name": "goodreads_books.json.gz", "type": "books"},
            {"name": "goodreads_interactions.csv", "type": "interactions"}
        ]
    else:
        files_to_download = [
            {"name": f"goodreads_books_{genre}.json.gz", "type": "books"},
            {"name": f"goodreads_interactions_{genre}.json.gz", "type": "interactions"}
        ]
    
    # Download each file
    for file_info in files_to_download:
        filename = file_info["name"]
        file_type = file_info["type"]
        output_path = os.path.join(args.data_dir, filename)
        
        # Skip if file already exists
        if os.path.exists(output_path):
            logger.info(f"File {filename} already exists, skipping download.")
            continue
        
        logger.info(f"Attempting to download {filename}...")
        success = False
        
        # Try CSEWEB URL first
        cseweb_url = f"{base_urls['cseweb']}/{filename}"
        logger.info(f"Trying URL: {cseweb_url}")
        success = download_file(cseweb_url, output_path)
        
        # If CSEWEB fails, try Google Drive
        if not success and genre in drive_ids and file_type in drive_ids[genre]:
            drive_id = drive_ids[genre][file_type]
            drive_url = f"{base_urls['drive1']}{drive_id}"
            logger.info(f"Trying Google Drive URL: {drive_url}")
            success = download_file(drive_url, output_path)
            
            # If first Drive URL fails, try with confirm parameter
            if not success:
                drive_url = f"{base_urls['drive2']}{drive_id}"
                logger.info(f"Trying alternate Google Drive URL: {drive_url}")
                success = download_file(drive_url, output_path)
        
        # If all direct downloads fail but we need small test files
        if not success and args.small:
            logger.info(f"Creating small test file for {filename}")
            if "books" in filename:
                # Create a small test file with a few books
                with gzip.open(output_path, 'wt') as f:
                    f.write('{"book_id": "1", "title": "Test Book 1", "authors": [{"author_id": "1", "name": "Test Author"}], "average_rating": 4.5}\n')
                    f.write('{"book_id": "2", "title": "Test Book 2", "authors": [{"author_id": "2", "name": "Another Author"}], "average_rating": 3.5}\n')
            elif "interactions" in filename:
                # Create a small test file with a few interactions
                with open(output_path, 'w') as f:
                    f.write("user_id,book_id,rating,is_read,is_reviewed\n")
                    f.write("1,1,5,True,False\n")
                    f.write("1,2,4,True,False\n")
                    f.write("2,1,3,True,False\n")
            logger.info(f"Created test file for {filename}")
            success = True
        
        if success:
            logger.info(f"Successfully processed {filename}")
        else:
            logger.error(f"Failed to download {filename}")
            logger.error("Please visit https://github.com/MengtingWan/goodreads for manual download instructions")
    
    # If we're using the small test option, create a small graph and save it
    if args.small and not os.path.exists(os.path.join(args.data_dir, "book_graph.gpickle")):
        logger.info("Creating a small test graph")
        try:
            import networkx as nx
            
            # Create a simple graph with 2 nodes
            G = nx.Graph()
            
            # Add nodes with metadata
            G.add_node(
                "1",
                title="Test Book 1",
                author="Test Author",
                rating=4.5,
                genres=["Fiction", "Fantasy"],
                similar_books=[],
                is_ucsd_node=True
            )
            
            G.add_node(
                "2",
                title="Test Book 2",
                author="Another Author",
                rating=3.5,
                genres=["Fiction", "Mystery"],
                similar_books=[],
                is_ucsd_node=True
            )
            
            # Add an edge between the two books
            G.add_edge("1", "2", weight=1)
            
            # Save the graph
            graph_path = os.path.join(args.data_dir, "book_graph.gpickle")
            nx.write_gpickle(G, graph_path)
            logger.info(f"Created test graph and saved to {graph_path}")
        except ImportError:
            logger.error("Could not create test graph: networkx not installed")
    
    logger.info("Download process complete.")

if __name__ == "__main__":
    main() 
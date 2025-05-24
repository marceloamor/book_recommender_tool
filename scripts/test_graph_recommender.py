#!/usr/bin/env python3
"""
Test Graph Recommender

This script tests that the graph recommender is working properly.
"""

import os
import sys
import argparse
from dotenv import load_dotenv
import logging

# Add parent directory to path so we can import modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def main():
    # Set up logging
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("logs/test_graph_recommender.log"),
        ]
    )
    logger = logging.getLogger(__name__)
    
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Test Graph Recommender")
    parser.add_argument("--user_id", help="Your Goodreads user ID")
    parser.add_argument("--download", action="store_true",
                      help="Download UCSD Book Graph data")
    parser.add_argument("--use_saved", action="store_true",
                      help="Use saved data instead of scraping")
    parser.add_argument("--verbose", action="store_true",
                      help="Show detailed logs")
    args = parser.parse_args()
    
    # Use environment variable if no user_id provided
    user_id = args.user_id or os.getenv("GOODREADS_USER_ID")
    
    if not user_id:
        logger.error("Goodreads user ID is required. Provide it with --user_id or set GOODREADS_USER_ID environment variable.")
        return 1
    
    logger.info("Testing graph recommender import...")
    try:
        from graph_recommender.main import main as graph_main
        logger.info("Successfully imported graph_main")
    except ImportError as e:
        logger.error(f"Failed to import graph_main: {e}")
        return 1
    
    logger.info("Testing command line execution...")
    
    # Build command
    cmd = [sys.executable, "-m", "graph_recommender.main"]
    cmd.extend(["--user_id", user_id])
    
    if args.download:
        cmd.append("--download")
    
    if args.use_saved:
        cmd.append("--use_saved")
    
    if args.verbose:
        cmd.append("--verbose")
    
    # Limit recommendations for testing
    cmd.extend(["--num_recommendations", "3"])
    
    # Execute command
    import subprocess
    logger.info(f"Executing: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        logger.info("Command executed successfully")
        logger.info(f"Output: {result.stdout}")
        return 0
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed with exit code {e.returncode}")
        logger.error(f"Error output: {e.stderr}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 
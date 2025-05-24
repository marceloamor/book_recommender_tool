#!/usr/bin/env python3
"""
Command-line interface for the graph-based book recommender.

This is a wrapper script to make it easier to run the graph-based recommender directly.
"""

import os
import sys
import logging
from dotenv import load_dotenv

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    # Load environment variables from .env file
    load_dotenv()
    
    # Check if user_id is provided in command line
    if "--user_id" not in sys.argv and "-u" not in sys.argv:
        # Get user_id from environment variable
        user_id = os.getenv("GOODREADS_USER_ID")
        if user_id:
            # Add to command line arguments
            sys.argv.extend(["--user_id", user_id])
        else:
            logger.error("Goodreads user ID is required. Provide it with --user_id or set GOODREADS_USER_ID environment variable.")
            sys.exit(1)
    
    try:
        # Import and call the graph recommender's main function
        logger.info("Starting graph-based book recommender...")
        from graph_recommender.main import main as graph_main
        graph_main()
    except ImportError as e:
        logger.error(f"Error importing graph recommender: {e}")
        logger.error("Make sure the graph_recommender package is installed correctly.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error running graph recommender: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
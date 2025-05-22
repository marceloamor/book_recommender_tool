"""
Data Storage Module

This module handles saving and loading book data to/from disk.
"""

import os
import json
import pandas as pd
from datetime import datetime

class DataStorage:
    def __init__(self, data_dir="data"):
        """
        Initialize the data storage
        
        Args:
            data_dir: Directory to store data files
        """
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
    
    def save_books(self, books_df, user_id):
        """
        Save books DataFrame to disk
        
        Args:
            books_df: DataFrame containing book data
            user_id: Goodreads user ID
        """
        if books_df is None or books_df.empty:
            print("No books to save.")
            return False
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.data_dir}/books_{user_id}_{timestamp}.csv"
        
        try:
            # Save to CSV
            books_df.to_csv(filename, index=False)
            print(f"Saved {len(books_df)} books to {filename}")
            return True
        except Exception as e:
            print(f"Error saving books: {e}")
            return False
    
    def load_books(self, filename=None, user_id=None):
        """
        Load books from disk
        
        Args:
            filename: Specific filename to load
            user_id: Goodreads user ID to load latest data for
            
        Returns:
            DataFrame containing book data
        """
        if filename:
            # Load specific file
            try:
                return pd.read_csv(filename)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                return None
        
        if user_id:
            # Find latest file for user_id
            files = [f for f in os.listdir(self.data_dir) if f.startswith(f"books_{user_id}_") and f.endswith(".csv")]
            
            if not files:
                print(f"No saved data found for user {user_id}")
                return None
            
            # Sort by timestamp (newest first)
            files.sort(reverse=True)
            latest_file = os.path.join(self.data_dir, files[0])
            
            try:
                print(f"Loading data from {latest_file}")
                return pd.read_csv(latest_file)
            except Exception as e:
                print(f"Error loading {latest_file}: {e}")
                return None
        
        print("Either filename or user_id must be provided")
        return None
    
    def list_saved_data(self):
        """
        List all saved data files
        
        Returns:
            List of data files
        """
        files = [f for f in os.listdir(self.data_dir) if f.endswith(".csv")]
        return files 
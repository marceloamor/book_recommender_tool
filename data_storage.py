"""
Data Storage Module

This module handles saving and loading book data to/from disk.
"""

import os
import json
import pandas as pd
from datetime import datetime
import pickle

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
        csv_filename = f"{self.data_dir}/books_{user_id}_{timestamp}.csv"
        pickle_filename = f"{self.data_dir}/books_{user_id}_{timestamp}.pkl"
        
        try:
            # Save to CSV for human-readable format
            books_df.to_csv(csv_filename, index=False)
            
            # Save to pickle for preserving complex data types
            with open(pickle_filename, 'wb') as f:
                pickle.dump(books_df, f)
                
            print(f"Saved {len(books_df)} books to {csv_filename} and {pickle_filename}")
            
            # Save a reference to the latest file
            latest_ref = f"{self.data_dir}/latest_{user_id}.txt"
            with open(latest_ref, 'w') as f:
                f.write(f"{timestamp}")
                
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
                if filename.endswith('.pkl'):
                    with open(filename, 'rb') as f:
                        return pickle.load(f)
                else:
                    return pd.read_csv(filename)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
                return None
        
        if user_id:
            # Check if we have a reference to the latest file
            latest_ref = f"{self.data_dir}/latest_{user_id}.txt"
            if os.path.exists(latest_ref):
                try:
                    with open(latest_ref, 'r') as f:
                        timestamp = f.read().strip()
                    
                    pickle_file = f"{self.data_dir}/books_{user_id}_{timestamp}.pkl"
                    if os.path.exists(pickle_file):
                        print(f"Loading data from {pickle_file}")
                        with open(pickle_file, 'rb') as f:
                            return pickle.load(f)
                except Exception as e:
                    print(f"Error loading latest reference: {e}")
            
            # If no reference or loading failed, find latest pickle file
            pickle_files = [f for f in os.listdir(self.data_dir) 
                          if f.startswith(f"books_{user_id}_") and f.endswith(".pkl")]
            
            if pickle_files:
                # Sort by timestamp (newest first)
                pickle_files.sort(reverse=True)
                latest_file = os.path.join(self.data_dir, pickle_files[0])
                
                try:
                    print(f"Loading data from {latest_file}")
                    with open(latest_file, 'rb') as f:
                        return pickle.load(f)
                except Exception as e:
                    print(f"Error loading {latest_file}: {e}")
            
            # If no pickle files or loading failed, try CSV files
            csv_files = [f for f in os.listdir(self.data_dir) 
                       if f.startswith(f"books_{user_id}_") and f.endswith(".csv")]
            
            if not csv_files:
                print(f"No saved data found for user {user_id}")
                return None
            
            # Sort by timestamp (newest first)
            csv_files.sort(reverse=True)
            latest_file = os.path.join(self.data_dir, csv_files[0])
            
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
        files = [f for f in os.listdir(self.data_dir) 
               if f.endswith(".csv") or f.endswith(".pkl")]
        return files
        
    def analyze_data_structure(self, user_id=None):
        """
        Analyze the structure of saved data
        
        Args:
            user_id: Goodreads user ID to analyze data for
            
        Returns:
            Dictionary with data structure information
        """
        books_df = self.load_books(user_id=user_id)
        if books_df is None or books_df.empty:
            return {"error": "No data found"}
        
        # Get basic info
        info = {
            "num_books": len(books_df),
            "columns": list(books_df.columns),
            "sample_rows": books_df.head(5).to_dict('records'),
            "missing_values": books_df.isnull().sum().to_dict(),
            "column_types": {col: str(books_df[col].dtype) for col in books_df.columns}
        }
        
        # Check for specific columns
        for col in ["title", "author", "genres", "avg_rating", "user_rating"]:
            if col in books_df.columns:
                if col == "genres":
                    # Check structure of genres
                    sample_genres = books_df[col].head(10).tolist()
                    info[f"{col}_samples"] = sample_genres
                else:
                    info[f"{col}_samples"] = books_df[col].head(10).tolist()
        
        return info 
#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from db import supabase

def clear_database():
    """Clear all data from Supabase tables"""
    
    print("Clearing Supabase database...")
    
    try:
        # Clear content_tickers first (has foreign key references)
        result = supabase.table("content_tickers").delete().neq("id", 0).execute()
        print(f"Cleared content_tickers table: {len(result.data)} rows deleted")
        
        # Clear comments table
        result = supabase.table("comments").delete().neq("reddit_id", "").execute()
        print(f"Cleared comments table: {len(result.data)} rows deleted")
        
        # Clear posts table
        result = supabase.table("posts").delete().neq("reddit_id", "").execute()
        print(f"Cleared posts table: {len(result.data)} rows deleted")
        
        print("✅ Database cleared successfully!")
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")
        return False
    
    return True

if __name__ == "__main__":
    clear_database()
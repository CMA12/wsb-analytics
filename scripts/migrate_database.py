#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from db import supabase

def migrate_database():
    """
    Add missing columns to the content_tickers table for LLM extraction support.
    
    This migration adds:
    - hype_score: DECIMAL column for sentiment hype score (0.0 to 1.0)
    - company_name: TEXT column for full company name from LLM
    """
    
    print("🔧 Starting database schema migration...")
    
    try:
        # Note: Supabase doesn't allow direct DDL operations via the Python client
        # These would need to be run in the Supabase SQL editor or via psql
        
        print("📋 SQL commands to run in Supabase SQL editor:")
        print("="*60)
        
        sql_commands = [
            "-- Add hype_score column (decimal for sentiment analysis)",
            "ALTER TABLE content_tickers ADD COLUMN IF NOT EXISTS hype_score DECIMAL(4,2) DEFAULT 0.0;",
            "",
            "-- Add company_name column (text for full company name)",
            "ALTER TABLE content_tickers ADD COLUMN IF NOT EXISTS company_name TEXT DEFAULT '';",
            "",
            "-- Create index on hype_score for performance",
            "CREATE INDEX IF NOT EXISTS idx_content_tickers_hype_score ON content_tickers(hype_score);",
            "",
            "-- Create index on company_name for searches", 
            "CREATE INDEX IF NOT EXISTS idx_content_tickers_company_name ON content_tickers(company_name);",
            "",
            "-- Verify the new columns were added",
            "SELECT column_name, data_type, is_nullable, column_default",
            "FROM information_schema.columns", 
            "WHERE table_name = 'content_tickers' AND column_name IN ('hype_score', 'company_name');"
        ]
        
        for cmd in sql_commands:
            print(cmd)
        
        print("="*60)
        print("\n📌 INSTRUCTIONS:")
        print("1. Copy the SQL commands above")
        print("2. Go to your Supabase dashboard → SQL Editor")
        print("3. Paste and run the commands")
        print("4. Verify the columns were added using the SELECT statement")
        
        # Test if we can query the table structure (this will fail if columns don't exist)
        print("\n🔍 Testing current table structure...")
        try:
            # Try to query with new columns - this will show us if they exist
            result = supabase.table("content_tickers").select("ticker, hype_score, company_name").limit(1).execute()
            print("✅ New columns already exist in database!")
            return True
        except Exception as e:
            if "column" in str(e).lower() and "does not exist" in str(e).lower():
                print("⚠️ New columns do not exist yet - please run the SQL commands above")
                return False
            else:
                print(f"❌ Unexpected error: {e}")
                return False
                
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

if __name__ == "__main__":
    migrate_database()
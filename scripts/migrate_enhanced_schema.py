#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from db import supabase

def migrate_enhanced_schema():
    """
    Enhanced database schema migration for time-series hype tracking.
    
    This migration adds:
    - processed_at columns to posts and comments for incremental processing
    - created_at column to content_tickers for time tracking
    - tickers table for aggregation and time-series data
    - ticker_daily_stats table for historical trend analysis
    """
    
    print("🔧 Starting ENHANCED database schema migration...")
    
    try:
        print("📋 SQL commands to run in Supabase SQL editor:")
        print("="*80)
        
        sql_commands = [
            "-- PHASE 1: Add missing columns to content_tickers table",
            "ALTER TABLE content_tickers ADD COLUMN IF NOT EXISTS hype_score DECIMAL(4,2) DEFAULT 0.0;",
            "ALTER TABLE content_tickers ADD COLUMN IF NOT EXISTS company_name TEXT DEFAULT '';",
            "ALTER TABLE content_tickers ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();",
            "ALTER TABLE content_tickers ADD COLUMN IF NOT EXISTS inheritance_source TEXT;",
            "ALTER TABLE content_tickers ADD COLUMN IF NOT EXISTS context_post_id TEXT;",
            "",
            "-- PHASE 2: Add processing tracking columns",
            "ALTER TABLE posts ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP NULL;",
            "ALTER TABLE comments ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP NULL;",
            "",
            "-- PHASE 3: Create ticker aggregation table",
            "CREATE TABLE IF NOT EXISTS tickers (",
            "  ticker TEXT PRIMARY KEY,",
            "  company_name TEXT,",
            "  total_mentions INTEGER DEFAULT 0,",
            "  total_posts INTEGER DEFAULT 0,",
            "  total_comments INTEGER DEFAULT 0,",
            "  avg_hype_score DECIMAL(4,2) DEFAULT 0.0,",
            "  max_hype_score DECIMAL(4,2) DEFAULT 0.0,",
            "  last_mentioned_at TIMESTAMP,",
            "  created_at TIMESTAMP DEFAULT NOW(),",
            "  updated_at TIMESTAMP DEFAULT NOW()",
            ");",
            "",
            "-- PHASE 4: Create daily statistics table for time-series",
            "CREATE TABLE IF NOT EXISTS ticker_daily_stats (",
            "  ticker TEXT,",
            "  date DATE,",
            "  mentions_count INTEGER DEFAULT 0,",
            "  posts_count INTEGER DEFAULT 0,",
            "  comments_count INTEGER DEFAULT 0,",
            "  avg_hype_score DECIMAL(4,2) DEFAULT 0.0,",
            "  max_hype_score DECIMAL(4,2) DEFAULT 0.0,",
            "  total_engagement INTEGER DEFAULT 0,",
            "  created_at TIMESTAMP DEFAULT NOW(),",
            "  PRIMARY KEY (ticker, date)",
            ");",
            "",
            "-- PHASE 5: Create performance indexes",
            "CREATE INDEX IF NOT EXISTS idx_posts_processed_at ON posts(processed_at);",
            "CREATE INDEX IF NOT EXISTS idx_comments_processed_at ON comments(processed_at);",
            "CREATE INDEX IF NOT EXISTS idx_content_tickers_created_at ON content_tickers(created_at);",
            "CREATE INDEX IF NOT EXISTS idx_content_tickers_ticker_created ON content_tickers(ticker, created_at);",
            "CREATE INDEX IF NOT EXISTS idx_tickers_mentions ON tickers(total_mentions DESC);",
            "CREATE INDEX IF NOT EXISTS idx_tickers_hype ON tickers(avg_hype_score DESC);",
            "CREATE INDEX IF NOT EXISTS idx_tickers_updated ON tickers(updated_at);",
            "CREATE INDEX IF NOT EXISTS idx_daily_stats_date ON ticker_daily_stats(date DESC);",
            "CREATE INDEX IF NOT EXISTS idx_daily_stats_ticker_date ON ticker_daily_stats(ticker, date);",
            "",
            "-- Add indexes for new content_tickers columns",
            "CREATE INDEX IF NOT EXISTS idx_content_tickers_hype_score ON content_tickers(hype_score);",
            "CREATE INDEX IF NOT EXISTS idx_content_tickers_company_name ON content_tickers(company_name);",
            "",
            "-- PHASE 6: Create trigger for updating tickers table updated_at",
            "CREATE OR REPLACE FUNCTION update_ticker_updated_at()",
            "RETURNS TRIGGER AS $$",
            "BEGIN",
            "  NEW.updated_at = NOW();",
            "  RETURN NEW;",
            "END;",
            "$$ LANGUAGE plpgsql;",
            "",
            "DROP TRIGGER IF EXISTS trigger_update_ticker_updated_at ON tickers;",
            "CREATE TRIGGER trigger_update_ticker_updated_at",
            "  BEFORE UPDATE ON tickers",
            "  FOR EACH ROW",
            "  EXECUTE FUNCTION update_ticker_updated_at();",
            "",
            "-- VERIFICATION QUERIES",
            "-- Check new columns exist",
            "SELECT column_name, data_type, is_nullable",
            "FROM information_schema.columns",
            "WHERE table_name IN ('posts', 'comments', 'content_tickers', 'tickers', 'ticker_daily_stats')",
            "ORDER BY table_name, column_name;",
            "",
            "-- Check tables exist",
            "SELECT table_name FROM information_schema.tables",
            "WHERE table_name IN ('tickers', 'ticker_daily_stats')",
            "AND table_schema = 'public';"
        ]
        
        for cmd in sql_commands:
            print(cmd)
        
        print("="*80)
        print("\n📌 MIGRATION INSTRUCTIONS:")
        print("1. Copy ALL SQL commands above")
        print("2. Go to your Supabase dashboard → SQL Editor")
        print("3. Paste and run the commands")
        print("4. Verify tables and columns were created using the verification queries")
        print("5. Run this script again to test the migration")
        
        # Test if migration has been applied
        print("\n🔍 Testing current schema...")
        test_migration()
        
    except Exception as e:
        print(f"❌ Migration error: {e}")
        return False

def test_migration():
    """Test if the enhanced schema migration has been applied"""
    
    tests = [
        ("posts.processed_at", lambda: supabase.table("posts").select("processed_at").limit(1).execute()),
        ("comments.processed_at", lambda: supabase.table("comments").select("processed_at").limit(1).execute()),
        ("content_tickers.created_at", lambda: supabase.table("content_tickers").select("created_at").limit(1).execute()),
        ("tickers table", lambda: supabase.table("tickers").select("ticker").limit(1).execute()),
        ("ticker_daily_stats table", lambda: supabase.table("ticker_daily_stats").select("ticker").limit(1).execute()),
    ]
    
    passed = 0
    for test_name, test_func in tests:
        try:
            test_func()
            print(f"✅ {test_name}: OK")
            passed += 1
        except Exception as e:
            if "does not exist" in str(e).lower() or "column" in str(e).lower():
                print(f"❌ {test_name}: Missing")
            else:
                print(f"⚠️ {test_name}: {e}")
    
    if passed == len(tests):
        print(f"\n🎉 Schema migration successful! All {passed}/{len(tests)} tests passed.")
        return True
    else:
        print(f"\n⚠️ Schema migration incomplete: {passed}/{len(tests)} tests passed.")
        print("Please run the SQL commands in Supabase dashboard first.")
        return False

if __name__ == "__main__":
    migrate_enhanced_schema()
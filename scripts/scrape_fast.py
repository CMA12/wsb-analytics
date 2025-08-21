#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import praw
from dotenv import load_dotenv
from db import map_submission, map_comments, supabase
import time

load_dotenv()

def fast_scrape_subreddit(sub_name="wallstreetbets", limit=3):
    """Fast scraping without LLM analysis - just collect raw data"""
    
    print(f"🚀 Starting FAST SCRAPE mode for r/{sub_name}")
    print(f"📊 Target: {limit} posts + all comments")
    print("⚡ Skipping LLM analysis for maximum speed\n")
    
    start_time = time.time()
    
    # Initialize Reddit client
    reddit = praw.Reddit(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        user_agent=os.getenv('USER_AGENT')
    )
    
    subreddit = reddit.subreddit(sub_name)
    
    processed_posts = 0
    total_comments = 0
    
    for submission in subreddit.top(time_filter='day', limit=limit):
        try:
            print(f"📝 Processing Post {processed_posts + 1}:")
            print(f"   Title: {submission.title[:80]}...")
            print(f"   Score: {submission.score} | Comments: {submission.num_comments}")
            print(f"   ID: {submission.id}")
            
            # FAST: Map submission without LLM analysis
            map_submission(submission, skip_analysis=True)
            
            # FAST: Map comments without LLM analysis
            comment_start = time.time()
            try:
                comment_count = map_comments(submission, skip_analysis=True)
                comment_time = time.time() - comment_start
                print(f"   💬 Stored {comment_count} comments in {comment_time:.1f}s")
                total_comments += comment_count
            except Exception as e:
                print(f"   ⚠️ Comment processing failed: {e}")
            
            processed_posts += 1
            print(f"   ✅ Post {processed_posts} completed\n")
            
        except Exception as e:
            print(f"   ❌ Error processing submission {submission.id}: {e}")
            continue
    
    total_time = time.time() - start_time
    
    print("="*60)
    print("🎯 FAST SCRAPE RESULTS")
    print("="*60)
    print(f"✅ Posts processed: {processed_posts}")
    print(f"✅ Comments stored: {total_comments}")
    print(f"⚡ Total time: {total_time:.1f}s")
    print(f"📈 Speed: {total_comments / total_time:.1f} comments/second")
    print(f"💰 LLM calls avoided: {processed_posts + total_comments}")
    print("\n🔄 Ready for batch analysis with batch_analyze.py")

if __name__ == "__main__":
    fast_scrape_subreddit()
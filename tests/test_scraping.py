#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

import praw
from dotenv import load_dotenv
from db import map_submission, supabase

load_dotenv()

def test_simple_scraping():
    """Test basic scraping functionality with 3 posts"""
    
    print("🚀 Testing simple scraping (posts only)...")
    
    # Initialize Reddit client
    reddit = praw.Reddit(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        user_agent=os.getenv('USER_AGENT')
    )
    
    # Get wallstreetbets subreddit
    subreddit = reddit.subreddit("wallstreetbets")
    
    # Process exactly 3 posts
    processed_posts = 0
    for submission in subreddit.hot(limit=10):
        if processed_posts >= 3:
            break
            
        try:
            print(f"\n📊 Processing Post {processed_posts + 1}:")
            print(f"   Title: {submission.title[:80]}...")
            print(f"   Score: {submission.score}")
            print(f"   ID: {submission.id}")
            
            # Map the submission (post only)
            map_submission(submission)
            
            processed_posts += 1
            print(f"   ✅ Post {processed_posts} completed")
            
        except Exception as e:
            print(f"   ❌ Error processing submission {submission.id}: {e}")
            continue
    
    print(f"\n🎯 Processed {processed_posts} posts total")
    
    # Display results
    display_scraping_results()

def test_targeted_scraping():
    """Test scraping with posts more likely to contain tickers"""
    
    print("\n🎯 Testing targeted scraping...")
    
    # Initialize Reddit client
    reddit = praw.Reddit(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        user_agent=os.getenv('USER_AGENT')
    )
    
    subreddit = reddit.subreddit("wallstreetbets")
    
    processed_posts = 0
    
    for submission in subreddit.hot(limit=10):
        if processed_posts >= 2:
            break
            
        # Check if the post likely contains financial content
        title_text = (submission.title + " " + getattr(submission, 'selftext', '')).upper()
        likely_financial = any(indicator in title_text for indicator in [
            '$', 'YOLO', 'CALL', 'PUT', 'TSLA', 'AAPL', 'NVDA', 'SPY', 'META', 'STOCK'
        ])
        
        if likely_financial:
            print(f"\n📊 Processing targeted post {processed_posts + 1}:")
            print(f"   Title: {submission.title[:80]}...")
            print(f"   Score: {submission.score}")
            
            try:
                map_submission(submission)
                processed_posts += 1
                print(f"   ✅ Targeted post {processed_posts} completed")
            except Exception as e:
                print(f"   ❌ Error: {e}")
    
    print(f"\n🎯 Processed {processed_posts} targeted posts")

def display_scraping_results():
    """Display the scraping test results"""
    
    print("\n" + "="*60)
    print("📈 SCRAPING TEST RESULTS")
    print("="*60)
    
    try:
        # Get all posts with their tickers
        posts_result = supabase.table("posts").select("reddit_id, title, score").execute()
        posts = posts_result.data or []
        
        print(f"Found {len(posts)} posts in database")
        
        for i, post in enumerate(posts, 1):
            print(f"\n📝 POST {i}: {post['title'][:60]}...")
            print(f"   Score: {post['score']} | ID: {post['reddit_id']}")
            
            # Get tickers for this post
            tickers_result = supabase.table("content_tickers").select("*").eq("content_reddit_id", post['reddit_id']).eq("kind", "post").execute()
            
            post_tickers = tickers_result.data or []
            
            if post_tickers:
                print("   🎯 EXTRACTED TICKERS:")
                for ticker in post_tickers:
                    conf = ticker.get('confidence', 0)
                    method = ticker.get('method', 'unknown')
                    print(f"      💎 {ticker['ticker']} | Conf: {conf:.3f} | Method: {method}")
            else:
                print("   ⚪ No tickers extracted from this post")
        
        # Summary
        all_tickers_result = supabase.table("content_tickers").select("*").execute()
        all_tickers = all_tickers_result.data or []
        
        if all_tickers:
            unique_tickers = list(set(t['ticker'] for t in all_tickers))
            avg_conf = sum(t.get('confidence', 0) for t in all_tickers) / len(all_tickers)
            print(f"\n📊 SUMMARY:")
            print(f"   Total extractions: {len(all_tickers)}")
            print(f"   Unique tickers: {len(unique_tickers)}")
            print(f"   Average confidence: {avg_conf:.3f}")
            print(f"   Tickers found: {', '.join(unique_tickers)}")
        
    except Exception as e:
        print(f"❌ Error displaying results: {e}")

if __name__ == "__main__":
    print("🧪 Starting scraping tests...")
    test_simple_scraping()
    test_targeted_scraping()
    print("\n✅ All scraping tests completed!")
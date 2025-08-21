#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from db import supabase, map_tickers
import time

def test_batch_analyze():
    """Test batch analysis with just posts and a few comments"""
    
    print("🧪 Testing BATCH ANALYSIS (posts + 10 comments)")
    print("="*50)
    
    start_time = time.time()
    
    # 1. Analyze all posts first (should be quick)
    print("\n📝 ANALYZING POSTS...")
    posts_result = supabase.table("posts").select("reddit_id, title, text").execute()
    posts = posts_result.data or []
    
    post_tickers = 0
    
    for i, post in enumerate(posts, 1):
        print(f"📊 Post {i}/{len(posts)}: {post['title'][:50]}...")
        
        # Check if already analyzed
        existing = supabase.table("content_tickers").select("ticker").eq("content_reddit_id", post['reddit_id']).eq("kind", "post").execute()
        if existing.data:
            print(f"   ⏭️ Already has {len(existing.data)} tickers")
            continue
        
        post_text = f"{post.get('title', '')}\n{post.get('text', '')}"
        
        try:
            tickers = map_tickers(supabase, kind="post", content_reddit_id=post["reddit_id"], text=post_text)
            if tickers:
                symbols = [t['ticker'] for t in tickers]
                print(f"   🎯 Found: {', '.join(symbols)}")
                post_tickers += len(tickers)
            else:
                print(f"   ⚪ No tickers")
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # 2. Analyze just 10 comments as test
    print(f"\n💬 ANALYZING 10 COMMENTS (sample)...")
    comments_result = supabase.table("comments").select("reddit_id, body").limit(10).execute()
    comments = comments_result.data or []
    
    comment_tickers = 0
    
    for i, comment in enumerate(comments, 1):
        body = comment.get('body', '').strip()
        if not body or body in ['[deleted]', '[removed]']:
            print(f"   Comment {i}: Empty/deleted")
            continue
        
        print(f"   Comment {i}: {body[:50]}...")
        
        # Check if already analyzed
        existing = supabase.table("content_tickers").select("ticker").eq("content_reddit_id", comment['reddit_id']).eq("kind", "comment").execute()
        if existing.data:
            print(f"     ⏭️ Already analyzed")
            continue
        
        try:
            tickers = map_tickers(supabase, kind="comment", content_reddit_id=comment["reddit_id"], text=body)
            if tickers:
                symbols = [t['ticker'] for t in tickers]
                print(f"     🎯 Found: {', '.join(symbols)}")
                comment_tickers += len(tickers)
            else:
                print(f"     ⚪ No tickers")
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*50)
    print("🎯 BATCH ANALYSIS TEST RESULTS")  
    print("="*50)
    print(f"📝 Posts analyzed: {len(posts)}")
    print(f"💬 Comments analyzed: {len(comments)}")
    print(f"🎯 Post tickers found: {post_tickers}")
    print(f"🎯 Comment tickers found: {comment_tickers}")
    print(f"⏱️ Total time: {total_time:.1f}s")
    
    # Show what's in database now
    show_database_summary()

def show_database_summary():
    """Show summary of what's stored in database"""
    
    print("\n📊 DATABASE SUMMARY")
    print("-" * 30)
    
    # Count posts and comments
    posts = supabase.table("posts").select("reddit_id").execute()
    comments = supabase.table("comments").select("reddit_id").execute()
    tickers = supabase.table("content_tickers").select("*").execute()
    
    print(f"📝 Posts stored: {len(posts.data or [])}")
    print(f"💬 Comments stored: {len(comments.data or [])}")
    print(f"🎯 Tickers extracted: {len(tickers.data or [])}")
    
    if tickers.data:
        # Group by ticker symbol
        ticker_counts = {}
        for t in tickers.data:
            symbol = t['ticker']
            kind = t['kind']
            if symbol not in ticker_counts:
                ticker_counts[symbol] = {'post': 0, 'comment': 0}
            ticker_counts[symbol][kind] += 1
        
        print("\n🏆 Top Tickers Found:")
        for symbol, counts in sorted(ticker_counts.items(), key=lambda x: x[1]['post'] + x[1]['comment'], reverse=True)[:5]:
            total = counts['post'] + counts['comment']
            print(f"   💎 {symbol}: {total} mentions (posts: {counts['post']}, comments: {counts['comment']})")

if __name__ == "__main__":
    test_batch_analyze()
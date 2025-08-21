#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from db import supabase, map_tickers
import time

def analyze_stored_posts():
    """Analyze all stored posts that haven't been processed yet"""
    
    print("🔍 Finding unanalyzed posts...")
    
    # Get all posts
    posts_result = supabase.table("posts").select("reddit_id, title, text").execute()
    posts = posts_result.data or []
    
    print(f"📝 Found {len(posts)} posts to analyze")
    
    analyzed_count = 0
    ticker_count = 0
    
    for i, post in enumerate(posts, 1):
        print(f"\n📊 Analyzing Post {i}/{len(posts)}: {post['title'][:60]}...")
        
        # Check if already analyzed
        existing_tickers = supabase.table("content_tickers").select("ticker").eq("content_reddit_id", post['reddit_id']).eq("kind", "post").execute()
        if existing_tickers.data:
            print(f"   ⏭️ Already analyzed ({len(existing_tickers.data)} tickers)")
            continue
        
        # Combine title and text for analysis
        post_text = f"{post.get('title', '')}\n{post.get('text', '')}"
        
        if post_text.strip():
            try:
                # Analyze with LLM
                tickers = map_tickers(supabase, kind="post", content_reddit_id=post["reddit_id"], text=post_text)
                
                if tickers:
                    ticker_symbols = [t['ticker'] for t in tickers]
                    print(f"   🎯 Found tickers: {', '.join(ticker_symbols)}")
                    ticker_count += len(tickers)
                else:
                    print(f"   ⚪ No tickers found")
                
                analyzed_count += 1
                
            except Exception as e:
                print(f"   ❌ Analysis failed: {e}")
        else:
            print(f"   ⚪ Empty post content")
    
    return analyzed_count, ticker_count

def analyze_stored_comments(limit=None):
    """Analyze stored comments that haven't been processed yet"""
    
    print("🔍 Finding unanalyzed comments...")
    
    # Get comments, optionally with limit
    query = supabase.table("comments").select("reddit_id, body, post_reddit_id, parent_reddit_id")
    if limit:
        query = query.limit(limit)
    
    comments_result = query.execute()
    comments = comments_result.data or []
    
    print(f"💬 Found {len(comments)} comments to analyze{f' (limited to {limit})' if limit else ''}")
    
    analyzed_count = 0
    ticker_count = 0
    
    for i, comment in enumerate(comments, 1):
        if i % 10 == 0:
            print(f"📊 Progress: {i}/{len(comments)} comments analyzed")
        
        # Check if already analyzed
        existing_tickers = supabase.table("content_tickers").select("ticker").eq("content_reddit_id", comment['reddit_id']).eq("kind", "comment").execute()
        if existing_tickers.data:
            continue
        
        body = comment.get('body', '').strip()
        
        if body and body not in ['[deleted]', '[removed]']:
            try:
                # Analyze with LLM
                tickers = map_tickers(supabase, kind="comment", content_reddit_id=comment["reddit_id"], text=body)
                
                if tickers:
                    ticker_count += len(tickers)
                
                analyzed_count += 1
                
            except Exception as e:
                print(f"   ❌ Comment {comment['reddit_id']} analysis failed: {e}")
    
    return analyzed_count, ticker_count

def batch_analyze(analyze_posts=True, analyze_comments=True, comment_limit=50):
    """Main batch analysis function"""
    
    print("🚀 Starting BATCH ANALYSIS")
    print("="*50)
    
    start_time = time.time()
    total_analyzed = 0
    total_tickers = 0
    
    if analyze_posts:
        print("\n📝 ANALYZING POSTS...")
        post_analyzed, post_tickers = analyze_stored_posts()
        total_analyzed += post_analyzed
        total_tickers += post_tickers
        print(f"✅ Posts complete: {post_analyzed} analyzed, {post_tickers} tickers found")
    
    if analyze_comments:
        print(f"\n💬 ANALYZING COMMENTS (limit: {comment_limit})...")
        comment_analyzed, comment_tickers = analyze_stored_comments(limit=comment_limit)
        total_analyzed += comment_analyzed  
        total_tickers += comment_tickers
        print(f"✅ Comments complete: {comment_analyzed} analyzed, {comment_tickers} tickers found")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*50)
    print("🎯 BATCH ANALYSIS RESULTS")
    print("="*50)
    print(f"✅ Total items analyzed: {total_analyzed}")
    print(f"🎯 Total tickers extracted: {total_tickers}")
    print(f"⏱️ Total time: {total_time:.1f}s")
    if total_analyzed > 0:
        print(f"📈 Speed: {total_analyzed / total_time:.1f} items/second")
    
    # Show extraction summary
    display_extraction_summary()

def display_extraction_summary():
    """Display summary of all extracted tickers"""
    
    print("\n🔍 EXTRACTION SUMMARY")
    print("-" * 30)
    
    # Get all tickers
    all_tickers = supabase.table("content_tickers").select("ticker, confidence, method, kind").execute()
    tickers = all_tickers.data or []
    
    if not tickers:
        print("No tickers found in database")
        return
    
    # Group by ticker
    ticker_counts = {}
    for t in tickers:
        symbol = t['ticker']
        if symbol not in ticker_counts:
            ticker_counts[symbol] = {'post': 0, 'comment': 0, 'total_confidence': 0}
        ticker_counts[symbol][t['kind']] += 1
        ticker_counts[symbol]['total_confidence'] += t.get('confidence', 0)
    
    # Sort by total mentions
    sorted_tickers = sorted(ticker_counts.items(), key=lambda x: x[1]['post'] + x[1]['comment'], reverse=True)
    
    print(f"📊 Found {len(sorted_tickers)} unique tickers:")
    for symbol, data in sorted_tickers[:10]:  # Top 10
        total = data['post'] + data['comment']
        avg_conf = data['total_confidence'] / total
        print(f"   💎 {symbol}: {total} mentions (posts: {data['post']}, comments: {data['comment']}) | Avg conf: {avg_conf:.3f}")

if __name__ == "__main__":
    # For testing, analyze posts and limited comments
    batch_analyze(analyze_posts=True, analyze_comments=True, comment_limit=50)
#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timedelta

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from db import supabase, map_tickers_with_context
import time

def analyze_unprocessed_posts():
    """Analyze all unprocessed posts using processed_at tracking"""
    
    print("🔍 Finding unprocessed posts...")
    
    # Get all posts that haven't been processed
    posts_result = (
        supabase.table("posts")
        .select("reddit_id, title, text, created_utc")
        .is_("processed_at", "null")
        .order("created_utc", desc=False)  # Process oldest first
        .execute()
    )
    
    posts = posts_result.data or []
    print(f"📝 Found {len(posts)} unprocessed posts")
    
    analyzed_count = 0
    ticker_count = 0
    
    for i, post in enumerate(posts, 1):
        print(f"\n📊 Processing Post {i}/{len(posts)}: {post['title'][:60]}...")
        
        # Combine title and text for analysis
        post_text = f"{post.get('title', '')}\n{post.get('text', '')}"
        
        if post_text.strip():
            try:
                # Analyze with enhanced context system
                tickers = map_tickers_with_context(
                    supabase, 
                    kind="post", 
                    content_reddit_id=post["reddit_id"], 
                    text=post_text
                )
                
                if tickers:
                    ticker_symbols = [t.get('ticker', 'UNKNOWN') for t in tickers]
                    print(f"   🎯 Found tickers: {', '.join(ticker_symbols)}")
                    ticker_count += len(tickers)
                else:
                    print(f"   ⚪ No tickers found")
                
                # Mark as processed
                supabase.table("posts").update({"processed_at": "NOW()"}).eq("reddit_id", post["reddit_id"]).execute()
                analyzed_count += 1
                
            except Exception as e:
                print(f"   ❌ Analysis failed: {e}")
                # Still mark as processed to avoid infinite retries
                supabase.table("posts").update({"processed_at": "NOW()"}).eq("reddit_id", post["reddit_id"]).execute()
        else:
            print(f"   ⚪ Empty post content")
            # Mark empty posts as processed
            supabase.table("posts").update({"processed_at": "NOW()"}).eq("reddit_id", post["reddit_id"]).execute()
    
    return analyzed_count, ticker_count


def analyze_unprocessed_comments(limit=None):
    """Analyze unprocessed comments with contextual inheritance"""
    
    print("🔍 Finding unprocessed comments...")
    
    # Get unprocessed comments with their post context
    query = (
        supabase.table("comments")
        .select("reddit_id, body, post_reddit_id, parent_reddit_id, created_utc")
        .is_("processed_at", "null")
        .order("created_utc", desc=False)  # Process oldest first
    )
    
    if limit:
        query = query.limit(limit)
    
    comments_result = query.execute()
    comments = comments_result.data or []
    
    print(f"💬 Found {len(comments)} unprocessed comments{f' (limited to {limit})' if limit else ''}")
    
    analyzed_count = 0
    ticker_count = 0
    inherited_count = 0
    
    for i, comment in enumerate(comments, 1):
        if i % 50 == 0:
            print(f"📊 Progress: {i}/{len(comments)} comments processed")
        
        body = comment.get('body', '').strip()
        
        if body and body not in ['[deleted]', '[removed]']:
            try:
                # Use enhanced context-aware analysis
                tickers = map_tickers_with_context(
                    supabase, 
                    kind="comment", 
                    content_reddit_id=comment["reddit_id"], 
                    text=body,
                    post_reddit_id=comment["post_reddit_id"]
                )
                
                if tickers:
                    ticker_count += len(tickers)
                    # Count how many were inherited vs direct
                    direct = sum(1 for t in tickers if t.get('method') != 'contextual_inheritance')
                    inherited = len(tickers) - direct
                    inherited_count += inherited
                    
                    if i % 50 == 0 and tickers:  # Sample logging
                        methods = [t.get('method', 'unknown') for t in tickers]
                        print(f"   🎯 Found: {methods}")
                
                # Mark as processed
                supabase.table("comments").update({"processed_at": "NOW()"}).eq("reddit_id", comment["reddit_id"]).execute()
                analyzed_count += 1
                
            except Exception as e:
                print(f"   ❌ Comment {comment['reddit_id']} analysis failed: {e}")
                # Mark as processed to avoid infinite retries
                supabase.table("comments").update({"processed_at": "NOW()"}).eq("reddit_id", comment["reddit_id"]).execute()
        else:
            # Mark deleted/empty comments as processed
            supabase.table("comments").update({"processed_at": "NOW()"}).eq("reddit_id", comment["reddit_id"]).execute()
    
    return analyzed_count, ticker_count, inherited_count


def incremental_batch_analyze(analyze_posts=True, analyze_comments=True, comment_limit=100):
    """Main incremental batch analysis function with enhanced metrics"""
    
    print("🚀 Starting INCREMENTAL BATCH ANALYSIS")
    print("="*60)
    
    start_time = time.time()
    total_analyzed = 0
    total_tickers = 0
    total_inherited = 0
    
    if analyze_posts:
        print("\n📝 ANALYZING UNPROCESSED POSTS...")
        post_analyzed, post_tickers = analyze_unprocessed_posts()
        total_analyzed += post_analyzed
        total_tickers += post_tickers
        print(f"✅ Posts complete: {post_analyzed} analyzed, {post_tickers} tickers found")
    
    if analyze_comments:
        print(f"\n💬 ANALYZING UNPROCESSED COMMENTS (limit: {comment_limit})...")
        comment_analyzed, comment_tickers, inherited_tickers = analyze_unprocessed_comments(limit=comment_limit)
        total_analyzed += comment_analyzed  
        total_tickers += comment_tickers
        total_inherited += inherited_tickers
        print(f"✅ Comments complete: {comment_analyzed} analyzed, {comment_tickers} tickers found")
        print(f"🔗 Contextual inheritance: {inherited_tickers} tickers inherited from post context")
    
    total_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("🎯 INCREMENTAL ANALYSIS RESULTS")
    print("="*60)
    print(f"✅ Total items analyzed: {total_analyzed}")
    print(f"🎯 Total tickers extracted: {total_tickers}")
    print(f"🔗 Contextually inherited: {total_inherited}")
    print(f"📊 Direct extraction: {total_tickers - total_inherited}")
    print(f"⏱️ Total time: {total_time:.1f}s")
    if total_analyzed > 0:
        print(f"📈 Speed: {total_analyzed / total_time:.1f} items/second")
    
    # Show enhanced extraction summary
    display_enhanced_summary()


def display_enhanced_summary():
    """Display enhanced summary with hype metrics and aggregation data"""
    
    print("\n🔍 ENHANCED EXTRACTION SUMMARY")
    print("-" * 40)
    
    # Get aggregated ticker data
    try:
        ticker_summary = (
            supabase.table("tickers")
            .select("ticker, company_name, total_mentions, total_posts, total_comments, avg_hype_score, max_hype_score")
            .order("total_mentions", desc=True)
            .limit(15)
            .execute()
        )
        
        tickers = ticker_summary.data or []
        
        if not tickers:
            print("No aggregated ticker data found - schema may need migration")
            return
        
        print(f"📊 Top {len(tickers)} tickers by total mentions:")
        print(f"{'Ticker':<8} {'Company':<20} {'Total':<7} {'Posts':<6} {'Comments':<8} {'Avg Hype':<9} {'Max Hype'}")
        print("-" * 75)
        
        for ticker in tickers:
            company = (ticker.get('company_name') or '')[:19]
            print(f"{ticker['ticker']:<8} {company:<20} {ticker['total_mentions']:<7} "
                  f"{ticker['total_posts']:<6} {ticker['total_comments']:<8} "
                  f"{ticker.get('avg_hype_score', 0):<9.2f} {ticker.get('max_hype_score', 0):.2f}")
        
        # Show method breakdown
        method_summary = (
            supabase.table("content_tickers")
            .select("method")
            .execute()
        )
        
        if method_summary.data:
            methods = {}
            for item in method_summary.data:
                method = item.get('method', 'unknown')
                methods[method] = methods.get(method, 0) + 1
            
            print(f"\n📈 Extraction methods breakdown:")
            for method, count in sorted(methods.items(), key=lambda x: x[1], reverse=True):
                print(f"   {method}: {count}")
        
    except Exception as e:
        print(f"❌ Error displaying enhanced summary: {e}")
        print("This may indicate the enhanced schema hasn't been applied yet.")


def backfill_single_day(target_date: str):
    """
    Backfill analysis for a single day of historical data.
    
    Args:
        target_date (str): Date in format 'YYYY-MM-DD'
    """
    print(f"🕐 BACKFILL ANALYSIS FOR {target_date}")
    print("="*50)
    
    try:
        start_date = datetime.fromisoformat(target_date)
        end_date = start_date + timedelta(days=1)
        
        start_iso = start_date.isoformat() + "Z"
        end_iso = end_date.isoformat() + "Z"
        
        # Get posts from this date
        posts = (
            supabase.table("posts")
            .select("reddit_id, title, text, created_utc")
            .gte("created_utc", start_iso)
            .lt("created_utc", end_iso)
            .is_("processed_at", "null")
            .execute()
        )
        
        # Get comments from this date
        comments = (
            supabase.table("comments")
            .select("reddit_id, body, post_reddit_id, created_utc")
            .gte("created_utc", start_iso)
            .lt("created_utc", end_iso)
            .is_("processed_at", "null")
            .execute()
        )
        
        print(f"📅 Found {len(posts.data or [])} posts and {len(comments.data or [])} comments for {target_date}")
        
        if not posts.data and not comments.data:
            print("✅ No unprocessed data found for this date")
            return
        
        # Run incremental analysis (which will only process unprocessed items)
        incremental_batch_analyze(analyze_posts=True, analyze_comments=True, comment_limit=None)
        
    except Exception as e:
        print(f"❌ Backfill failed: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Incremental batch analysis with contextual inheritance")
    parser.add_argument("--posts", action="store_true", default=True, help="Analyze posts")
    parser.add_argument("--comments", action="store_true", default=True, help="Analyze comments")
    parser.add_argument("--comment-limit", type=int, default=100, help="Limit comments to process")
    parser.add_argument("--backfill-date", type=str, help="Backfill specific date (YYYY-MM-DD)")
    
    args = parser.parse_args()
    
    if args.backfill_date:
        backfill_single_day(args.backfill_date)
    else:
        incremental_batch_analyze(
            analyze_posts=args.posts,
            analyze_comments=args.comments, 
            comment_limit=args.comment_limit
        )
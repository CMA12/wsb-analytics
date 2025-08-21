#!/usr/bin/env python3

import sys
import os
from datetime import datetime, timedelta
import time

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from db import supabase, map_tickers_with_context

def backfill_date_range(start_date: str, end_date: str, batch_size: int = 500):
    """
    Backfill historical data for a date range with chunked processing.
    
    Args:
        start_date (str): Start date in format 'YYYY-MM-DD'
        end_date (str): End date in format 'YYYY-MM-DD'
        batch_size (int): Number of items to process per batch
    """
    
    print(f"🕐 HISTORICAL BACKFILL: {start_date} to {end_date}")
    print("="*60)
    
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        if start_dt >= end_dt:
            print("❌ Start date must be before end date")
            return
        
        total_days = (end_dt - start_dt).days
        print(f"📅 Processing {total_days} days of historical data")
        
        current_date = start_dt
        day_count = 0
        total_processed = 0
        total_tickers = 0
        
        while current_date < end_dt:
            day_count += 1
            next_date = current_date + timedelta(days=1)
            
            print(f"\n📆 Day {day_count}/{total_days}: {current_date.strftime('%Y-%m-%d')}")
            
            # Process this day's data
            day_processed, day_tickers = process_single_day(
                current_date.strftime('%Y-%m-%d'), 
                batch_size
            )
            
            total_processed += day_processed
            total_tickers += day_tickers
            
            print(f"   ✅ Day complete: {day_processed} items, {day_tickers} tickers")
            
            # Brief pause to avoid overwhelming the API
            if day_processed > 0:
                time.sleep(1)
            
            current_date = next_date
        
        print(f"\n🎉 BACKFILL COMPLETE")
        print(f"📊 Total processed: {total_processed} items")
        print(f"🎯 Total tickers: {total_tickers}")
        
    except Exception as e:
        print(f"❌ Backfill failed: {e}")


def process_single_day(date_str: str, batch_size: int = 500):
    """
    Process all unprocessed content for a single day.
    
    Args:
        date_str (str): Date in format 'YYYY-MM-DD'
        batch_size (int): Number of items per batch
        
    Returns:
        tuple: (total_processed, total_tickers)
    """
    
    start_time = datetime.fromisoformat(date_str)
    end_time = start_time + timedelta(days=1)
    
    start_iso = start_time.isoformat() + "Z"
    end_iso = end_time.isoformat() + "Z"
    
    # Get unprocessed posts for this date
    posts = (
        supabase.table("posts")
        .select("reddit_id, title, text, created_utc")
        .gte("created_utc", start_iso)
        .lt("created_utc", end_iso)
        .is_("processed_at", "null")
        .order("created_utc")
        .execute()
    )
    
    # Get unprocessed comments for this date  
    comments = (
        supabase.table("comments")
        .select("reddit_id, body, post_reddit_id, parent_reddit_id, created_utc")
        .gte("created_utc", start_iso)
        .lt("created_utc", end_iso)
        .is_("processed_at", "null")
        .order("created_utc")
        .execute()
    )
    
    posts_data = posts.data or []
    comments_data = comments.data or []
    
    if not posts_data and not comments_data:
        return 0, 0
    
    print(f"   📝 {len(posts_data)} posts, 💬 {len(comments_data)} comments")
    
    total_processed = 0
    total_tickers = 0
    
    # Process posts in batches
    if posts_data:
        post_processed, post_tickers = process_posts_batch(posts_data, batch_size)
        total_processed += post_processed
        total_tickers += post_tickers
    
    # Process comments in batches
    if comments_data:
        comment_processed, comment_tickers = process_comments_batch(comments_data, batch_size)
        total_processed += comment_processed
        total_tickers += comment_tickers
    
    return total_processed, total_tickers


def process_posts_batch(posts: list, batch_size: int):
    """Process posts in batches"""
    
    total_processed = 0
    total_tickers = 0
    
    for i in range(0, len(posts), batch_size):
        batch = posts[i:i + batch_size]
        print(f"      📝 Processing posts batch {i//batch_size + 1} ({len(batch)} posts)")
        
        batch_processed = 0
        batch_tickers = 0
        
        for post in batch:
            try:
                # Combine title and text
                post_text = f"{post.get('title', '')}\n{post.get('text', '')}"
                
                if post_text.strip():
                    # Analyze with enhanced system
                    tickers = map_tickers_with_context(
                        supabase,
                        kind="post",
                        content_reddit_id=post["reddit_id"],
                        text=post_text
                    )
                    
                    if tickers:
                        batch_tickers += len(tickers)
                
                # Mark as processed
                supabase.table("posts").update({"processed_at": "NOW()"}).eq("reddit_id", post["reddit_id"]).execute()
                batch_processed += 1
                
            except Exception as e:
                print(f"         ❌ Post {post['reddit_id']} failed: {e}")
                # Still mark as processed to avoid infinite retries
                supabase.table("posts").update({"processed_at": "NOW()"}).eq("reddit_id", post["reddit_id"]).execute()
        
        total_processed += batch_processed
        total_tickers += batch_tickers
        print(f"         ✅ Batch complete: {batch_processed}/{len(batch)} processed, {batch_tickers} tickers")
    
    return total_processed, total_tickers


def process_comments_batch(comments: list, batch_size: int):
    """Process comments in batches with contextual inheritance"""
    
    total_processed = 0
    total_tickers = 0
    total_inherited = 0
    
    for i in range(0, len(comments), batch_size):
        batch = comments[i:i + batch_size]
        print(f"      💬 Processing comments batch {i//batch_size + 1} ({len(batch)} comments)")
        
        batch_processed = 0
        batch_tickers = 0
        batch_inherited = 0
        
        for comment in batch:
            try:
                body = comment.get('body', '').strip()
                
                if body and body not in ['[deleted]', '[removed]']:
                    # Analyze with contextual inheritance
                    tickers = map_tickers_with_context(
                        supabase,
                        kind="comment",
                        content_reddit_id=comment["reddit_id"],
                        text=body,
                        post_reddit_id=comment["post_reddit_id"]
                    )
                    
                    if tickers:
                        batch_tickers += len(tickers)
                        # Count inherited tickers
                        inherited = sum(1 for t in tickers if t.get('method') == 'contextual_inheritance')
                        batch_inherited += inherited
                
                # Mark as processed
                supabase.table("comments").update({"processed_at": "NOW()"}).eq("reddit_id", comment["reddit_id"]).execute()
                batch_processed += 1
                
            except Exception as e:
                print(f"         ❌ Comment {comment['reddit_id']} failed: {e}")
                # Still mark as processed
                supabase.table("comments").update({"processed_at": "NOW()"}).eq("reddit_id", comment["reddit_id"]).execute()
        
        total_processed += batch_processed
        total_tickers += batch_tickers
        total_inherited += batch_inherited
        
        if batch_inherited > 0:
            print(f"         ✅ Batch complete: {batch_processed}/{len(batch)} processed, {batch_tickers} tickers ({batch_inherited} inherited)")
        else:
            print(f"         ✅ Batch complete: {batch_processed}/{len(batch)} processed, {batch_tickers} tickers")
    
    return total_processed, total_tickers


def estimate_backfill_scope(start_date: str, end_date: str):
    """
    Estimate the scope of backfill work without processing.
    
    Args:
        start_date (str): Start date in format 'YYYY-MM-DD'
        end_date (str): End date in format 'YYYY-MM-DD'
    """
    
    print(f"🔍 ESTIMATING BACKFILL SCOPE: {start_date} to {end_date}")
    print("="*50)
    
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)
        
        start_iso = start_dt.isoformat() + "Z"
        end_iso = end_dt.isoformat() + "Z"
        
        # Count unprocessed posts
        posts_count = (
            supabase.table("posts")
            .select("reddit_id", count="exact")
            .gte("created_utc", start_iso)
            .lt("created_utc", end_iso)
            .is_("processed_at", "null")
            .execute()
        )
        
        # Count unprocessed comments
        comments_count = (
            supabase.table("comments")
            .select("reddit_id", count="exact")
            .gte("created_utc", start_iso)
            .lt("created_utc", end_iso)
            .is_("processed_at", "null")
            .execute()
        )
        
        total_posts = posts_count.count or 0
        total_comments = comments_count.count or 0
        total_items = total_posts + total_comments
        
        print(f"📊 Unprocessed content:")
        print(f"   📝 Posts: {total_posts:,}")
        print(f"   💬 Comments: {total_comments:,}")
        print(f"   🔢 Total items: {total_items:,}")
        
        if total_items > 0:
            # Estimate processing time (assume 2 items/second including API calls)
            estimated_seconds = total_items / 2
            estimated_hours = estimated_seconds / 3600
            
            print(f"\n⏱️ Estimated processing time:")
            print(f"   🕐 {estimated_hours:.1f} hours")
            print(f"   💰 Estimated API calls: ~{total_items:,}")
            
            # Estimate cost (rough calculation for GPT API)
            estimated_cost = total_items * 0.001  # Very rough estimate
            print(f"   💸 Estimated cost: ~${estimated_cost:.2f}")
            
        else:
            print("✅ No unprocessed content found in date range")
            
        print(f"\n📅 Date range: {(end_dt - start_dt).days} days")
        
    except Exception as e:
        print(f"❌ Estimation failed: {e}")


def resume_backfill():
    """
    Resume backfill from where it left off by finding the latest processed date.
    """
    
    print("🔄 RESUMING BACKFILL FROM LAST PROCESSED DATE")
    print("="*50)
    
    try:
        # Find the latest processed post or comment
        latest_post = (
            supabase.table("posts")
            .select("created_utc")
            .not_.is_("processed_at", "null")
            .order("created_utc", desc=True)
            .limit(1)
            .execute()
        )
        
        latest_comment = (
            supabase.table("comments")
            .select("created_utc")
            .not_.is_("processed_at", "null")
            .order("created_utc", desc=True)
            .limit(1)
            .execute()
        )
        
        latest_dates = []
        if latest_post.data:
            latest_dates.append(latest_post.data[0]['created_utc'])
        if latest_comment.data:
            latest_dates.append(latest_comment.data[0]['created_utc'])
        
        if not latest_dates:
            print("❌ No processed content found - cannot resume")
            return
        
        # Get the latest date
        latest_processed = max(latest_dates)
        latest_dt = datetime.fromisoformat(latest_processed.replace('Z', ''))
        
        # Start from the day after latest processed
        resume_date = (latest_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        today = datetime.now().strftime('%Y-%m-%d')
        
        print(f"📅 Latest processed content: {latest_dt.strftime('%Y-%m-%d')}")
        print(f"🚀 Resuming from: {resume_date}")
        print(f"📍 Processing until: {today}")
        
        if resume_date >= today:
            print("✅ Already up to date!")
            return
        
        # Resume backfill
        backfill_date_range(resume_date, today)
        
    except Exception as e:
        print(f"❌ Resume failed: {e}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Historical data backfill with contextual inheritance")
    parser.add_argument("--start-date", type=str, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end-date", type=str, help="End date (YYYY-MM-DD)")
    parser.add_argument("--batch-size", type=int, default=500, help="Batch size for processing")
    parser.add_argument("--estimate", action="store_true", help="Estimate scope without processing")
    parser.add_argument("--resume", action="store_true", help="Resume from last processed date")
    
    args = parser.parse_args()
    
    if args.resume:
        resume_backfill()
    elif args.estimate and args.start_date and args.end_date:
        estimate_backfill_scope(args.start_date, args.end_date)
    elif args.start_date and args.end_date:
        backfill_date_range(args.start_date, args.end_date, args.batch_size)
    else:
        print("Usage examples:")
        print("  # Estimate scope")
        print("  python backfill_historical.py --start-date 2024-08-01 --end-date 2024-08-02 --estimate")
        print("  # Run backfill")
        print("  python backfill_historical.py --start-date 2024-08-01 --end-date 2024-08-02")
        print("  # Resume from last processed")
        print("  python backfill_historical.py --resume")
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import datetime
from db_helpers import _comment_to_row
from typing import Iterable, List, Dict
from nlp import extract_tickers, analyze_contextual_hype, inherit_tickers_with_context


load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def map_submission(s, skip_analysis=False):
    row = {
        "reddit_id": s.id,                               # <-- conflict key
        "title": (s.title or "").strip(),
        "text": (s.selftext or "").strip(),
        "url": getattr(s, "url", None),
        "author": str(s.author) if getattr(s, "author", None) else None,
        "score": int(getattr(s, "score", 0) or 0),
        "num_comments": int(getattr(s, "num_comments", 0) or 0),
        "total_awards": int(getattr(s, "total_awards_received", 0) or 0),
        "upvote_ratio": float(getattr(s, "upvote_ratio", 0.0) or 0.0),
        "created_utc": datetime.datetime.utcfromtimestamp(
            int(getattr(s, "created_utc", 0) or 0)
        ).isoformat() + "Z",
        "permalink": f"https://reddit.com{s.permalink}" if getattr(s, "permalink", None) else None,
        "subreddit": str(getattr(s, "subreddit", "") or "") or "wallstreetbets",
        "flair": str(getattr(s, "link_flair_text", "") or "")  # optional but useful
    }

    try:
        row["reddit_id_int"] = int(s.id, 36)
    except Exception:
        pass

    supabase.table("posts").upsert(row, on_conflict="reddit_id").execute()
    
    # Optionally skip LLM analysis during fast scraping
    if not skip_analysis:
        # Link tickers from the post's title + body
        post_text = f"{row.get('title','')}\n{row.get('text','')}"
        try:
            map_tickers_with_context(supabase, kind="post", content_reddit_id=row["reddit_id"], text=post_text)
        except Exception as e:
            print(f"[map_tickers post] failed for {row['reddit_id']}: {e}")
    else:
        print(f"[FAST SCRAPE] Skipped analysis for post {row['reddit_id']}")


def map_comments(submission, batch_size: int = 1000, skip_analysis=False) -> int:
    
    # Ensure the forest is expanded (pulls in MoreComments)
    submission.comments.replace_more(limit=None)
    forest: List = submission.comments.list()  # flat list with .depth populated

    post_reddit_id = submission.id  # base36 string; matches posts.reddit_id
    rows: List[dict] = []

    for c in forest:
        # PRAW can include Submission objects in .list() in rare cases; guard it
        if not hasattr(c, "id") or not getattr(c, "body", None):
            continue
        row = _comment_to_row(c, post_reddit_id)
        if row.get("reddit_id"):
            rows.append(row)
            
            # Optionally skip LLM analysis during fast scraping
            if not skip_analysis:
                try:
                    found = map_tickers_with_context(
                        supabase, kind="comment",
                        content_reddit_id=row["reddit_id"],
                        text=row.get("body",""),
                        post_reddit_id=post_reddit_id
                    )
                    # If none found, try inheritance from parent (fallback)
                    if not found and row.get("parent_reddit_id"):
                        inherit_parent_tickers(
                            supabase,
                            parent_reddit_id=row["parent_reddit_id"],
                            child_reddit_id=row["reddit_id"]
                        )
                except Exception as e:
                    print(f"[map_tickers comment] failed for {row['reddit_id']}: {e}")



    # Upsert in batches to avoid payload limits
    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        if not chunk:
            continue
        supabase.table("comments").upsert(chunk, on_conflict="reddit_id").execute()
        total += len(chunk)

    if skip_analysis:
        print(f"[FAST SCRAPE] Stored {total} comments without analysis")
    
    return total

def inherit_parent_tickers(supabase, parent_reddit_id: str, child_reddit_id: str) -> int:
    # get parent's tickers
    resp = (
        supabase.table("content_tickers")
        .select("ticker,confidence")
        .eq("content_reddit_id", parent_reddit_id)
        .order("confidence", desc=True)
        .execute()
    )
    parents = resp.data or []
    if not parents:
        return 0

    # build child rows with softened confidence
    rows = []
    for parent in parents:
        rows.append({
            "kind": "comment",
            "content_reddit_id": child_reddit_id,
            "ticker": parent["ticker"],
            "confidence": min(0.50, float(parent["confidence"]) * 0.8),
            "method": "inherit",
            "source": "inherited",
            "inherited_from": parent_reddit_id,
            # no spans for inherited
        })

    # upsert into content_tickers 
    (
        supabase.table("content_tickers")
        .upsert(rows, on_conflict="kind,content_reddit_id,ticker")
        .execute()
    )
    return len(rows)


def map_tickers_with_context(supabase, kind: str, content_reddit_id: str, text: str, post_reddit_id: str = None) -> List[Dict]:
    """
    Enhanced ticker mapping with contextual inheritance from post-level tickers.
    
    Args:
        supabase: Supabase client
        kind: "post" or "comment" 
        content_reddit_id: Reddit ID of the content
        text: Text content to analyze
        post_reddit_id: Reddit ID of the post (for contextual inheritance)
        
    Returns:
        List of ticker dictionaries found or inherited
    """
    # First try direct ticker extraction
    direct_tickers = extract_tickers(text or "")
    
    if direct_tickers:
        # Found direct tickers - store them and update aggregation
        rows = store_tickers_to_db(supabase, kind, content_reddit_id, direct_tickers, post_reddit_id)
        update_ticker_aggregation(supabase, direct_tickers, kind)
        return rows
    
    # No direct tickers found - try contextual inheritance for comments
    if kind == "comment" and post_reddit_id:
        return try_contextual_inheritance(supabase, content_reddit_id, text, post_reddit_id)
    
    return []


def try_contextual_inheritance(supabase, comment_reddit_id: str, comment_text: str, post_reddit_id: str) -> List[Dict]:
    """
    Attempt to inherit tickers from post context using contextual sentiment analysis.
    
    Args:
        supabase: Supabase client
        comment_reddit_id: Reddit ID of the comment
        comment_text: Comment text to analyze for contextual hype
        post_reddit_id: Reddit ID of the post to inherit from
        
    Returns:
        List of inherited ticker dictionaries
    """
    try:
        # Get tickers from the post
        post_tickers_resp = (
            supabase.table("content_tickers")
            .select("ticker, confidence, hype_score, company_name")
            .eq("content_reddit_id", post_reddit_id)
            .eq("kind", "post")
            .execute()
        )
        
        post_tickers = post_tickers_resp.data or []
        if not post_tickers:
            return []
        
        # Analyze comment for contextual hype
        contextual_hype = analyze_contextual_hype(comment_text)
        
        if contextual_hype < 0.3:  # Threshold for inheritance
            return []
        
        # Create inherited tickers
        inherited_tickers = inherit_tickers_with_context(
            post_tickers, 
            contextual_hype, 
            post_reddit_id
        )
        
        if inherited_tickers:
            # Store inherited tickers
            rows = store_tickers_to_db(
                supabase, 
                "comment", 
                comment_reddit_id, 
                inherited_tickers,
                post_reddit_id
            )
            
            # Update aggregation with inherited data
            update_ticker_aggregation(supabase, inherited_tickers, "comment")
            
            print(f"[CONTEXTUAL] Inherited {len(inherited_tickers)} tickers with hype {contextual_hype:.2f}")
            return rows
        
        return []
        
    except Exception as e:
        print(f"[CONTEXTUAL] Error in contextual inheritance: {e}")
        return []


def store_tickers_to_db(supabase, kind: str, content_reddit_id: str, tickers: List[Dict], post_reddit_id: str = None) -> List[Dict]:
    """
    Store ticker data to content_tickers table with enhanced metadata.
    
    Args:
        supabase: Supabase client
        kind: "post" or "comment"
        content_reddit_id: Reddit ID of content
        tickers: List of ticker dictionaries
        post_reddit_id: Reddit ID of post (for context tracking)
        
    Returns:
        List of stored ticker rows
    """
    if not tickers:
        return []

    # Collapse to one row per ticker: keep the highest-confidence occurrence
    best = {}
    for it in tickers:
        t = it["ticker"]
        if (t not in best) or (it["confidence"] > best[t]["confidence"]):
            best[t] = it

    rows = []
    for it in best.values():
        start, end = it.get("span", (-1, -1))
        row_data = {
            "kind": kind,
            "content_reddit_id": content_reddit_id,
            "ticker": it["ticker"],
            "confidence": float(it["confidence"]),
            "span_start": int(start) if start != -1 else None,
            "span_end": int(end) if end != -1 else None,
            "method": it["method"],
        }
        
        # Add enhanced fields
        if "hype_score" in it:
            row_data["hype_score"] = float(it["hype_score"])
        if "company_name" in it:
            row_data["company_name"] = it["company_name"]
        if "inheritance_source" in it:
            row_data["inheritance_source"] = it["inheritance_source"]  
        if "context_post_id" in it:
            row_data["context_post_id"] = it["context_post_id"]
        elif post_reddit_id and kind == "comment":
            row_data["context_post_id"] = post_reddit_id
            
        rows.append(row_data)

    # Store to database with error handling for schema compatibility
    try:
        supabase.table("content_tickers").upsert(
            rows, on_conflict="kind,content_reddit_id,ticker"
        ).execute()
    except Exception as e:
        if "column" in str(e).lower():
            # Fallback to basic fields for old schema
            print(f"[DB] Schema compatibility issue - storing basic fields only")
            basic_rows = []
            for row in rows:
                basic_row = {k: v for k, v in row.items() 
                           if k in ["kind", "content_reddit_id", "ticker", "confidence", "span_start", "span_end", "method"]}
                basic_rows.append(basic_row)
            
            supabase.table("content_tickers").upsert(
                basic_rows, on_conflict="kind,content_reddit_id,ticker"
            ).execute()
        else:
            raise e

    return rows


def update_ticker_aggregation(supabase, tickers: List[Dict], kind: str):
    """
    Update the ticker aggregation table with new ticker data.
    
    Args:
        supabase: Supabase client
        tickers: List of ticker dictionaries
        kind: "post" or "comment"
    """
    try:
        for ticker_data in tickers:
            ticker = ticker_data.get("ticker", "").upper()
            if not ticker:
                continue
                
            hype_score = ticker_data.get("hype_score", 0.0)
            company_name = ticker_data.get("company_name", "")
            
            # Check if ticker exists in aggregation table
            existing = supabase.table("tickers").select("*").eq("ticker", ticker).execute()
            
            if existing.data:
                # Update existing ticker
                current = existing.data[0]
                new_total = current["total_mentions"] + 1
                new_posts = current["total_posts"] + (1 if kind == "post" else 0)
                new_comments = current["total_comments"] + (1 if kind == "comment" else 0)
                
                # Calculate new average hype score
                current_avg = current.get("avg_hype_score", 0.0)
                new_avg = ((current_avg * current["total_mentions"]) + hype_score) / new_total
                max_hype = max(current.get("max_hype_score", 0.0), hype_score)
                
                supabase.table("tickers").update({
                    "total_mentions": new_total,
                    "total_posts": new_posts, 
                    "total_comments": new_comments,
                    "avg_hype_score": round(new_avg, 2),
                    "max_hype_score": round(max_hype, 2),
                    "last_mentioned_at": "NOW()",
                    "company_name": company_name or current.get("company_name", "")
                }).eq("ticker", ticker).execute()
                
            else:
                # Create new ticker entry
                supabase.table("tickers").insert({
                    "ticker": ticker,
                    "company_name": company_name,
                    "total_mentions": 1,
                    "total_posts": 1 if kind == "post" else 0,
                    "total_comments": 1 if kind == "comment" else 0,
                    "avg_hype_score": round(hype_score, 2),
                    "max_hype_score": round(hype_score, 2),
                    "last_mentioned_at": "NOW()"
                }).execute()
                
    except Exception as e:
        print(f"[AGGREGATION] Error updating ticker aggregation: {e}")




def map_tickers(supabase, kind: str, content_reddit_id: str, text: str) -> List[Dict]:
    """
    Legacy ticker mapping function - maintained for backward compatibility.
    New code should use map_tickers_with_context for enhanced functionality.
    """
    items = extract_tickers(text or "")
    if not items:
        return []

    # Store using new enhanced system
    rows = store_tickers_to_db(supabase, kind, content_reddit_id, items)
    
    # Update aggregation
    update_ticker_aggregation(supabase, items, kind)
    
    return rows




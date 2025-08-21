import os
from dotenv import load_dotenv
from supabase import create_client, Client
import datetime
from db_helpers import _comment_to_row
from typing import Iterable, List, Dict
from nlp import extract_tickers


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
            map_tickers(supabase, kind="post", content_reddit_id=row["reddit_id"], text=post_text)
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
                    found = map_tickers(
                        supabase, kind="comment",
                        content_reddit_id=row["reddit_id"],
                        text=row.get("body","")
                    )
                    # If none found, try inheritance from parent
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




def map_tickers(supabase, kind: str, content_reddit_id: str, text: str) -> List[Dict]:
    items = extract_tickers(text or "")
    if not items:
        return []

    # Collapse to one row per ticker: keep the highest-confidence occurrence.
    best = {}
    for it in items:
        t = it["ticker"]
        if (t not in best) or (it["confidence"] > best[t]["confidence"]):
            best[t] = it  # keep the best-scoring mention

    rows = []
    for it in best.values():
        start, end = it["span"]
        row_data = {
            "kind": kind,
            "content_reddit_id": content_reddit_id,
            "ticker": it["ticker"],
            "confidence": float(it["confidence"]),
            "span_start": int(start),
            "span_end": int(end),
            "method": it["method"],
        }
        
        # Add new fields from LLM if available
        if "hype_score" in it:
            row_data["hype_score"] = float(it["hype_score"])
        if "company_name" in it:
            row_data["company_name"] = it["company_name"]
            
        rows.append(row_data)

    # Try upsert with new fields first, fall back to basic fields if schema doesn't support them
    try:
        supabase.table("content_tickers").upsert(
            rows, on_conflict="kind,content_reddit_id,ticker"
        ).execute()
    except Exception as e:
        if "column" in str(e).lower() and ("company_name" in str(e) or "hype_score" in str(e)):
            print(f"[DB] Schema migration needed - falling back to basic ticker storage")
            # Retry with only basic fields (remove the new LLM fields)
            basic_rows = []
            for row in rows:
                basic_row = {k: v for k, v in row.items() if k not in ["hype_score", "company_name"]}
                basic_rows.append(basic_row)
            
            supabase.table("content_tickers").upsert(
                basic_rows, on_conflict="kind,content_reddit_id,ticker"
            ).execute()
            print(f"[DB] Successfully stored {len(basic_rows)} tickers without LLM metadata")
        else:
            # Re-raise if it's a different error
            raise e

    return rows




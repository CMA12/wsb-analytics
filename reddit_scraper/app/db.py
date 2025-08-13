import os
from dotenv import load_dotenv
from supabase import create_client, Client
import datetime
from db_helpers import _comment_to_row
from typing import Iterable, List



load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def map_submission(s):
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

def map_comments(submission, batch_size: int = 1000) -> int:
    
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

    # Upsert in batches to avoid payload limits
    total = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        if not chunk:
            continue
        supabase.table("comments").upsert(chunk, on_conflict="reddit_id").execute()
        total += len(chunk)

    return total


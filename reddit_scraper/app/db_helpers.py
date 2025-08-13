import datetime

def _comment_to_row(c, post_reddit_id: str) -> dict:
    """Convert a PRAW Comment into a DB row."""
    # parent_id comes as t1_XXXX or t3_XXXX; strip the prefix for reddit_id consistency
    parent = getattr(c, "parent_id", None)
    parent_reddit_id = parent.split("_", 1)[1] if parent and "_" in parent else None

    # awards: PRAW exposes awardings as a list of dicts
    awards = getattr(c, "all_awardings", None) or getattr(c, "awardings", None) or []

    created_ts = int(getattr(c, "created_utc", 0) or 0)
    created_iso = (
        datetime.datetime.utcfromtimestamp(created_ts).isoformat() + "Z"
        if created_ts
        else None
    )

    return {
        "reddit_id": getattr(c, "id", None),           # UNIQUE text
        "post_reddit_id": post_reddit_id,              # FK to posts.reddit_id
        "parent_reddit_id": parent_reddit_id,          # reddit_id of parent (post or comment)
        "author": str(getattr(c, "author", None)) if getattr(c, "author", None) else None,
        "body": (getattr(c, "body", "") or "").strip(),
        "created_utc": created_iso,
        "score": int(getattr(c, "score", 0) or 0),
        "depth": int(getattr(c, "depth", 0) or 0),
        "total_awards": int(getattr(c, "total_awards_received", 0) or 0),
        "awards": awards,                               # jsonb column recommended
    }

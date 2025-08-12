import os
from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def map_submission(s):
    int_id = int(s.id, 36)  # base36 → integer
    row = {
        "id": int_id,
        "title": s.title,
        "text": (s.selftext or "").strip(),
        "url": s.url,
        #"permalink": f"https://reddit.com{s.permalink}",
        "author": str(s.author) if s.author else None,
        "score": int(s.score),
        "num_comments": int(s.num_comments),
        "total_awards": int(s.total_awards_received or 0),   
    }
    supabase.table("posts").upsert(row, on_conflict="id").execute()


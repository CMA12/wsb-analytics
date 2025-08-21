#!/usr/bin/env python3

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

print("Testing imports...")

try:
    from dotenv import load_dotenv
    print("✅ dotenv imported")
    
    load_dotenv()
    print("✅ .env loaded")
    
    from db import supabase
    print("✅ supabase imported")
    
    import praw
    print("✅ praw imported")
    
    # Test Reddit connection
    reddit = praw.Reddit(
        client_id=os.getenv('CLIENT_ID'),
        client_secret=os.getenv('CLIENT_SECRET'),
        user_agent=os.getenv('USER_AGENT')
    )
    print("✅ Reddit client created")
    
    # Test getting one post
    subreddit = reddit.subreddit("wallstreetbets")
    print("✅ Subreddit accessed")
    
    print("Getting one post...")
    for submission in subreddit.hot(limit=1):
        print(f"✅ Got post: {submission.title[:50]}...")
        break
        
    print("All tests passed!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
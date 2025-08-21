#import asyncpraw
import praw
import pprint
import os
from dotenv import load_dotenv
from db import map_submission, map_comments

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    user_agent=os.getenv('USER_AGENT')
)


def loop_subreddit(sub_name):
    sub = reddit.subreddit(sub_name)

    for submission in sub.top(time_filter='day',limit=3):
        # map_submission(submission)
        # map_comments(submission)
        map_submission_and_comments(submission)


def map_submission_and_comments(submission):
    map_submission(submission)  # your existing function for posts
    try:
        n = map_comments(submission)
        print(f"Upserted {n} comments for post {submission.id}")
    except Exception as e:
        print(f"Comment upsert failed for {submission.id}: {e}")


loop_subreddit("wallstreetbets")






#import asyncpraw
import praw
import pprint
import os
from dotenv import load_dotenv
from db import map_submission

load_dotenv()

reddit = praw.Reddit(
    client_id=os.getenv('CLIENT_ID'),
    client_secret=os.getenv('CLIENT_SECRET'),
    user_agent=os.getenv('USER_AGENT')
)


def loop_subreddit(sub_name):
    sub = reddit.subreddit(sub_name)

    for submission in sub.top(time_filter='day',limit=1):
        map_submission(submission)
        #print(f'Title: {submission.title}')
        #print(f'Score: {submission.score}')
        #print(f'URL: {submission.url}')
        #print(f'TEXT: {submission.selftext}')
        #print(f'AWARDS: {submission.total_awards_received}')
        #print(f'Num comments: {submission.num_comments}')
        #all_comments = submission.comments.list()
        #print(all_comments)
        #pprint.pprint(vars(submission))
        #print('---')


loop_subreddit("wallstreetbets")






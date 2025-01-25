import praw
from datetime import datetime, timezone
import pandas as pd
import os
from prawcore.exceptions import ResponseException, OAuthException
import logging
from typing import Optional, Dict, Union, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditAnalyzer:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize RedditAnalyzer with optional credentials.
        If not provided, will attempt to get from environment variables.
        """
        self.client_id = client_id or os.environ.get('REDDIT_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('REDDIT_CLIENT_SECRET')

        if not self.client_id or not self.client_secret:
            raise ValueError("Reddit API credentials not found in parameters or environment variables")

        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent="script:reddit-analyzer:v1.0 (by /u/RedditAnalyzerBot)",
                check_for_async=False,
                read_only=True
            )
            logger.info("Verifying Reddit API connection...")
            # Use a simpler verification that doesn't require authentication
            self.reddit.subreddit('announcements').id
            logger.info("Reddit API connection successful")
        except ResponseException as e:
            logger.error(f"Reddit API error: {str(e)}")
            raise Exception(f"Reddit API error: {str(e)}")
        except Exception as e:
            logger.error(f"Error initializing Reddit client: {str(e)}")
            raise Exception(f"Error initializing Reddit client: {str(e)}")

    def get_user_data(self, username):
        try:
            logger.info(f"Fetching data for user: {username}")
            user = self.reddit.redditor(username)

            # Force a simple API call to verify the user exists
            created_utc = user.created_utc

            user_data = {
                'created_utc': datetime.fromtimestamp(created_utc, tz=timezone.utc),
                'comment_karma': user.comment_karma,
                'link_karma': user.link_karma,
                'verified_email': user.has_verified_email if hasattr(user, 'has_verified_email') else None,
            }

            # Collect recent comments with actual comment count
            comments = []
            comment_count = 0
            try:
                logger.info(f"Fetching recent comments for user: {username}")
                for comment in user.comments.new():  # Remove limit to get all comments
                    comment_count += 1
                    comments.append({
                        'body': comment.body,
                        'created_utc': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc),
                        'score': comment.score,
                        'subreddit': str(comment.subreddit)
                    })
                logger.info(f"Successfully fetched {comment_count} comments")
            except Exception as e:
                logger.warning(f"Could not fetch comments for user {username}: {str(e)}")
                if not comments:
                    comments = []

            return user_data, pd.DataFrame(comments)
        except ResponseException as e:
            if e.response.status_code == 404:
                logger.error(f"User '{username}' not found")
                raise Exception(f"User '{username}' not found")
            elif e.response.status_code == 403:
                logger.error(f"Access to user '{username}' data is forbidden")
                raise Exception(f"Access to user '{username}' data is forbidden. The account might be private or suspended.")
            logger.error(f"Error fetching user data: {str(e)}")
            raise Exception(f"Error fetching user data: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching user data: {str(e)}")
            raise Exception(f"Error fetching user data: {str(e)}")

    def analyze_activity_patterns(self, comments_df):
        if comments_df.empty:
            return {
                'total_comments': 0,
                'unique_subreddits': 0,
                'avg_score': 0,
                'activity_hours': {},
                'top_subreddits': {}
            }

        patterns = {
            'total_comments': len(comments_df),
            'unique_subreddits': comments_df['subreddit'].nunique(),
            'avg_score': comments_df['score'].mean(),
            'activity_hours': comments_df['created_utc'].dt.hour.value_counts().to_dict(),
            'top_subreddits': comments_df['subreddit'].value_counts().head(5).to_dict()
        }

        return patterns
import praw
from datetime import datetime, timezone
import pandas as pd
import os
from prawcore.exceptions import ResponseException, OAuthException
import logging
from typing import Optional, Dict, Union, Tuple, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RedditAnalyzer:
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id or os.environ.get('REDDIT_CLIENT_ID')
        self.client_secret = client_secret or os.environ.get('REDDIT_CLIENT_SECRET')

        if not self.client_id or not self.client_secret:
            raise ValueError("Reddit API credentials not found")

        try:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent="script:reddit-analyzer:v1.0 (by /u/RedditAnalyzerBot)",
                check_for_async=False,
                read_only=True
            )
            logger.info("Reddit API connection successful")
        except Exception as e:
            logger.error(f"Error initializing Reddit client: {str(e)}")
            raise

    def _fetch_user_content(self, user, content_type: str = 'comments', limit: Optional[int] = None) -> List[Dict]:
        """Fetch either comments or submissions for a user."""
        content_list = []
        one_year_ago = datetime.now(timezone.utc).timestamp() - (365 * 24 * 60 * 60)

        try:
            iterator = user.comments.new(limit=limit) if content_type == 'comments' else user.submissions.new(limit=limit)

            logger.info(f"Fetching {content_type} for user {user.name}")
            for item in iterator:
                if item.created_utc < one_year_ago:
                    break

                content_dict = {
                    'created_utc': datetime.fromtimestamp(item.created_utc, tz=timezone.utc),
                    'score': item.score,
                    'subreddit': str(item.subreddit),
                }

                if content_type == 'comments':
                    content_dict['body'] = item.body
                else:
                    content_dict['title'] = item.title
                    content_dict['is_self'] = item.is_self

                content_list.append(content_dict)

                if len(content_list) % 100 == 0:
                    logger.info(f"Fetched {len(content_list)} {content_type}")

            logger.info(f"Total {content_type} fetched: {len(content_list)}")
            return content_list

        except Exception as e:
            logger.error(f"Error fetching {content_type}: {str(e)}")
            return []

    def get_user_data(self, username: str) -> Tuple[Dict, pd.DataFrame, pd.DataFrame]:
        """Get user data including both comments and submissions."""
        try:
            logger.info(f"Analyzing user: {username}")
            user = self.reddit.redditor(username)

            # Basic user info
            user_data = {
                'created_utc': datetime.fromtimestamp(user.created_utc, tz=timezone.utc),
                'comment_karma': user.comment_karma,
                'link_karma': user.link_karma,
                'verified_email': user.has_verified_email if hasattr(user, 'has_verified_email') else None,
            }

            # Fetch both comments and submissions
            comments = self._fetch_user_content(user, 'comments')
            submissions = self._fetch_user_content(user, 'submissions')

            logger.info(f"Found {len(comments)} comments and {len(submissions)} submissions")

            return (
                user_data,
                pd.DataFrame(comments),
                pd.DataFrame(submissions)
            )

        except ResponseException as e:
            if e.response.status_code == 404:
                raise Exception(f"User '{username}' not found")
            elif e.response.status_code == 403:
                raise Exception(f"Access to user '{username}' data is forbidden")
            raise Exception(f"Error fetching user data: {str(e)}")
        except Exception as e:
            raise Exception(f"Error analyzing user: {str(e)}")

    def analyze_activity_patterns(self, comments_df: pd.DataFrame, submissions_df: pd.DataFrame) -> Dict:
        """Analyze activity patterns from both comments and submissions."""
        if comments_df.empty and submissions_df.empty:
            return {
                'total_comments': 0,
                'total_submissions': 0,
                'unique_subreddits': 0,
                'avg_score': 0,
                'activity_hours': {},
                'top_subreddits': {}
            }

        # Combine subreddits from both comments and submissions for analysis
        all_subreddits = pd.concat([
            comments_df['subreddit'] if not comments_df.empty else pd.Series(),
            submissions_df['subreddit'] if not submissions_df.empty else pd.Series()
        ])

        # Log activity stats
        logger.info(f"Total comments: {len(comments_df)}")
        logger.info(f"Total submissions: {len(submissions_df)}")
        logger.info(f"Unique subreddits: {all_subreddits.nunique()}")

        # Calculate average scores
        comments_avg = comments_df['score'].mean() if not comments_df.empty else 0
        submissions_avg = submissions_df['score'].mean() if not submissions_df.empty else 0

        # Combine timestamps for activity analysis
        all_times = pd.concat([
            comments_df['created_utc'] if not comments_df.empty else pd.Series(),
            submissions_df['created_utc'] if not submissions_df.empty else pd.Series()
        ])

        patterns = {
            'total_comments': len(comments_df),
            'total_submissions': len(submissions_df),
            'unique_subreddits': all_subreddits.nunique(),
            'avg_comment_score': comments_avg,
            'avg_submission_score': submissions_avg,
            'activity_hours': all_times.dt.hour.value_counts().to_dict(),
            'top_subreddits': all_subreddits.value_counts().head(5).to_dict()
        }

        return patterns
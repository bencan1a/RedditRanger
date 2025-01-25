import os
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.rate_limiter import RateLimiter
import uvicorn
from pydantic import BaseModel
from datetime import datetime
from config import get_settings, Settings
import logging

# Configure application logger
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Reddit Ranger API",
    version=get_settings().VERSION,
    description="Reddit account analysis API with ML-powered credibility insights"
)

settings = get_settings()

# Configure CORS with settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize analyzers and rate limiter
text_analyzer = TextAnalyzer()
account_scorer = AccountScorer()
rate_limiter = RateLimiter(tokens=5, fill_rate=0.1)  # 5 requests per 10 seconds

class AnalysisResponse(BaseModel):
    username: str
    probability: float
    summary: dict

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

@app.on_event("startup")
async def startup_event():
    """Log application startup and configuration"""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: CORS Origins configured for {settings.CORS_ORIGINS}")
    logger.info(f"Server running on {settings.HOST}:{settings.PORT}")

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API status"""
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        timestamp=datetime.utcnow().isoformat()
    )

async def check_rate_limit(request: Request):
    """Rate limiting dependency"""
    client_ip = request.client.host
    allowed, headers = rate_limiter.check_rate_limit(client_ip)

    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests",
            headers=headers
        )

    return headers

@app.get("/api/v1/analyze/{username}")
async def analyze_user(
    username: str,
    settings: Settings = Depends(get_settings),
    rate_limit_headers: dict = Depends(check_rate_limit)
):
    """Analyze Reddit user account"""
    logger.info(f"Analyzing user: {username}")
    try:
        # Create a new RedditAnalyzer instance for each request using settings
        reddit_analyzer = RedditAnalyzer(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET
        )

        # Fetch and analyze data
        user_data, comments_df, submissions_df = reddit_analyzer.get_user_data(username)
        activity_patterns = reddit_analyzer.analyze_activity_patterns(comments_df, submissions_df)
        text_metrics = text_analyzer.analyze_comments(
            comments_df['body'].tolist() if not comments_df.empty else []
        )
        final_score, component_scores = account_scorer.calculate_score(
            user_data, activity_patterns, text_metrics
        )

        response = AnalysisResponse(
            username=username,
            probability=(1 - final_score) * 100,  # Convert to percentage and invert for bot probability
            summary={
                "account_age": user_data['created_utc'].strftime('%Y-%m-%d'),
                "karma": user_data['comment_karma'] + user_data['link_karma'],
                "scores": component_scores,
                "activity_metrics": activity_patterns,
                "text_analysis": text_metrics
            }
        )

        # Add rate limit headers to response
        return {
            **response.dict(),
            "headers": rate_limit_headers
        }

    except Exception as e:
        logger.error(f"Error analyzing user {username}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
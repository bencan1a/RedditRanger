import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.rate_limiter import RateLimiter
from utils.database import init_db, get_db, AnalysisResult, User
from utils.auth import get_current_user, require_auth
from sqlalchemy.orm import Session
import uvicorn
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from config import get_settings, Settings
import logging

# Configure application logger
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources"""
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

    settings = get_settings()
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: CORS Origins configured for {settings.CORS_ORIGINS}")
    logger.info(f"Authentication enabled: {settings.ENABLE_AUTH}")
    logger.info(f"Server running on {settings.HOST}:5001")
    yield

app = FastAPI(
    title="Reddit Ranger API",
    version=get_settings().VERSION,
    description="Reddit account analysis API with ML-powered credibility insights",
    lifespan=lifespan
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

settings = get_settings()

# Configure CORS with settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=[*settings.CORS_ORIGINS],
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
    analysis_count: int
    last_analyzed: datetime
    analyzed_by: str | None = None
    model_config = ConfigDict(from_attributes=True)

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    auth_enabled: bool
    model_config = ConfigDict(from_attributes=True)

@app.get("/")
async def root():
    """Root endpoint providing API information and navigation."""
    return {
        "name": "Reddit Ranger API",
        "version": settings.VERSION,
        "description": "Reddit account analysis API with ML-powered credibility insights",
        "auth_enabled": settings.ENABLE_AUTH,
        "endpoints": {
            "health": "/health",
            "analyze_user": "/api/v1/analyze/{username}"
        },
        "documentation": "/docs"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API status"""
    logger.debug("Health check requested")
    return HealthResponse(
        status="healthy",
        version=settings.VERSION,
        timestamp=datetime.utcnow().isoformat(),
        auth_enabled=settings.ENABLE_AUTH
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
    rate_limit_headers: dict = Depends(check_rate_limit),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Optional user if auth enabled
):
    """Analyze Reddit user account and store results"""
    logger.info(f"Analyzing user: {username}")
    try:
        # Create a new RedditAnalyzer instance
        # Use user's Reddit OAuth tokens if available, otherwise fall back to app credentials
        reddit_credentials = {}
        if current_user and current_user.reddit_tokens:
            token = current_user.reddit_tokens
            if not token.is_expired:
                reddit_credentials = {
                    'access_token': token.access_token,
                    'token_type': token.token_type
                }

        if not reddit_credentials:
            reddit_credentials = {
                'client_id': settings.REDDIT_CLIENT_ID,
                'client_secret': settings.REDDIT_CLIENT_SECRET
            }

        reddit_analyzer = RedditAnalyzer(**reddit_credentials)

        # Fetch and analyze data
        user_data, comments_df, submissions_df = reddit_analyzer.get_user_data(username)
        activity_patterns = reddit_analyzer.analyze_activity_patterns(comments_df, submissions_df)
        text_metrics = text_analyzer.analyze_comments(
            comments_df['body'].tolist() if not comments_df.empty else []
        )
        final_score, component_scores = account_scorer.calculate_score(
            user_data, activity_patterns, text_metrics
        )

        # Store analysis result in database
        bot_probability = (1 - final_score) * 100
        analysis_result = AnalysisResult.get_or_create(
            db, 
            username, 
            bot_probability,
            user_id=current_user.id if current_user else None
        )
        db.commit()

        response = AnalysisResponse(
            username=username,
            probability=bot_probability,
            summary={
                "account_age": user_data['created_utc'].strftime('%Y-%m-%d'),
                "karma": user_data['comment_karma'] + user_data['link_karma'],
                "scores": component_scores,
                "activity_metrics": activity_patterns,
                "text_analysis": text_metrics
            },
            analysis_count=analysis_result.analysis_count,
            last_analyzed=analysis_result.last_analyzed,
            analyzed_by=current_user.email if current_user else None
        )

        # Add rate limit headers to response
        return {
            **response.model_dump(),
            "headers": rate_limit_headers
        }

    except Exception as e:
        logger.error(f"Error analyzing user {username}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=5001,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1
    )
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.rate_limiter import RateLimiter
from utils.database import init_db, get_db, AnalysisResult
from utils.performance_monitor import timing_decorator, PerformanceMonitor
from sqlalchemy.orm import Session
import uvicorn
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from config import get_settings, Settings
import logging
import time

# Configure application logger
logger = logging.getLogger(__name__)

@timing_decorator("app_startup")
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize application resources"""
    startup_time = time.time()
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

    settings = get_settings()
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info(f"Environment: CORS Origins configured for {settings.CORS_ORIGINS}")
    logger.info(f"Server running on {settings.HOST}:{settings.PORT}")

    total_startup_time = time.time() - startup_time
    PerformanceMonitor.record_metric("total_startup_time", total_startup_time)
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
    analysis_count: int
    last_analyzed: datetime
    model_config = ConfigDict(from_attributes=True)

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    model_config = ConfigDict(from_attributes=True)

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

@app.middleware("http")
async def add_performance_metrics(request: Request, call_next):
    """Middleware to track request performance"""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time

    # Record the request duration
    PerformanceMonitor.record_metric(
        f"request_{request.method}_{request.url.path}",
        duration
    )

    return response

@timing_decorator("analyze_user_endpoint")
@app.get("/api/v1/analyze/{username}")
async def analyze_user(
    username: str,
    settings: Settings = Depends(get_settings),
    rate_limit_headers: dict = Depends(check_rate_limit),
    db: Session = Depends(get_db)
):
    """Analyze Reddit user account and store results"""
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

        # Store analysis result in database
        bot_probability = (1 - final_score) * 100
        analysis_result = AnalysisResult.get_or_create(db, username, bot_probability)
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
            last_analyzed=analysis_result.last_analyzed
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
        host=settings.HOST,
        port=settings.PORT,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        workers=1  # Ensure single worker to avoid port conflicts
    )
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordRequestForm
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
from utils.rate_limiter import RateLimiter
from utils.database import init_db, get_db, AnalysisResult, User, RedditOAuthToken
from utils.auth import get_current_user, require_auth, create_access_token, require_admin
from sqlalchemy.orm import Session
import uvicorn
from pydantic import BaseModel, ConfigDict
from datetime import datetime, timedelta
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

# Auth models
class UserCreate(BaseModel):
    username: str
    password: str
    email: str | None = None
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    model_config = ConfigDict(from_attributes=True)

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

@app.post("/auth/register", response_model=Token)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user"""
    if not settings.ENABLE_AUTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication is not enabled"
        )

    # Check if username already exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Create new user
    user = User(username=user_data.username, email=user_data.email)
    user.set_password(user_data.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create access token
    access_token = create_access_token({"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")

@app.post("/auth/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login to get access token"""
    if not settings.ENABLE_AUTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication is not enabled"
        )

    # Find user
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not user.verify_password(form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token
    access_token = create_access_token({"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")

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
            "analyze_user": "/api/v1/analyze/{username}",
            "register": "/auth/register",
            "login": "/auth/login"
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
            analyzed_by=current_user.username if current_user else None
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
        workers=1
    )
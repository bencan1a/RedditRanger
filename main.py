import os
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
import uvicorn
from pydantic import BaseModel
from datetime import datetime
from config import get_settings, Settings

app = FastAPI(title="Reddit Ranger API")
settings = get_settings()

# Configure CORS with settings
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Initialize analyzers
text_analyzer = TextAnalyzer()
account_scorer = AccountScorer()

class AnalysisResponse(BaseModel):
    username: str
    probability: float
    summary: dict

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str

@app.get("/health")
async def health_check():
    """
    Health check endpoint to verify API status
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp=datetime.utcnow().isoformat()
    )

@app.get("/api/v1/analyze/{username}")
async def analyze_user(username: str, settings: Settings = Depends(get_settings)):
    try:
        # Create a new RedditAnalyzer instance for each request using settings
        reddit_analyzer = RedditAnalyzer(
            client_id=settings.REDDIT_CLIENT_ID,
            client_secret=settings.REDDIT_CLIENT_SECRET
        )

        # Fetch and analyze data
        user_data, comments_df = reddit_analyzer.get_user_data(username)
        activity_patterns = reddit_analyzer.analyze_activity_patterns(comments_df)
        text_metrics = text_analyzer.analyze_comments(comments_df['body'].tolist())
        final_score, component_scores = account_scorer.calculate_score(
            user_data, activity_patterns, text_metrics
        )

        return AnalysisResponse(
            username=username,
            probability=(1 - final_score) * 100,
            summary={
                "account_age": user_data['created_utc'].strftime('%Y-%m-%d'),
                "karma": user_data['comment_karma'] + user_data['link_karma'],
                "scores": component_scores
            }
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )
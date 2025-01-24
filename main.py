import streamlit as st
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from utils.reddit_analyzer import RedditAnalyzer
from utils.text_analyzer import TextAnalyzer
from utils.scoring import AccountScorer
import uvicorn
from pydantic import BaseModel

app = FastAPI()

# Enable CORS for browser extension
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize analyzers
reddit_analyzer = RedditAnalyzer()
text_analyzer = TextAnalyzer()
account_scorer = AccountScorer()

class AnalysisResponse(BaseModel):
    username: str
    probability: float
    summary: dict

@app.get("/analyze/{username}")
async def analyze_user(username: str):
    try:
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
    uvicorn.run(app, host="0.0.0.0", port=5001)
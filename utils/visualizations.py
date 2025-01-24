import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone

def create_score_radar_chart(scores):
    categories = list(scores.keys())
    values = list(scores.values())
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Account Scores'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1]
            )
        ),
        showlegend=False
    )
    
    return fig

def create_activity_heatmap(activity_hours):
    hours = list(range(24))
    activities = [activity_hours.get(hour, 0) for hour in hours]
    
    fig = go.Figure(data=go.Bar(
        x=hours,
        y=activities,
        name='Activity by Hour'
    ))
    
    fig.update_layout(
        title='Activity Distribution by Hour',
        xaxis_title='Hour of Day',
        yaxis_title='Number of Comments'
    )
    
    return fig

def create_subreddit_distribution(top_subreddits):
    fig = go.Figure(data=go.Pie(
        labels=list(top_subreddits.keys()),
        values=list(top_subreddits.values()),
        hole=0.3
    ))
    
    fig.update_layout(
        title='Top Subreddits Distribution'
    )
    
    return fig

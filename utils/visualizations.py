import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone
import pandas as pd

def create_score_radar_chart(scores):
    categories = list(scores.keys())
    values = list(scores.values())

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values,
        theta=categories,
        fill='toself',
        name='Account Scores',
        fillcolor='rgba(99, 110, 250, 0.5)',
        line=dict(color='rgb(99, 110, 250)', width=2)
    ))

    fig.update_layout(
        title={
            'text': 'Account Risk Analysis',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                tickformat='.0%',
                gridcolor='rgba(255, 255, 255, 0.1)',
                linecolor='rgba(255, 255, 255, 0.1)'
            ),
            angularaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.1)',
                linecolor='rgba(255, 255, 255, 0.1)'
            ),
            bgcolor='rgba(0, 0, 0, 0)'
        ),
        showlegend=False,
        margin=dict(t=50, b=20, l=40, r=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_monthly_activity_chart(comments_df):
    if comments_df.empty:
        return go.Figure()

    # Resample data by month and count
    monthly_activity = (
        comments_df.set_index('created_utc')
        .resample('M')
        .size()
        .reset_index()
    )
    monthly_activity.columns = ['month', 'count']

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=monthly_activity['month'],
        y=monthly_activity['count'],
        mode='lines+markers',
        name='Posts per Month',
        line=dict(width=3, color='rgb(99, 110, 250)'),
        marker=dict(
            size=8,
            color='rgb(99, 110, 250)',
            line=dict(width=2, color='rgb(255, 255, 255)')
        ),
        fill='tozeroy',
        fillcolor='rgba(99, 110, 250, 0.1)'
    ))

    fig.update_layout(
        title={
            'text': 'Monthly Activity Timeline',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        xaxis=dict(
            title="Month",
            showgrid=True,
            gridcolor='rgba(255, 255, 255, 0.1)',
            tickangle=45,
            nticks=12,
            showline=True,
            linecolor='rgba(255, 255, 255, 0.2)'
        ),
        yaxis=dict(
            title="Number of Posts",
            showgrid=True,
            gridcolor='rgba(255, 255, 255, 0.1)',
            showline=True,
            linecolor='rgba(255, 255, 255, 0.2)'
        ),
        showlegend=False,
        margin=dict(t=50, b=50, l=40, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_subreddit_distribution(top_subreddits):
    # Create a color sequence that's visually distinct
    colors = px.colors.qualitative.Set3

    fig = go.Figure(data=go.Pie(
        labels=list(top_subreddits.keys()),
        values=list(top_subreddits.values()),
        hole=0.3,
        marker=dict(colors=colors),
        textinfo='label+percent',
        textposition='outside',
        insidetextorientation='radial'
    ))

    fig.update_layout(
        title={
            'text': 'Top Subreddits Distribution',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top'
        },
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            bgcolor='rgba(0,0,0,0)'
        ),
        margin=dict(t=50, b=80, l=20, r=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
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
        title={
            'text': 'Activity Distribution by Hour',
            'y':0.95,
            'x':0.5,
            'xanchor':'center',
            'yanchor':'top'
        },
        xaxis_title='Hour of Day',
        yaxis_title='Number of Comments',
        showlegend=False,
        margin=dict(t=50, b=20, l=20, r=20)
    )
    
    return fig
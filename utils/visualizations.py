import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def create_score_radar_chart(scores):
    # Remove "_score" suffix from category names
    categories = [cat.replace('_score', '') for cat in scores.keys()]
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
            'text': 'Risk Analysis',
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
                linecolor='rgba(255, 255, 255, 0.1)',
                tickfont=dict(color='#E6D5B8')  # Match the theme text color
            ),
            angularaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.1)',
                linecolor='rgba(255, 255, 255, 0.1)',
                tickfont=dict(color='#E6D5B8')  # Match the theme text color
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
    """Create a monthly activity chart from comments dataframe."""
    # Debug logging for raw data
    logger.info(f"Total comments in dataframe: {len(comments_df)}")
    logger.info("Raw comment dates:")
    for date in comments_df['created_utc'].tolist():
        logger.info(f"Comment date: {date}")

    # Ensure we're working with UTC timestamps
    now = pd.Timestamp.now(tz='UTC')
    one_year_ago = now - pd.DateOffset(months=12)

    logger.info(f"Filtering between {one_year_ago} and {now}")

    # Convert created_utc to datetime if it isn't already
    if not pd.api.types.is_datetime64_any_dtype(comments_df['created_utc']):
        comments_df['created_utc'] = pd.to_datetime(comments_df['created_utc'], utc=True)

    # Filter and resample
    mask = (comments_df['created_utc'] >= one_year_ago) & (comments_df['created_utc'] <= now)
    filtered_df = comments_df[mask]
    logger.info(f"Comments after date filtering: {len(filtered_df)}")

    monthly_activity = (
        filtered_df
        .resample('M', on='created_utc')
        .size()
        .reset_index()
    )
    monthly_activity.columns = ['month', 'count']

    # Log the final aggregated data
    logger.info("Monthly aggregated data:")
    for _, row in monthly_activity.iterrows():
        logger.info(f"Month: {row['month']}, Count: {row['count']}")

    # Create the figure
    fig = go.Figure(data=go.Scatter(
        x=monthly_activity['month'],
        y=monthly_activity['count'],
        mode='lines+markers',
        line=dict(color='#E6D5B8', width=2),
        marker=dict(
            size=8,
            color='#E6D5B8',
            line=dict(color='#ff9800', width=2)
        )
    ))

    # Update layout with custom styling
    fig.update_layout(
        title={
            'text': 'Trailing 12 Month Activity',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(color='#E6D5B8')
        },
        xaxis=dict(
            title="Month",
            showgrid=True,
            gridcolor='rgba(255, 255, 255, 0.1)',
            tickangle=45,
            showline=True,
            linecolor='rgba(255, 255, 255, 0.2)',
            tickmode='array',
            ticktext=[d.strftime('%b %y') for d in monthly_activity['month']],
            tickvals=monthly_activity['month'],
            tickfont=dict(color='#E6D5B8')
        ),
        yaxis=dict(
            title="Number of Posts",
            showgrid=True,
            gridcolor='rgba(255, 255, 255, 0.1)',
            showline=True,
            linecolor='rgba(255, 255, 255, 0.2)',
            tickfont=dict(color='#E6D5B8')
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
            'text': 'Top Subreddits',
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
            bgcolor='rgba(0,0,0,0)',
            font=dict(color='#E6D5B8')  # Match theme text color
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
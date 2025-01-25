import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone
import pandas as pd
import logging
from datetime import datetime, timezone
from typing import Dict

logger = logging.getLogger(__name__)

def create_score_radar_chart(scores):
    """Create a radar chart visualization of account scores."""
    logger.debug(f"Creating radar chart with scores: {scores}")

    # Filter out non-score keys and format names
    score_items = {k: v for k, v in scores.items() if isinstance(v, (int, float)) and k != 'metrics'}
    logger.debug(f"Filtered score items: {score_items}")

    # Remove "_score" suffix from category names
    categories = [cat.replace('_score', '') for cat in score_items.keys()]
    values = list(score_items.values())

    logger.debug(f"Radar chart categories: {categories}")
    logger.debug(f"Radar chart values: {values}")

    if not categories or not values:
        logger.warning("No valid scores found for radar chart")
        # Return an empty figure with a warning
        fig = go.Figure()
        fig.add_annotation(
            text="No score data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color="#E6D5B8")
        )
        return fig

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
                tickfont=dict(color='#E6D5B8')
            ),
            angularaxis=dict(
                gridcolor='rgba(255, 255, 255, 0.1)',
                linecolor='rgba(255, 255, 255, 0.1)',
                tickfont=dict(color='#E6D5B8')
            ),
            bgcolor='rgba(0, 0, 0, 0)'
        ),
        showlegend=False,
        margin=dict(t=50, b=20, l=40, r=40),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def create_monthly_activity_chart(activity_data: pd.DataFrame) -> go.Figure:
    """Create a bar chart showing monthly activity trends."""
    fig = go.Figure()

    # Add comments bars
    fig.add_trace(go.Bar(
        x=activity_data['month'],
        y=activity_data['comments'],
        name='Comments',
        marker_color='#E6D5B8'
    ))

    # Add submissions bars
    fig.add_trace(go.Bar(
        x=activity_data['month'],
        y=activity_data['submissions'],
        name='Submissions',
        marker_color='#ff9800'
    ))

    # Update layout
    fig.update_layout(
        title={
            'text': 'Monthly Activity',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(color='#E6D5B8')
        },
        barmode='group',
        xaxis=dict(
            title="Month",
            tickangle=45,
            gridcolor='rgba(255, 255, 255, 0.1)',
            tickfont=dict(color='#E6D5B8')
        ),
        yaxis=dict(
            title="Count",
            gridcolor='rgba(255, 255, 255, 0.1)',
            tickfont=dict(color='#E6D5B8')
        ),
        showlegend=True,
        legend=dict(
            font=dict(color='#E6D5B8'),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=50, l=40, r=20)
    )

    return fig

def create_monthly_activity_table(comments_df, submissions_df) -> pd.DataFrame:
    """Create a monthly activity table showing comment and submission counts."""
    try:
        # Initialize with current time in UTC
        now = pd.Timestamp.now(tz='UTC')
        eleven_months_ago = now - pd.DateOffset(months=11)

        def get_monthly_counts(df, start_date):
            """Get monthly counts for a dataframe."""
            if df.empty:
                return pd.DataFrame(columns=['month', 'count'])

            # Ensure datetime is in UTC
            if not pd.api.types.is_datetime64_any_dtype(df['created_utc']):
                df['created_utc'] = pd.to_datetime(df['created_utc'], utc=True)

            # Filter to last 12 months
            mask = df['created_utc'] >= start_date
            filtered = df[mask]

            if filtered.empty:
                return pd.DataFrame(columns=['month', 'count'])

            # Group by month and count
            monthly = filtered.groupby(filtered['created_utc'].dt.strftime('%Y-%m'))\
                             .size()\
                             .reset_index(name='count')
            monthly.columns = ['month', 'count']
            return monthly

        # Get counts for both types
        comments_monthly = get_monthly_counts(comments_df, eleven_months_ago)
        submissions_monthly = get_monthly_counts(submissions_df, eleven_months_ago)

        # Create date range for last 12 months
        months = pd.date_range(
            start=eleven_months_ago,
            end=now,
            freq='MS'  # Month Start
        ).strftime('%Y-%m').tolist()

        # Create final dataframe
        result = pd.DataFrame({'month': months})
        result = result.merge(
            comments_monthly, 
            on='month', 
            how='left'
        ).rename(columns={'count': 'comments'})
        result = result.merge(
            submissions_monthly,
            on='month',
            how='left'
        ).rename(columns={'count': 'submissions'})

        # Fill NaN with 0
        result = result.fillna(0)
        result[['comments', 'submissions']] = result[['comments', 'submissions']].astype(int)

        # Log the results
        logger.info("Monthly activity data:")
        for _, row in result.iterrows():
            logger.info(f"Month: {row['month']}, Comments: {row['comments']}, Submissions: {row['submissions']}")

        return result

    except Exception as e:
        logger.error(f"Error creating activity table: {str(e)}")
        # Return empty dataframe with correct columns
        return pd.DataFrame(columns=['month', 'comments', 'submissions'])

def create_subreddit_distribution(top_subreddits):
    """Create a simple dictionary of top subreddits and their post counts."""
    return top_subreddits

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

def create_bot_analysis_chart(text_metrics: Dict, activity_patterns: Dict) -> go.Figure:
    """Create a comprehensive bot analysis visualization."""
    # Combine all bot-related metrics
    bot_metrics = {
        'Text Patterns': {
            'Repetitive Phrases': text_metrics.get('repetition_score', 0),
            'Template Usage': text_metrics.get('template_score', 0),
            'Language Complexity': text_metrics.get('complexity_score', 0),
            'Copy-Paste Content': text_metrics.get('copy_paste_score', 0)
        },
        'Timing Patterns': {
            'Regular Intervals': activity_patterns.get('bot_patterns', {}).get('regular_intervals', 0),
            'Rapid Responses': activity_patterns.get('bot_patterns', {}).get('rapid_responses', 0),
            'Automated Timing': activity_patterns.get('bot_patterns', {}).get('automated_timing', 0)
        },
        'Suspicious Patterns': {
            'Generic Responses': text_metrics.get('suspicious_patterns', {}).get('generic_responses', 0) / 100,
            'Promotional Content': text_metrics.get('suspicious_patterns', {}).get('promotional_phrases', 0) / 100,
            'URL Patterns': text_metrics.get('suspicious_patterns', {}).get('url_patterns', 0) / 100
        }
    }

    # Create figure with secondary y-axis
    fig = go.Figure()

    # Add traces for each category
    colors = ['rgb(99, 110, 250)', 'rgb(239, 85, 59)', 'rgb(0, 204, 150)']

    for i, (category, metrics) in enumerate(bot_metrics.items()):
        values = list(metrics.values())
        labels = list(metrics.keys())

        fig.add_trace(go.Bar(
            name=category,
            x=labels,
            y=values,
            marker_color=colors[i]
        ))

    # Update layout
    fig.update_layout(
        title={
            'text': 'Bot Behavior Analysis',
            'y': 0.95,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': dict(color='#E6D5B8')
        },
        barmode='group',
        xaxis=dict(
            title="Metrics",
            tickangle=45,
            gridcolor='rgba(255, 255, 255, 0.1)',
            tickfont=dict(color='#E6D5B8')
        ),
        yaxis=dict(
            title="Score",
            gridcolor='rgba(255, 255, 255, 0.1)',
            tickfont=dict(color='#E6D5B8'),
            range=[0, 1]
        ),
        showlegend=True,
        legend=dict(
            font=dict(color='#E6D5B8'),
            bgcolor='rgba(0,0,0,0)'
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=50, b=100, l=40, r=20)
    )

    return fig
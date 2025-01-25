import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timezone
import pandas as pd
import logging
from datetime import datetime, timezone

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

def create_monthly_activity_table(comments_df, submissions_df):
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
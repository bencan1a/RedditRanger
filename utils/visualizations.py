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

def create_monthly_activity_chart(comments_df, submissions_df):
    """Create a monthly activity chart showing both comments and submissions."""
    # Debug logging
    logger.info(f"Creating chart with {len(comments_df)} comments and {len(submissions_df)} submissions")

    # Ensure we're working with UTC timestamps
    now = pd.Timestamp.now(tz='UTC')
    eleven_months_ago = now - pd.DateOffset(months=11)  # Changed from 12 to 11 to include current month

    def process_activity(df, activity_type):
        """Process activity data for either comments or submissions."""
        # Create a date range covering current month plus prior 11 months
        date_range = pd.date_range(
            start=eleven_months_ago.replace(day=1),  # Start from first day of month
            end=now + pd.offsets.MonthEnd(0),  # Ensure current month is included
            freq='ME',  # Monthly frequency
            tz='UTC'  # Ensure timezone awareness
        )

        # Create an empty DataFrame with all months
        monthly_template = pd.DataFrame({
            'month': date_range,
            'count': 0
        })

        if df.empty:
            logger.info(f"No {activity_type} data available")
            return monthly_template

        # Convert timestamps if needed
        if not pd.api.types.is_datetime64_any_dtype(df['created_utc']):
            df['created_utc'] = pd.to_datetime(df['created_utc'], utc=True)

        # Filter and resample
        mask = (df['created_utc'] >= eleven_months_ago) & (df['created_utc'] <= now)
        filtered = df[mask]

        if filtered.empty:
            return monthly_template

        # Group by month and count
        monthly = filtered.groupby(pd.Grouper(
            key='created_utc',
            freq='ME'  # Month End frequency
        )).size().reset_index()
        monthly.columns = ['month', 'count']

        # Merge with template to ensure all months are present
        monthly = pd.merge(
            monthly_template,
            monthly,
            on='month',
            how='left'
        )

        # Use the count from actual data where available, otherwise keep 0
        monthly['count'] = monthly['count_y'].fillna(monthly['count_x'])
        monthly = monthly[['month', 'count']]

        # Debug logging
        logger.info(f"Monthly {activity_type} data:")
        for _, row in monthly.iterrows():
            logger.info(f"Month: {row['month']}, Count: {row['count']}")

        return monthly

    # Process both types of activity
    comments_monthly = process_activity(comments_df, 'comments')
    posts_monthly = process_activity(submissions_df, 'submissions')

    # Create figure with two traces
    fig = go.Figure()

    # Add comments trace
    fig.add_trace(go.Scatter(
        x=comments_monthly['month'],
        y=comments_monthly['count'],
        name='Comments',
        mode='lines+markers',
        line=dict(color='#E6D5B8', width=2),
        marker=dict(
            size=8,
            color='#E6D5B8',
            line=dict(color='#ff9800', width=2)
        )
    ))

    # Add posts trace
    fig.add_trace(go.Scatter(
        x=posts_monthly['month'],
        y=posts_monthly['count'],
        name='Posts',
        mode='lines+markers',
        line=dict(color='#ff9800', width=2),
        marker=dict(
            size=8,
            color='#ff9800',
            line=dict(color='#E6D5B8', width=2)
        )
    ))

    # Update layout
    fig.update_layout(
        title={
            'text': 'Monthly Activity Timeline',
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
            tickfont=dict(color='#E6D5B8'),
            # Ensure x-axis shows all months
            tickmode='array',
            ticktext=[d.strftime('%b %Y') for d in comments_monthly['month']],
            tickvals=comments_monthly['month']
        ),
        yaxis=dict(
            title="Count",
            showgrid=True,
            gridcolor='rgba(255, 255, 255, 0.1)',
            showline=True,
            linecolor='rgba(255, 255, 255, 0.2)',
            tickfont=dict(color='#E6D5B8'),
            # Explicitly set y-axis range to start at 0
            range=[0, max(max(comments_monthly['count'].max(), posts_monthly['count'].max()) * 1.1, 1)]
        ),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            font=dict(color='#E6D5B8'),
            bgcolor='rgba(0,0,0,0)'
        ),
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
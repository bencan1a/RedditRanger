from datetime import datetime, timedelta
import os
import logging
from functools import lru_cache
import pandas as pd
import time
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, func, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)

# Create database engine with proper error handling
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database engine initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize database engine: {str(e)}")
    raise

Base = declarative_base()

class AnalysisResult(Base):
    """Store Reddit user analysis results"""
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    bot_probability = Column(Float)
    analysis_count = Column(Integer, default=1)
    last_analyzed = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    @classmethod
    @lru_cache(maxsize=100)
    def get_cached(cls, username: str) -> dict:
        """Get cached analysis result if it exists and is recent"""
        try:
            with SessionLocal() as db:
                result = db.query(cls).filter_by(username=username).first()
                if result and (datetime.utcnow() - result.last_analyzed) < timedelta(hours=1):
                    return {
                        'username': result.username,
                        'bot_probability': result.bot_probability,
                        'analysis_count': result.analysis_count,
                        'last_analyzed': result.last_analyzed
                    }
                return None
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_cached: {str(e)}")
            return None

    @classmethod
    def get_or_create(cls, db_session, username: str, bot_probability: float) -> 'AnalysisResult':
        """Get existing result or create new one"""
        try:
            instance = db_session.query(cls).filter_by(username=username).first()
            if instance:
                instance.bot_probability = bot_probability
                instance.analysis_count += 1
                instance.last_analyzed = datetime.utcnow()
                # Update cache
                cls.get_cached.cache_clear()
                logger.debug(f"Updated existing analysis for {username}")
            else:
                instance = cls(
                    username=username,
                    bot_probability=bot_probability
                )
                db_session.add(instance)
                logger.debug(f"Created new analysis for {username}")
            return instance
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_or_create: {str(e)}")
            raise

    @classmethod
    def get_all_analysis_stats(cls) -> pd.DataFrame:
        """Get all analysis results for statistics page"""
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                with SessionLocal() as db:
                    results = db.query(
                        cls.username,
                        cls.last_analyzed,
                        cls.analysis_count,
                        cls.bot_probability
                    ).all()

                    return pd.DataFrame([
                        {
                            'Username': r.username,
                            'Last Analyzed': r.last_analyzed,
                            'Analysis Count': r.analysis_count,
                            'Bot Probability': f"{r.bot_probability:.1f}%"
                        }
                        for r in results
                    ])

            except Exception as e:
                logger.error(f"Database error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    logger.error("Maximum retries reached, raising error")
                    raise
                time.sleep(retry_delay)
                continue

        # This should never be reached due to the raise in the last attempt
        return pd.DataFrame()  # Return empty DataFrame as fallback

def init_db():
    """Initialize the database tables"""
    try:
        Base.metadata.create_all(bind=engine)
        # Test database connection with proper text() usage
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database tables created and connection tested successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
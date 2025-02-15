from datetime import datetime, timedelta
import os
import logging
from functools import lru_cache
import pandas as pd
import time
from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, func, text
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

class Database:
    """Singleton database connection manager with connection pooling."""
    _instance = None
    _initialized = False
    _engine = None
    _SessionLocal = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._initialized = True
            logger.info("Database manager initialized")

    @property
    def engine(self):
        """Lazy initialize database engine with connection pooling."""
        if self._engine is None:
            DATABASE_URL = os.environ.get('DATABASE_URL')
            if not DATABASE_URL:
                raise ValueError("DATABASE_URL environment variable is not set")

            try:
                logger.info("Initializing database engine with connection pool")
                self._engine = create_engine(
                    DATABASE_URL,
                    poolclass=QueuePool,
                    pool_size=5,
                    max_overflow=10,
                    pool_timeout=30,
                    pool_recycle=1800,
                    pool_pre_ping=True  # Added to handle stale connections
                )
                # Test connection
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                logger.info("Database engine initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize database engine: {str(e)}")
                raise
        return self._engine

    @property
    def SessionLocal(self):
        """Lazy initialize session factory."""
        if self._SessionLocal is None:
            self._SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
        return self._SessionLocal

# Initialize singleton instance
db = Database()
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
            with db.SessionLocal() as session:
                result = session.query(cls).filter_by(username=username).first()
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
        """Get existing result or create new one with retry logic"""
        max_retries = 3
        retry_delay = 0.5  # seconds
        last_error = None

        for attempt in range(max_retries):
            try:
                # Start a nested transaction
                with db_session.begin_nested():
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

                    # Flush changes within the transaction
                    db_session.flush()
                    return instance

            except SQLAlchemyError as e:
                last_error = e
                logger.warning(f"Database operation failed on attempt {attempt + 1}: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                    continue
                logger.error(f"Database error in get_or_create after {max_retries} attempts: {str(e)}")
                raise last_error

    @classmethod
    def get_all_analysis_stats(cls) -> pd.DataFrame:
        """Get all analysis results for statistics page with retry logic"""
        max_retries = 3
        retry_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                with db.SessionLocal() as session:
                    with session.begin():  # Ensure transaction
                        results = session.query(
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
                time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                continue

        # This should never be reached due to the raise in the last attempt
        return pd.DataFrame()  # Return empty DataFrame as fallback

def init_db():
    """Initialize the database tables"""
    try:
        Base.metadata.create_all(bind=db.engine)
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

def get_db():
    """Get database session with automatic retry on connection failure"""
    max_retries = 3
    retry_delay = 0.5  # seconds

    for attempt in range(max_retries):
        try:
            session = db.SessionLocal()
            # Test the connection
            session.execute(text("SELECT 1"))
            return session
        except SQLAlchemyError as e:
            logger.warning(f"Failed to create database session (attempt {attempt + 1}): {str(e)}")
            if attempt == max_retries - 1:
                logger.error("Maximum retries reached, raising error")
                raise
            time.sleep(retry_delay * (attempt + 1))
            continue
        finally:
            session.close()

# Export SessionLocal for backward compatibility
SessionLocal = db.SessionLocal
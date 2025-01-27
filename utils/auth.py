from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from google.oauth2 import id_token
from google.auth.transport import requests
from sqlalchemy.orm import Session
from utils.database import User, get_db
from config import get_settings
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth",
    tokenUrl="https://oauth2.googleapis.com/token",
    auto_error=False
)

settings = get_settings()

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user from token if auth is enabled"""
    if not settings.ENABLE_AUTH:
        return None
        
    if not token:
        return None

    try:
        # Verify the token with Google
        idinfo = id_token.verify_oauth2_token(
            token, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )

        # Get or create user
        email = idinfo['email']
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            user = User(
                email=email,
                name=idinfo.get('name'),
                google_id=idinfo['sub']
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            
        return user

    except Exception as e:
        logger.error(f"Error validating token: {str(e)}")
        return None

def require_auth(user: Optional[User] = Depends(get_current_user)):
    """Require authentication if enabled"""
    if settings.ENABLE_AUTH and not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

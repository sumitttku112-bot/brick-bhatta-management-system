from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import jwt
from .database import SessionLocal
from . import security

# Database Dependency
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


bearer_scheme = HTTPBearer()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer_scheme), db: Session = Depends(get_db)):
    """
    Verifies the JWT in the Authorization header and loads the user.
    Returns a dict with 'uid' (the user id) and 'phone_number'.
    """
    from . import crud

    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = security.decode_access_token(creds.credentials)
    except jwt.PyJWTError:
        raise unauthorized

    user = crud.get_user(db, payload.get("sub", ""))
    if user is None or not user.is_active:
        raise unauthorized

    return {"uid": user.id, "phone_number": user.phone_number}

def get_user_context(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get user context including role from database.
    Returns dict with user_id and role.
    """
    from . import crud

    user = crud.get_user(db, current_user['uid'])
    return {"user_id": user.id, "role": user.role, "name": user.name}

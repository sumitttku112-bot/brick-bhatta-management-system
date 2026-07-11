from typing import Generator
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import SessionLocal
import firebase_admin
from firebase_admin import auth, credentials
import os
import json

# Database Dependency
def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Firebase Init (SAFE + SIMPLE) - Optional for development
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
firebase_key_path = os.path.join(BASE_DIR, "firebase-key.json")

if not firebase_admin._apps:
    # Try environment variable first (best for Production)
    firebase_json = os.getenv("FIREBASE_KEY_JSON")
    
    if firebase_json:
        try:
            cred_dict = json.loads(firebase_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("✅ Firebase initialized successfully from environment variable")
        except Exception as e:
            print(f"❌ Failed to initialize Firebase from environment variable: {e}")
    elif os.path.exists(firebase_key_path):
        # Fallback to local file
        cred = credentials.Certificate(firebase_key_path)
        firebase_admin.initialize_app(cred)
        print("✅ Firebase initialized successfully from firebase-key.json")
    else:
        # Don't block startup - Firebase is only needed for token verification
        print("⚠️  Firebase key not found (no FIREBASE_KEY_JSON env or firebase-key.json file)")
        print("⚠️  Backend will start, but Firebase token verification will fail")


security = HTTPBearer()

def get_current_user(creds: HTTPAuthorizationCredentials = Depends(security)):
    """
    Verifies the Firebase ID token in the Authorization header.
    Returns the decoded token dict (uid, email, etc) if valid.
    For development: If Firebase is not initialized, accepts any token.
    """
    token = creds.credentials
    
    # Check if Firebase is initialized
    if not firebase_admin._apps:
        # Firebase not initialized - allow in development
        print("⚠️  Firebase not initialized - accepting token for development")
        print(f"⚠️  Token received: {token[:20]}...")
        return {"uid": "dev_user", "phone_number": "dev_phone"}
    
    try:
        # In a real deployed env with valid creds:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"Auth Error: {e}")
        # For development, if Firebase is initialized but verification fails,
        # we still reject (this means there's a real auth issue)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_user_context(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get user context including role from database.
    Returns dict with user_id and role.
    Checks both Users table and Names table (for Kaccha/Pakka Muneem).
    """
    from . import crud
    
    firebase_uid = current_user.get('uid')
    
    # Try to find user in Users table by Firebase UID
    user = crud.get_user(db, firebase_uid)
    if user:
        return {"user_id": user.id, "role": user.role, "name": user.name}
    
    # If not in Users table, try to find by phone number in Names table
    phone = current_user.get('phone_number')
    if phone:
        user = crud.get_user_by_phone(db, phone)
        if user:
            return {"user_id": user.id, "role": user.role, "name": user.name}
    
    # Default to a basic user context (shouldn't happen if auth is working)
    return {"user_id": firebase_uid, "role": "User", "name": "Unknown"}


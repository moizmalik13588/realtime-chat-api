from fastapi import APIRouter,Depends, HTTPException, Request, Response, Cookie
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import Base,get_db
from auth.auth_security import create_access_token, decode_access_token, create_refresh_token, hash_token
from auth.auth_security import hash_token
from datetime import datetime, timedelta, UTC
import models

router = APIRouter()

@router.post("/refresh-token")
def refresh_access_token(response: Response, refresh_token: str = Cookie(None), db: Session = Depends(get_db)):
    if refresh_token is None:
        raise HTTPException(status_code=401, detail="No refresh token found")

    payload = decode_access_token(refresh_token)
    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid or expiry token")
    if payload["type"] != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    hashed = hash_token(refresh_token)
    db_token = db.query(models.RefreshToken).filter(
        models.RefreshToken.token_hash == hashed,
        models.RefreshToken.is_revoked == False
    ).first()
    if not db_token:
        raise HTTPException(status_code=401, detail="Refresh token revoked or not found")

    user = db.query(models.User).filter(models.User.id == payload["userId"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # New access token
    new_access_token = create_access_token({"userId": user.id, "username": user.username, "role": user.role})

    #(ROTATION)
    new_refresh_token = create_refresh_token({"userId": user.id})
    new_hashed = hash_token(new_refresh_token)

    db_token.token_hash = new_hashed   
    db_token.expires_at = datetime.now(UTC) + timedelta(days=7)
    db.commit()

    response.set_cookie(key="access_token", value=new_access_token, httponly=True, max_age=15 * 60)
    response.set_cookie(key="refresh_token", value=new_refresh_token, httponly=True, max_age=7 * 24 * 60 * 60)

    return {"message": "Token refreshed"}
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Cookie
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.user_schema import Signup, Login, UserResponse
from auth.auth_dependency import check_current_user
from auth.auth_security import hash_password, verify_password, create_access_token, create_refresh_token
from slowapi import Limiter
from slowapi.util import get_remote_address
from datetime import datetime, timedelta, UTC
from auth.auth_security import hash_token

router = APIRouter(tags=['Auth'])
limiter = Limiter(key_func=get_remote_address)

@router.post("/sign-up", response_model=UserResponse)
def sign_up(data: Signup, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists.")

    new_user = models.User(username=data.username, password=hash_password(data.password), role=data.role)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, response: Response, data: Login, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == data.username).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=400, detail="invalid credentials")

    access_token = create_access_token({
        "userId": user.id,
        "username": user.username,
        "role": user.role
    })
    refresh_token = create_refresh_token({"userId": user.id})
    hashed = hash_token(refresh_token)

    new_token = models.RefreshToken(
        token_hash=hashed,
        user_id=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=7)
    )
    db.add(new_token)
    db.commit()

    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=True, samesite="lax", max_age=15 * 60)
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="lax", max_age=7 * 24 * 60 * 60)

    return {"message": "Login Successfully"}

@router.get("/profile")
def get_profile(current_user: dict = Depends(check_current_user)):
    return current_user

@router.post("/logout")
def logout(response: Response, refresh_token: str = Cookie(None), db: Session = Depends(get_db)):
    if refresh_token:
        hashed = hash_token(refresh_token)
        db_token = db.query(models.RefreshToken).filter(models.RefreshToken.token_hash == hashed).first()
        if db_token:
            db_token.is_revoked = True
            db.commit()

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}
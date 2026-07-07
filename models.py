from sqlalchemy import Column, Integer, String, Boolean, ForeignKey,DateTime
from database import Base
from datetime import datetime
from sqlalchemy.sql import func

class User(Base):
    __tablename__ = "users"

    id = Column(Integer,primary_key=True ,index=True)
    username = Column(String,index=True)
    password = Column(String)
    role = Column(String, default="user")


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer,primary_key=True ,index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String)
    timestamp = Column(DateTime, server_default=func.now())
    is_read = Column(Boolean, default=False)

# models.py mein add karo
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    token_hash = Column(String, unique=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    expires_at = Column(DateTime)
    is_revoked = Column(Boolean, default=False)
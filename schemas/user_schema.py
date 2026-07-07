from enum import Enum
from pydantic import BaseModel, field_validator



class Role(str, Enum):
    admin = "admin"
    user = "user"

class Signup(BaseModel):
    username: str
    password: str
    role: Role
    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.isalnum():
            raise ValueError("Username must be alphanumeric (no spaces or special characters)")
        return v
    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("password must bhi at least 8 characters long.")
        if not any(char.isdigit() for char in v):
            raise ValueError("password must contain atleast 1 digit.")
        if not any(char.isupper() for char in v):
            raise ValueError("password must contain atleast 1 capital letter.")
        return v

class Login(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True
from fastapi import Depends, HTTPException, Cookie
from auth.auth_security import decode_access_token

def check_current_user(access_token: str = Cookie(None)) -> str:
    if access_token is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(access_token)
    if not payload:
       raise HTTPException(status_code=400, detail="invalid token")
    return payload

class RoleCheck:
    def __init__(self, allowed_roles: list[str]):
        self.allowed_roles = allowed_roles
    def __call__(self, current_user: dict = Depends(check_current_user)):
        if current_user['role'] not in self.allowed_roles:
            raise HTTPException(status_code=403, detail="Not allowed")
        return current_user

admin_obj = RoleCheck(["admin"])
user_obj = RoleCheck(["user"])
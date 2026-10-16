from datetime import timedelta
import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request

from .config import get_settings
from .database import get_db, now, oid

COOKIE_NAME = "skysnr_token"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except Exception:
        return False


def create_token(user_id: str, role: str) -> str:
    s = get_settings()
    if not s.jwt_secret:
        raise HTTPException(status_code=500, detail="Server is not configured")
    exp = now() + timedelta(minutes=s.access_token_minutes)
    return jwt.encode({"sub": user_id, "role": role, "exp": exp}, s.jwt_secret, algorithm="HS256")


def get_current_user(request: Request, db=Depends(get_db)) -> dict:
    s = get_settings()
    token = request.cookies.get(COOKIE_NAME)
    auth = request.headers.get("authorization", "")
    if not token and auth.lower().startswith("bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, s.jwt_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please sign in again.")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session")
    user = db.users.find_one({"_id": oid(payload["sub"])})
    # Role and status are always re-read from the database, never trusted from the token.
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    if user.get("approval_status") != "approved" or not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Account is not approved or is inactive")
    return user


def require_roles(*roles: str):
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="You do not have permission for this action")
        return user
    return checker


require_admin = require_roles("admin")
require_manager = require_roles("rescue_manager")
require_member = require_roles("rescue_member")

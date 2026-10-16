from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field, model_validator

from ..config import get_settings
from ..database import get_db, now, ser
from ..dependencies import (COOKIE_NAME, create_token, get_current_user, hash_password, verify_password)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    confirm_password: str
    # Admin is deliberately not allowed here.
    role: Literal["rescue_manager", "rescue_member"]

    @model_validator(mode="after")
    def passwords_match(self):
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", status_code=201)
def register(body: RegisterIn, db=Depends(get_db)):
    email = body.email.lower()
    if db.users.find_one({"email": email}):
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    db.users.insert_one({"full_name": body.full_name.strip(), "email": email,
                         "password_hash": hash_password(body.password), "role": body.role,
                         "approval_status": "pending", "is_active": False, "created_at": now()})
    return {"message": "Registration received. An admin must approve your account before you can sign in."}


@router.post("/login")
def login(body: LoginIn, response: Response, db=Depends(get_db)):
    user = db.users.find_one({"email": body.email.lower()})
    if not user or not verify_password(body.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    status = user.get("approval_status")
    if status == "pending":
        raise HTTPException(status_code=403, detail="Your account is awaiting admin approval")
    if status == "rejected":
        raise HTTPException(status_code=403, detail="Your registration was not approved")
    if not user.get("is_active", False):
        raise HTTPException(status_code=403, detail="Your account is inactive. Contact an admin.")
    s = get_settings()
    token = create_token(str(user["_id"]), user["role"])
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", secure=s.cookie_secure,
                        max_age=s.access_token_minutes * 60, path="/")
    return {"user": ser(user), "access_token": token, "token_type": "bearer"}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return ser(user)


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Signed out"}

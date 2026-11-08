from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select

from .. import audit
from ..models import User
from ..schemas import Register, StaffCreate, Token, UserOut
from ..security import DB, AdminUser, CurrentUser, ROLES, create_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
def register(body: Register, db: DB):
    """Candidates create their own account. HR accounts are created by an admin."""
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=body.email, full_name=body.full_name, password_hash=hash_password(body.password),
                role="candidate")
    db.add(user)
    db.commit()
    return user


@router.post("/login", response_model=Token)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DB):
    user = db.scalar(select(User).where(User.email == form.username.lower()))
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    return Token(access_token=create_token(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.post("/staff", response_model=UserOut, status_code=201)
def create_staff(body: StaffCreate, admin: AdminUser, db: DB):
    if body.role not in ROLES - {"candidate"}:
        raise HTTPException(422, "Staff role must be hr or admin")
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(email=body.email, full_name=body.full_name, password_hash=hash_password(body.password),
                role=body.role)
    db.add(user)
    db.flush()
    audit.log(db, admin.id, "create_staff", "user", user.id, role=body.role)
    db.commit()
    return user

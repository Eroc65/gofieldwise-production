from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..core.auth import hash_password, verify_password
from ..core.db import get_db
from ..core.jwt import create_access_token, decode_access_token
from ..models.core import Organization, User
from ..schemas.organization import OrganizationOut
from ..schemas.user import UserCreate, UserOut

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    payload = decode_access_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

@router.post("/signup", response_model=UserOut)
def signup(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    if not user.organization_name:
        raise HTTPException(status_code=400, detail="Organization name is required")

    organization = (
        db.query(Organization)
        .filter(Organization.name == user.organization_name)
        .first()
    )
    if organization is None:
        organization = Organization(name=user.organization_name)
        db.add(organization)
        db.flush()

    db_user = User(
        email=user.email,
        hashed_password=hash_password(user.password),
        organization_id=organization.id,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token = create_access_token({"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user

@router.get("/org", response_model=OrganizationOut)
def current_org(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    organization = (
        db.query(Organization)
        .filter(Organization.id == current_user.organization_id)
        .first()
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization
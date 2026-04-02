from fastapi import APIRouter, Depends
from .auth import get_current_user

router = APIRouter()

@router.get("/protected")
def protected_route(user=Depends(get_current_user)):
    return {"message": f"Hello, {user.email}. This is a protected route."}
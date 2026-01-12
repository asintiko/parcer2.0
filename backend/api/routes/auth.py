"""
API Routes for Telegram Authentication
Provides QR code login and JWT token management
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
from services.auth_service import (
    generate_qr_login,
    check_qr_login_status,
    cleanup_session,
    logout_user,
    verify_user_token
)

router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Request/Response Models
class QRLoginResponse(BaseModel):
    session_id: str
    qr_code: str
    url: str
    expires_in: int


class LoginStatusResponse(BaseModel):
    status: str
    message: Optional[str] = None
    token: Optional[str] = None
    user: Optional[dict] = None


class LogoutResponse(BaseModel):
    success: bool
    message: str


class UserInfoResponse(BaseModel):
    user_id: int
    phone: str
    exp: int


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Dependency to get current authenticated user"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")
    user = await verify_user_token(token)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return user


@router.post("/qr/generate", response_model=QRLoginResponse)
async def generate_qr():
    """
    Generate QR code for Telegram login
    Returns QR code image and session ID
    """
    try:
        session_id = str(uuid.uuid4())
        result = await generate_qr_login(session_id)
        return QRLoginResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/qr/status/{session_id}", response_model=LoginStatusResponse)
async def check_login_status(session_id: str):
    """
    Check if QR code has been scanned and user authenticated
    Poll this endpoint to detect successful login
    """
    try:
        result = await check_qr_login_status(session_id)
        return LoginStatusResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/qr/cleanup/{session_id}")
async def cleanup_qr_session(session_id: str):
    """Clean up QR authentication session"""
    try:
        await cleanup_session(session_id)
        return {"success": True, "message": "Session cleaned up"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/logout", response_model=LogoutResponse)
async def logout(authorization: Optional[str] = Header(None)):
    """Logout current user and invalidate token"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.replace("Bearer ", "")

    try:
        success = await logout_user(token)
        if success:
            return LogoutResponse(success=True, message="Logged out successfully")
        else:
            return LogoutResponse(success=False, message="Failed to logout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/me", response_model=UserInfoResponse)
async def get_current_user_info(user: dict = Depends(get_current_user)):
    """Get current authenticated user information"""
    return UserInfoResponse(
        user_id=user["user_id"],
        phone=user["phone"],
        exp=user["exp"]
    )


@router.get("/verify")
async def verify_token(user: dict = Depends(get_current_user)):
    """Verify if token is valid"""
    return {"valid": True, "user_id": user["user_id"]}

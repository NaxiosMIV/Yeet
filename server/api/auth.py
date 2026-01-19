from fastapi import APIRouter, HTTPException, Body, Response, Request
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv
from core.providers.google import verify_google_token
from core.providers.guest import create_guest_user
from core.auth_utils import create_access_token, decode_access_token
import os
from core.database import get_or_create_user, get_user_by_uuid
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

def set_auth_cookie(response: Response, user_id: str):
    logger.info(f"Setting auth cookie for user {user_id}")
    token = create_access_token({"user_uuid": str(user_id)})
    response.set_cookie(
        key="session_id",
        value=token,
        max_age=3600,
        expires=3600,
        secure=False,
        httponly=True,
        samesite="lax"
    )

def delete_auth_cookie(response: Response):
    logger.info("Deleting auth cookie")
    response.delete_cookie("session_id")

@router.get("/config")
async def get_config():
    load_dotenv()
    return {
        "google_client_id": os.getenv("GOOGLE_CLIENT_ID")
    }

@router.get("/me")
async def get_me(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="세션이 없습니다.")
    
    payload = decode_access_token(session_id)
    if not isinstance(payload, dict):
        raise HTTPException(status_code=401, detail="유효하지 않은 세션입니다.")
    
    user_uuid = payload.get("user_uuid")
    user = await get_user_by_uuid(user_uuid)
    if not user:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    
    return {"status": "success", "user": user}

@router.post("/login/{provider}")
async def login(provider: str, response: Response, request: Request, token: str = Body(None, embed=True)):
    if request.cookies.get("session_id"):
        return await get_me(request)

    user_info = None
    if provider == "google":
        user_info = await verify_google_token(token)
    elif provider == "guest":
        user_info = create_guest_user(token)
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 로그인 방식입니다.")

    if user_info is None or user_info["status"] != "success":
        raise HTTPException(status_code=401, detail="인증 정보가 없습니다.")
    
    user_uuid = await get_or_create_user(user_info["user"])
    set_auth_cookie(response, user_uuid)
    
    return {"status": "success", "user": user_info["user"]}

@router.post("/logout")
async def logout(response: Response):
    delete_auth_cookie(response)
    return {"status": "success"}

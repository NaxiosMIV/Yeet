from fastapi import APIRouter, HTTPException, Body, Response
from google.oauth2 import id_token
from google.auth.transport import requests
from dotenv import load_dotenv
from core.providers.google import verify_google_token
from core.providers.kakao import verify_kakao_token
from core.providers.guest import create_guest_user
from core.auth_utils import create_access_token
import os
from core.database import get_or_create_user

load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")

router = APIRouter(prefix="/auth", tags=["auth"])

def set_auth_cookie(response: Response, user_id: str):
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
    response.delete_cookie("session_id")

@router.get("/config")
async def get_config():
    return {
        "google_client_id": GOOGLE_CLIENT_ID
    }

@router.post("/login/{provider}")
async def login(provider: str, response: Response, token: str = Body(..., embed=True)):
    user_info = None
    if provider == "google":
        user_info = await verify_google_token(token)
    elif provider == "kakao":
        user_info = await verify_kakao_token(token)
    elif provider == "guest":
        user_info = create_guest_user(token)
    else:
        raise HTTPException(status_code=400, detail="지원하지 않는 로그인 방식입니다.")

    if user_info is None or user_info["status"] != "success":
        raise HTTPException(status_code=401, detail="인증 정보가 없습니다.")

    set_auth_cookie(response, await get_or_create_user(user_info["user"]))
    
    return {"status": "success", "user": user_info["user"]}
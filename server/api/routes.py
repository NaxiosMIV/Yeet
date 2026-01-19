from fastapi import APIRouter
from fastapi.responses import FileResponse
from core.words import get_word_in_cache
from .auth import router as auth_router
from core.database import get_user_by_uuid
from .rooms import router as rooms_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(rooms_router)

@router.get("/loginTest")
async def loginTest():
    return FileResponse("../client/loginTest.html")

@router.get("/chatTest")
async def chat_test():
    return FileResponse("../client/chatTest.html")

@router.get("/")
async def index():
    return FileResponse("../client/index.html")

@router.get("/get_user/{user_uuid}")
async def get_user(user_uuid: str):
    return get_user_by_uuid(user_uuid)

@router.get("/get_word/{word}")
async def get_word(word: str):
    return get_word_in_cache(word)


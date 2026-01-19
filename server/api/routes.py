from fastapi import APIRouter
from fastapi.responses import FileResponse
from core.words import get_word_in_cache
from .auth import router as auth_router
from core.database import get_user_by_uuid
from core.logging_config import get_logger

logger = get_logger(__name__)
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

@router.get("/next")
async def next_ui():
    # Redirect to Next.js dev server during development
    # In production, this would serve the built static files
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="http://localhost:3000")

@router.get("/get_user/{user_uuid}")
async def get_user(user_uuid: str):
    return get_user_by_uuid(user_uuid)

@router.get("/get_word/{word}")
async def get_word(word: str):
    return get_word_in_cache(word)


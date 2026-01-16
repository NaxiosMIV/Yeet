from fastapi import APIRouter
from fastapi.responses import FileResponse
from core.words import check_word_in_cache

router = APIRouter()

@router.get("/")
async def index():
    return FileResponse("../client/index.html")

@router.get("/get_word/{word}")
async def get_word(word: str):
    return get_word_in_cache(word)


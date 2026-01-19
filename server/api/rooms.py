from fastapi import APIRouter, Query
from core.game import room_manager

router = APIRouter(prefix="/rooms", tags=["rooms"])

@router.post("/join")
async def join_room(room_code: str = Query(...)):
    """
    방 코드를 받아 방을 생성하거나 기존의 방을 반환합니다.
    """
    room = room_manager.get_or_create_room(room_code)
    return {
        "status": "success",
        "room_state": room.get_state()
    }

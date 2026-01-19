from fastapi import WebSocket, WebSocketDisconnect
from core.game import room_manager, Player
from core.auth_utils import decode_access_token
import uuid
import asyncio
from core.logging_config import get_logger

logger = get_logger(__name__)

async def handle_websocket(ws: WebSocket):
    room_code = ws.query_params.get("room")
    name = ws.query_params.get("name") or "Guest"
    
    if not room_code:
        await ws.close()
        return

    await ws.accept()

    # Auth logic
    session_id = ws.cookies.get("session_id")
    user_uuid = None
    if session_id:
        payload = decode_access_token(session_id)
        if isinstance(payload, dict):
            user_uuid = payload.get("user_uuid")
    
    if not user_uuid:
        user_uuid = str(uuid.uuid4())

    # Get room and add player
    room = room_manager.get_or_create_room(room_code)
    player = Player(user_uuid, name, ws)
    room.add_player(player)

    # Initial Init & Broadcast
    await ws.send_json({"type": "INIT", "playerId": user_uuid, "state": room.get_state()})
    await room.broadcast({"type": "UPDATE", "state": room.get_state()})

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "PLACE":
                x, y, letter = data["x"], data["y"], data["letter"]
                success, error_message = await room.handle_place_tile(x, y, letter, user_uuid)
                
                if not success:
                    await ws.send_json({"type": "ERROR", "message": error_message})
            
            elif data["type"] == "CHAT":
                message = data.get("message", "")
                if message:
                    await room.broadcast({
                        "type": "CHAT",
                        "sender": name,
                        "senderId": user_uuid,
                        "message": message
                    })

            elif data["type"] == "END_GAME":
                game_id = await room.handle_end_game()
                await room.broadcast({"type": "GAME_OVER", "game_id": game_id, "state": room.get_state()})

    except WebSocketDisconnect:
        room.remove_player(user_uuid)
        await room.broadcast({"type": "UPDATE", "state": room.get_state()})
        # Optional: Auto-clean empty rooms
        if not room.players:
            room_manager.remove_room(room_code)
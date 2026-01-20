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
    user_color = ws.query_params.get("color") or "#6366F1"
    
    if not room_code:
        await ws.close()
        return

    await ws.accept()

    # Auth logic
    session_id = ws.cookies.get("session_id")
    logger.debug(f"WebSocket handshake: session_id={session_id}")
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
    player.color = user_color
    room.add_player(player)

    # Init hand
    room.draw_tiles_for_player(user_uuid, 7)

    # Initial Init & Broadcast
    await ws.send_json({"type": "INIT", "playerId": user_uuid, "state": room.get_state()})
    await room.broadcast({"type": "UPDATE", "state": room.get_state()})

    try:
        while True:
            data = await ws.receive_json()
            
            # Recalculate host status for every command to handle host migration
            player_ids = list(room.players.keys())
            is_host = player_ids[0] == user_uuid if player_ids else False
            
            if data["type"] == "START_GAME":
                if is_host:
                    countdown_seconds = 3
                    await room.broadcast({
                        "type": "GAME_START_COUNTDOWN", 
                        "seconds": countdown_seconds
                    })
                    await asyncio.sleep(countdown_seconds + 0.5)
                    room.start_match()
                    await room.broadcast({"type": "GAME_STARTED"})
                    room.start_global_timer(300)
                    await room.broadcast_state()
                else:
                    await ws.send_json({"type": "ERROR", "message": "Only the host can start."})

            elif data["type"] == "PLACE":
                x, y, letter = data["x"], data["y"], data["letter"]
                color = data.get("color", "#4f46e5")
                hand_index = data.get("hand_index")
                success, error_message = await room.handle_place_tile(x, y, letter, user_uuid, color, hand_index)
                
                if not success:
                    await ws.send_json({"type": "ERROR", "message": error_message})

            elif data["type"] == "UPDATE_SETTINGS":
                if is_host:
                    room.update_settings(data.get("settings", {}))
                    await room.broadcast_state()
                else:
                    await ws.send_json({"type": "ERROR", "message": "Only the host can update settings."})
            
            elif data["type"] == "DRAW":
                count = data.get("count", 1)
                new_tiles = room.draw_tiles_for_player(user_uuid, count)
                await ws.send_json({"type": "DRAWN_TILES", "tiles": new_tiles})
                # Broadcast updated player state (hand changed)
                await room.broadcast({"type": "UPDATE", "state": room.get_state()})

            elif data["type"] == "START_TIMER":
                duration = data.get("duration", 60)
                room.start_timer(duration)
                await room.broadcast({"type": "UPDATE", "state": room.get_state()})
            
            elif data["type"] == "CHAT":
                message = data.get("message", "")
                if message:
                    await room.broadcast({
                        "type": "CHAT",
                        "sender": name,
                        "senderId": user_uuid,
                        "message": message
                    })
            elif data["type"] == "REROLL_HAND":
                room.reroll_hand(user_uuid)
                await room.broadcast_state()
                
            elif data["type"] == "DESTROY_TILE":
                hand_index = data.get("hand_index")
                if hand_index is not None:
                    room.destroy_tile(user_uuid, hand_index)
                    # Always broadcast state so the rack updates visually
                    await room.broadcast_state()

            elif data["type"] == "END_GAME":
                game_id = await room.handle_end_game()
                await room.broadcast({"type": "GAME_OVER", "game_id": game_id, "state": room.get_state()})

    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected: {user_uuid}")
        room.remove_player(user_uuid)
        # If the host disconnected, the next broadcast will show a new host
        await room.broadcast_state()
        if not room.players:
            room_manager.remove_room(room_code)
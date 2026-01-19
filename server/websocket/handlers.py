from fastapi import WebSocket, WebSocketDisconnect
from core.game import room_manager, Player
from core.words import get_word_in_cache
from core.auth_utils import decode_access_token
from core.database import save_game_result
import uuid
import asyncio

def find_words_at(board, x, y, new_letter):
    """지정된 위치에 새로운 글자를 놓았을 때 형성되는 가로/세로 단어들을 찾음"""
    board_dict = {(t['x'], t['y']): t['letter'] for t in board}
    board_dict[(x, y)] = new_letter
    
    def get_word(dx, dy):
        curr_x, curr_y = x, y
        while (curr_x - dx, curr_y - dy) in board_dict:
            curr_x -= dx
            curr_y -= dy
        
        word = ""
        while (curr_x, curr_y) in board_dict:
            word += board_dict[(curr_x, curr_y)]
            curr_x += dx
            curr_y += dy
        return word

    horizontal = get_word(1, 0)
    vertical = get_word(0, 1)
    
    words = []
    if len(horizontal) > 1: words.append(horizontal)
    if len(vertical) > 1: words.append(vertical)
    if not words: words.append(new_letter)
    return words

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
                
                # Validation logic
                formed_words = find_words_at(room.board, x, y, letter)
                all_valid = True
                total_points = 0
                
                for w in formed_words:
                    result = get_word_in_cache(w)
                    if result["is_valid"]:
                        total_points += result["score"]
                    elif len(w) > 1:
                        all_valid = False
                        break
                
                if all_valid:
                    if room.place_tile(x, y, letter, user_uuid, 10 + total_points):
                        await room.broadcast({"type": "UPDATE", "state": room.get_state()})
                else:
                    await ws.send_json({"type": "ERROR", "message": f"Invalid words: {formed_words}"})
            
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
                # Convert players dict for saving
                players_data = {pid: p.to_dict() for pid, p in room.players.items()}
                game_id = await save_game_result(room_code, players_data)
                await room.broadcast({"type": "GAME_OVER", "game_id": game_id, "state": room.get_state()})

    except WebSocketDisconnect:
        room.remove_player(user_uuid)
        await room.broadcast({"type": "UPDATE", "state": room.get_state()})
        # Optional: Auto-clean empty rooms
        if not room.players:
            room_manager.remove_room(room_code)
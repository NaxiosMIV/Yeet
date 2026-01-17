from fastapi import WebSocket, WebSocketDisconnect
from core.game import rooms, connections, create_room, broadcast
from core.words import get_word_in_cache
from core.auth_utils import decode_access_token
from core.database import save_game_result
import uuid

def find_words_at(board, x, y, new_letter):
    """지정된 위치에 새로운 글자를 놓았을 때 형성되는 가로/세로 단어들을 찾음"""
    
    # 임시 보드 생성 (새 글자 포함)
    temp_board = board + [{'x': x, 'y': y, 'letter': new_letter}]
    board_dict = {(t['x'], t['y']): t['letter'] for t in temp_board}
    
    def get_word(dx, dy):
        # 시작점 찾기
        curr_x, curr_y = x, y
        while (curr_x - dx, curr_y - dy) in board_dict:
            curr_x -= dx
            curr_y -= dy
        
        # 단어 읽기
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
    
    # 만약 주변에 아무것도 없어서 단어가 형성되지 않는다면, 자기 자신이라도 단어로 취급 (검증용)
    if not words:
        words.append(new_letter)
        
    return words

async def handle_websocket(ws: WebSocket):
    room = ws.query_params.get("room")
    name = ws.query_params.get("name") or "Guest"
    
    if not room:
        await ws.close()
        return

    await ws.accept()

    # 쿠키에서 유저 UUID 가져오기
    session_id = ws.cookies.get("session_id")
    user_uuid = None
    if session_id:
        payload = decode_access_token(session_id)
        if isinstance(payload, dict):
            user_uuid = payload.get("user_uuid")
    
    # 세션이 없으면 (테스트용 등) 랜덤 생성
    if not user_uuid:
        user_uuid = str(uuid.uuid4())

    if room not in rooms:
        rooms[room] = create_room()

    game = rooms[room]
    player_id = user_uuid # player_id로 user_uuid 사용
    
    game["players"][player_id] = {
        "name": name,
        "score": 0
    }
    
    connections[room][player_id] = ws
    await ws.send_json({"type": "INIT", "playerId": player_id, "state": game})
    await broadcast(room, {"type": "UPDATE", "state": game})

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "PLACE":
                x, y, letter = data["x"], data["y"], data["letter"]
                exists = any(t for t in game["board"] if t['x'] == x and t['y'] == y)
                
                if not exists:
                    # 1. 형성되는 단어들 추출
                    formed_words = find_words_at(game["board"], x, y, letter)
                    
                    # 2. 모든 단어가 유효한지 검사
                    all_valid = True
                    total_points = 0
                    
                    for w in formed_words:
                        result = get_word_in_cache(w)
                        if result["is_valid"]:
                            total_points += result["score"]
                        else:
                            # 1글자짜리는 단어가 아니므로 그냥 통과시키되 점수는 없음 (게임을 이어가기 위함)
                            if len(w) > 1:
                                all_valid = False
                                break
                    
                    if all_valid:
                        game["board"].append({'x': x, 'y': y, 'letter': letter})
                        # 최소 10점 보장 + 단어 점수
                        game["players"][player_id]["score"] += (10 + total_points)
                        await broadcast(room, {"type": "UPDATE", "state": game})
                    else:
                        await ws.send_json({"type": "ERROR", "message": f"Invalid words formed: {formed_words}"})
            
            elif data["type"] == "END_GAME":
                # 게임 종료 및 DB 저장
                game_id = await save_game_result(room, game["players"])
                await broadcast(room, {"type": "GAME_OVER", "game_id": game_id, "state": game})
                # 방 정리 (옵션)
                # rooms.pop(room, None)

            elif data["type"] == "CHAT":
                message = data.get("message", "")
                if message:
                    await broadcast(room, {
                        "type": "CHAT",
                        "sender": name,
                        "senderId": player_id,
                        "message": message
                    })

    except WebSocketDisconnect:
        game["players"].pop(player_id, None)
        connections[room].pop(player_id, None)
        await broadcast(room, {"type": "UPDATE", "state": game})
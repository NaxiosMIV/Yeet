from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from collections import defaultdict
import os
import asyncpg

app = FastAPI()
BOARD_SIZE = 5
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db/yeet_db")

# Serve client files
app.mount("/static", StaticFiles(directory="../client"), name="static")

@app.get("/")
async def index():
    return FileResponse("../client/index.html")

# room_code -> game state
rooms = {}
# room_code -> {player_id: websocket}
connections = defaultdict(dict)
word_cache = {}

def create_room():
    return {
        "board": [
            {'x':1, 'y':1, 'letter': 'S'},
            {'x':2, 'y':1, 'letter': 'H'},
            {'x':3, 'y':1, 'letter': 'I'},
            {'x':4, 'y':1, 'letter': 'T'}
        ],
        "current_player": 0,
        "players": []
    }

async def broadcast(room, message):
    for ws in connections[room].values():
        await ws.send_json(message)

@app.on_event("startup")
async def load_words_to_memory():
    global word_cache
    print("DB에서 단어 데이터를 메모리로 로드하는 중...")
    
    try:
        # DB 연결
        conn = await asyncpg.connect(DATABASE_URL)
        
        # 전체 데이터 조회
        rows = await conn.fetch("SELECT word, length, score FROM dictionary")
        
        # 메모리(dict)에 저장 - O(1) 속도로 접근 가능
        word_cache = {row['word']: (row['length'], row['score']) for row in rows}
        
        await conn.close()
        print(f"로드 완료! 총 {len(word_cache)}개의 단어가 메모리에 준비되었습니다.")
        
    except Exception as e:
        print(f"데이터 로드 중 오류 발생: {e}")

@app.get("/check/{word}")
async def check_word(word: str):
    upper_word = word.upper()
    # 메모리에서 즉시 확인 (DB 조회 안 함)
    if upper_word in word_cache:
        length, score = word_cache[upper_word]
        return {
            "is_valid": True,
            "word": upper_word,
            "length": length,
            "score": score
        }
    
    return {"is_valid": False, "word": upper_word}

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    room = ws.query_params.get("room")
    if not room:
        await ws.close()
        return

    await ws.accept()

    if room not in rooms:
        rooms[room] = create_room()

    game = rooms[room]

    player_id = len(game["players"])
    game["players"].append(player_id)
    connections[room][player_id] = ws

    await ws.send_json({
        "type": "INIT",
        "playerId": player_id,
        "state": game
    })

    try:
        while True:
            data = await ws.receive_json()

            # In main.py, inside the PLACE logic:
            if data["type"] == "PLACE":
                x, y, letter = data["x"], data["y"], data["letter"]

                # Check if a tile already exists at these coordinates
                exists = any(t for t in game["board"] if t['x'] == x and t['y'] == y)
                
                if not exists:
                    game["board"].append({'x': x, 'y': y, 'letter': letter})
                    # Broadcast the update
                    await broadcast(room, {"type": "UPDATE", "state": game})

    except WebSocketDisconnect:
        connections[room].pop(player_id, None)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from collections import defaultdict

app = FastAPI()
BOARD_SIZE = 5

# Serve client files
app.mount("/static", StaticFiles(directory="../client"), name="static")

@app.get("/")
async def index():
    return FileResponse("../client/index.html")

# room_code -> game state
rooms = {}

# room_code -> {player_id: websocket}
connections = defaultdict(dict)

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
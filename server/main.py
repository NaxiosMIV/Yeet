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
        "board": [[None for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)],
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

            if data["type"] == "PLACE":
                if player_id != game["current_player"]:
                    continue

                x, y, letter = data["x"], data["y"], data["letter"]

                if game["board"][y][x] is None:
                    game["board"][y][x] = letter
                    game["current_player"] = (
                        game["current_player"] + 1
                    ) % len(game["players"])

                    await broadcast(room, {
                        "type": "UPDATE",
                        "state": game
                    })

    except WebSocketDisconnect:
        connections[room].pop(player_id, None)

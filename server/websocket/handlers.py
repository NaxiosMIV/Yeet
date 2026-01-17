from fastapi import WebSocket, WebSocketDisconnect
from core.game import rooms, connections, create_room, broadcast
import uuid

async def handle_websocket(ws: WebSocket):
    room = ws.query_params.get("room")
    name = ws.query_params.get("name") or "Guest" # Capture name from query
    
    if not room:
        await ws.close()
        return

    await ws.accept()

    if room not in rooms:
        rooms[room] = create_room() # Ensure create_room initializes "players": {}

    game = rooms[room]

    # Use a unique ID (could be simple increment or string)
    player_id = str(uuid.uuid4())
    
    # Store player data
    game["players"][player_id] = {
        "name": name,
        "score": 0
    }
    
    connections[room][player_id] = ws
    await ws.send_json({"type": "INIT", "playerId": player_id, "state": game})
    # Broadcast that a new player joined (updates everyone's leaderboard)
    await broadcast(room, {"type": "UPDATE", "state": game})

    try:
        while True:
            data = await ws.receive_json()

            if data["type"] == "PLACE":
                x, y, letter = data["x"], data["y"], data["letter"]
                exists = any(t for t in game["board"] if t['x'] == x and t['y'] == y)
                
                if not exists:
                    game["board"].append({'x': x, 'y': y, 'letter': letter})
                    
                    # Award points!
                    game["players"][player_id]["score"] += 10
                    
                    await broadcast(room, {"type": "UPDATE", "state": game})

    except WebSocketDisconnect:
        game["players"].pop(player_id, None)
        connections[room].pop(player_id, None)
        await broadcast(room, {"type": "UPDATE", "state": game})
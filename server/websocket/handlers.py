from fastapi import WebSocket, WebSocketDisconnect
from core.game import rooms, connections, create_room, broadcast

async def handle_websocket(ws: WebSocket):
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
                x, y, letter = data["x"], data["y"], data["letter"]

                # Check if a tile already exists at these coordinates
                exists = any(t for t in game["board"] if t['x'] == x and t['y'] == y)
                
                if not exists:
                    game["board"].append({'x': x, 'y': y, 'letter': letter})
                    # Broadcast the update
                    await broadcast(room, {"type": "UPDATE", "state": game})

    except WebSocketDisconnect:
        connections[room].pop(player_id, None)

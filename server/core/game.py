from collections import defaultdict

# room_code -> game state
rooms = {}

# room_code -> {player_id: websocket}
connections = defaultdict(dict)

def create_room():
    return {
        "board": [
            {'x': 1, 'y': 1, 'letter': 'S'},
            {'x': 2, 'y': 1, 'letter': 'H'},
            {'x': 3, 'y': 1, 'letter': 'I'},
            {'x': 4, 'y': 1, 'letter': 'T'}
        ],
        "current_player": 0,
        "players": []
    }

async def broadcast(room, message):
    for ws in connections[room].values():
        await ws.send_json(message)

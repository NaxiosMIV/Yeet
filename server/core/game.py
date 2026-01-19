from collections import defaultdict
from typing import Dict, List, Optional
import time
import asyncio

class Player:
    def __init__(self, player_id: str, name: str, websocket):
        self.player_id = player_id
        self.name = name
        self.websocket = websocket
        self.score = 0
        self.color = "#6366F1" # Default color

    def to_dict(self):
        return {
            "name": self.name,
            "score": self.score,
            "color": self.color
        }

class GameRoom:
    def __init__(self, room_code: str):
        self.room_code = room_code
        self.board: List[Dict] = []
        self.players: Dict[str, Player] = {}
        self.status = "PLAYING" # WAITING, PLAYING, FINISHED
        self.created_at = time.time()

    def add_player(self, player: Player):
        self.players[player.player_id] = player

    def remove_player(self, player_id: str):
        if player_id in self.players:
            del self.players[player_id]

    async def broadcast(self, message: dict):
        # 플레이어들에게 메시지 비동기 전송
        tasks = [
            p.websocket.send_json(message) 
            for p in self.players.values()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_state(self):
        return {
            "board": self.board,
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "status": self.status,
            "room_code": self.room_code
        }

    def place_tile(self, x: int, y: int, letter: str, player_id: str, points: int):
        # 타일 존재 여부 체크
        if any(t for t in self.board if t['x'] == x and t['y'] == y):
            return False
        
        self.board.append({'x': x, 'y': y, 'letter': letter})
        if player_id in self.players:
            self.players[player_id].score += points
        return True

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}

    def get_or_create_room(self, room_code: str) -> GameRoom:
        if room_code not in self.rooms:
            self.rooms[room_code] = GameRoom(room_code)
        return self.rooms[room_code]

    def remove_room(self, room_code: str):
        if room_code in self.rooms:
            del self.rooms[room_code]

# Global instance
room_manager = RoomManager()

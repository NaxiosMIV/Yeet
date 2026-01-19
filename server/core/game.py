from collections import defaultdict
from typing import Dict, List, Optional
import time
import asyncio
from core.words import get_word_in_cache
from core.database import save_game_result

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

    def find_words_at(self, x, y, new_letter):
        """지정된 위치에 새로운 글자를 놓았을 때 형성되는 가로/세로 단어들을 찾음"""
        board_dict = {(t['x'], t['y']): t['letter'] for t in self.board}
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

    async def handle_place_tile(self, x: int, y: int, letter: str, player_id: str):
        """타일 배치를 검증하고 결과를 반환합니다."""
        formed_words = self.find_words_at(x, y, letter)
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
            if self.place_tile(x, y, letter, player_id, 10 + total_points):
                return True, None
            return False, "Tile already exists at this position"
        return False, f"Invalid words: {formed_words}"

    async def handle_end_game(self):
        """게임을 종료하고 결과를 저장합니다."""
        players_data = {pid: p.to_dict() for pid, p in self.players.items()}
        game_id = await save_game_result(self.room_code, players_data)
        self.status = "FINISHED"
        return game_id

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

room_manager = RoomManager()
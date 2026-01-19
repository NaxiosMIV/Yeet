from collections import defaultdict
from typing import Dict, List, Optional
import time
import asyncio
from core.words import get_word_in_cache, get_random_word
from core.database import save_game_result
from core.logging_config import get_logger

logger = get_logger(__name__)

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
        self.pending_tiles: List[Dict] = []
        self.players: Dict[str, Player] = {}
        self.status = "PLAYING" # WAITING, PLAYING, FINISHED
        self.created_at = time.time()
        self.timer_task: Optional[asyncio.Task] = None
        
        # 초기 단어 생성
        self._initialize_starting_word()

    def _initialize_starting_word(self):
        word = get_random_word(6)
        if word:
            # 중앙에 배치 (가로)
            start_x = -(len(word) // 2)
            for i, letter in enumerate(word):
                self.board.append({'x': start_x + i, 'y': 0, 'letter': letter})
            logger.info(f"Initialized room {self.room_code} with word: {word}")

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
            "pending_tiles": self.pending_tiles,
            "players": {pid: p.to_dict() for pid, p in self.players.items()},
            "status": self.status,
            "room_code": self.room_code
        }

    def place_tile(self, x: int, y: int, letter: str, player_id: str, points: int):
        # 타일 존재 여부 체크 (보드 및 대기열)
        if any(t for t in self.board if t['x'] == x and t['y'] == y):
            return False
        
        self.board.append({'x': x, 'y': y, 'letter': letter})
        if player_id in self.players:
            self.players[player_id].score += points
        return True

    def _get_combined_board_dict(self):
        board_dict = {(t['x'], t['y']): t['letter'] for t in self.board}
        for t in self.pending_tiles:
            board_dict[(t['x'], t['y'])] = t['letter']
        return board_dict

    def find_words_at(self, x, y, new_letter, board_dict=None):
        """지정된 위치에 새로운 글자를 놓았을 때 형성되는 가로/세로 단어들을 찾음"""
        if board_dict is None:
            board_dict = self._get_combined_board_dict()
        
        # 만약 new_letter가 이미 board_dict에 없다면 추가 (보통 handle_place_tile에서 미리 추가함)
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
        """타일을 대기열에 추가하고 5초 타이머를 시작/재설정합니다."""
        # 이미 같은 위치에 타일이 있는지 체크
        if any(t for t in self.board if t['x'] == x and t['y'] == y) or \
           any(t for t in self.pending_tiles if t['x'] == x and t['y'] == y):
            return False, "Tile already exists at this position"

        self.pending_tiles.append({'x': x, 'y': y, 'letter': letter, 'player_id': player_id})

        # 타이머 재설정
        if self.timer_task:
            self.timer_task.cancel()
        
        self.timer_task = asyncio.create_task(self._wait_and_finalize())
        
        # 대기 상태 브로드캐스트
        await self.broadcast({"type": "UPDATE", "state": self.get_state(), "timer": 5})
        return True, None

    async def _wait_and_finalize(self):
        try:
            await asyncio.sleep(5)
            await self.finalize_pending_tiles()
        except asyncio.CancelledError:
            pass

    async def finalize_pending_tiles(self):
        """대기 중인 모든 타일을 검증하고 영구 배치하거나 제거합니다."""
        if not self.pending_tiles:
            return

        board_dict = self._get_combined_board_dict()
        all_formed_words = set()
        
        # 모든 대기 타일에 의해 형성된 모든 단어 수집
        for t in self.pending_tiles:
            words = self.find_words_at(t['x'], t['y'], t['letter'], board_dict)
            for w in words:
                all_formed_words.add(w)

        # 단어 검증
        invalid_words = []
        valid_words_data = []
        total_score_map = defaultdict(int) # player_id -> points

        for word in all_formed_words:
            if len(word) <= 1:
                continue # 단일 글자는 무시하거나 별도 처리
            
            result = get_word_in_cache(word)
            if result["is_valid"]:
                valid_words_data.append(result)
            else:
                invalid_words.append(word)

        if not invalid_words and valid_words_data:
            # 모든 단어가 유효함 -> 영구 배치 및 점수 추가
            # Scrabble 규칙에 따라 점수 계산 로직이 복잡할 수 있으나, 여기서는 단순화
            # 각 타일별로 10점 + 형성된 유효 단어들의 점수 합산
            
            # 먼저 보드에 반영
            for t in self.pending_tiles:
                # 여기서 points는 각 플레이어에게 할당해야 함
                # 간단하게 하기 위해 타일 하나당 10점 + 해당 타일이 포함된 단어 점수... 
                # 여기서는 그냥 합산해서 n분의 1 하거나, 각 플레이어별 타일 개수로 할당
                player_id = t['player_id']
                self.place_tile(t['x'], t['y'], t['letter'], player_id, 10)
            
            # 단어 점수 분배 (단어를 만든 타일들의 주인들에게 분배하는 게 맞지만, 여기서는 전체 합산 후 기여도에 따라?)
            # 일단 단순하게 전체 합산 점수를 기여한 플레이어들에게 적절히 배분 (여기서는 생략하고 타일당 10점만 우선 적용하거나 로직 추가)
            total_word_score = sum(r['score'] for r in valid_words_data)
            # 기여한 플레이어들에게 보너스 점수 (대기 타일을 놓은 플레이어들)
            unique_players = {t['player_id'] for t in self.pending_tiles}
            bonus_per_player = total_word_score // len(unique_players) if unique_players else 0
            for pid in unique_players:
                if pid in self.players:
                    self.players[pid].score += bonus_per_player

            await self.broadcast({"type": "MODAL", "message": f"Words completed: {', '.join([r['word'] for r in valid_words_data])}"})
        else:
            # 유효하지 않은 단어가 있거나 단어가 형성되지 않음 -> 대기 타일 모두 제거
            reason = f"Invalid words: {', '.join(invalid_words)}" if invalid_words else "No valid words formed"
            await self.broadcast({"type": "ERROR", "message": reason})
        
        self.pending_tiles = []
        self.timer_task = None
        await self.broadcast({"type": "UPDATE", "state": self.get_state()})

    async def handle_end_game(self):
        """게임을 종료하고 결과를 저장합니다."""
        # 대기 중인 타일이 있다면 즉시 처리
        if self.pending_tiles:
            if self.timer_task:
                self.timer_task.cancel()
            await self.finalize_pending_tiles()

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
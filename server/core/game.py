from collections import defaultdict
from typing import Dict, List, Optional
import time
import asyncio
import uuid
from core.words import get_word_in_cache, get_random_word
from core.tiles import generate_weighted_tiles
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
        self.hand: List[str] = []
        logger.debug(f"Player created: {self.name} ({self.player_id})")

    def to_dict(self):
        return {
            "name": self.name,
            "score": self.score,
            "color": self.color,
            "hand": self.hand
        }

class GameRoom:
    def __init__(self, room_code):
        self.room_code = room_code
        self.players = {} 
        self.state = "LOBBY" 
        self.settings = {
            "mode": "classic",
            "max_players": 10
        }
        self.board = []
        self.pending_tiles = [] # Added missing init
        self.group_timers = {}  # Added missing init

    def _initialize_starting_word(self):
        word = get_random_word(6)
        if word:
            # 중앙에 배치 (가로)
            start_x = -(len(word) // 2)
            for i, letter in enumerate(word):
                self.board.append({'x': start_x + i, 'y': 0, 'letter': letter})
            logger.info(f"Initialized room {self.room_code} with word: {word}")

    def add_player(self, player: Player):
        logger.debug(f"Adding player {player.name} to room {self.room_code}")
        self.players[player.player_id] = player

    def remove_player(self, player_id: str):
        logger.debug(f"Removing player {player_id} from room {self.room_code}")
        if player_id in self.players:
            del self.players[player_id]

    def draw_tiles_for_player(self, player_id: str, count: int) -> List[str]:
        if player_id not in self.players:
            return []
        
        new_tiles = generate_weighted_tiles(count)
        self.players[player_id].hand.extend(new_tiles)
        logger.debug(f"Player {player_id} drew {count} tiles: {new_tiles}")
        return new_tiles

    async def broadcast(self, message: dict):
        logger.debug(f"Broadcasting message type {message.get('type')} to {len(self.players)} players in {self.room_code}")
        # 플레이어들에게 메시지 비동기 전송
        tasks = [
            p.websocket.send_json(message) 
            for p in self.players.values()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_state(self):
        await self.broadcast({"type": "UPDATE", "state": self.get_state()})

    def start_match(self):
        self.state = "INGAME"
        if not self.board:
            self._initialize_starting_word()
        
        # Ensure all players have 7 tiles at start
        for p_id in self.players:
            self.players[p_id].hand = [] # Clear lobby hands
            self.draw_tiles_for_player(p_id, 12)

    def get_state(self):
        return {
            "room_code": self.room_code,
            "state": self.state,
            "settings": self.settings,
            "players": {
                uuid: {
                    "name": p.name,
                    "color": p.color,
                    "score": p.score,
                    "hand": p.hand if self.state == "INGAME" else []
                } for uuid, p in self.players.items()
            },
            "board": self.board,
            "pending_tiles": self.pending_tiles
        }

    def place_tile(self, x: int, y: int, letter: str, player_id: str, points: int, color: str = None):
        # 타일 존재 여부 체크 (보드 및 대기열)
        if any(t for t in self.board if t['x'] == x and t['y'] == y):
            return False
        
        # Check hand
        if player_id in self.players:
            player = self.players[player_id]
            if letter.upper() not in player.hand:
                logger.warning(f"Player {player.name} tried to place {letter} but they don't have it in hand: {player.hand}")
                return False
            
            # Remove from hand
            player.hand.remove(letter.upper())

        self.board.append({'x': x, 'y': y, 'letter': letter, 'color': color})
        if player_id in self.players:
            self.players[player_id].score += points
        return True

    def _get_combined_board_dict(self):
        board_dict = {(t['x'], t['y']): t['letter'] for t in self.board}
        for t in self.pending_tiles:
            board_dict[(t['x'], t['y'])] = t['letter']
        return board_dict

    def _get_connected_directional_group_ids(self, x: int, y: int, dx: int, dy: int) -> set:
        """지정된 방향(dx, dy)으로 연결된 모든 pending_tile의 group_id를 찾습니다."""
        pending_map = {(t['x'], t['y']): t for t in self.pending_tiles}
        board_tiles = {(t['x'], t['y']) for t in self.board}
        dir_key = 'h_group_id' if dx != 0 else 'v_group_id'
        found_groups = set()

        def find_in_dir(step):
            curr_x, curr_y = x + dx * step, y + dy * step
            while (curr_x, curr_y) in board_tiles:
                curr_x += dx * step
                curr_y += dy * step
            if (curr_x, curr_y) in pending_map:
                gid = pending_map[(curr_x, curr_y)].get(dir_key)
                if gid: found_groups.add(gid)

        find_in_dir(1)
        find_in_dir(-1)
        return found_groups

    async def handle_place_tile(self, x: int, y: int, letter: str, player_id: str, color: str = None):
        """타일을 대기열에 추가하고 가로/세로 타이머를 처리합니다. 병합 로직 포함."""
        logger.debug(f"handle_place_tile: x={x}, y={y}, letter={letter}, player={player_id}, color={color}")
        if any(t for t in self.board if t['x'] == x and t['y'] == y) or \
           any(t for t in self.pending_tiles if t['x'] == x and t['y'] == y):
            return False, "Tile already exists at this position"

        # 방향별 그룹 처리
        def process_direction(dx, dy, prefix):
            found = self._get_connected_directional_group_ids(x, y, dx, dy)
            dir_key = 'h_group_id' if dx != 0 else 'v_group_id'
            
            if not found:
                gid = str(uuid.uuid4())
            else:
                glist = list(found)
                gid = glist[0]
                if len(glist) > 1:
                    # 병합 로직
                    for other_id in glist[1:]:
                        for pt in self.pending_tiles:
                            if pt.get(dir_key) == other_id:
                                pt[dir_key] = gid
                        # 기존 타이머 제거
                        other_key = f"{prefix}:{other_id}"
                        if other_key in self.group_timers:
                            self.group_timers[other_key].cancel()
                            del self.group_timers[other_key]
            return gid

        h_group_id = process_direction(1, 0, "h")
        v_group_id = process_direction(0, 1, "v")

        # 타일 추가
        self.pending_tiles.append({
            'x': x, 'y': y, 'letter': letter, 
            'player_id': player_id, 
            'color': color,
            'h_group_id': h_group_id, 
            'v_group_id': v_group_id
        })

        # 타이머 리셋 (가로/세로)
        for gid, prefix in [(h_group_id, "h"), (v_group_id, "v")]:
            key = f"{prefix}:{gid}"
            if key in self.group_timers: self.group_timers[key].cancel()
            self.group_timers[key] = asyncio.create_task(self._wait_and_finalize_group(gid, prefix))

        await self.broadcast({"type": "UPDATE", "state": self.get_state(), "timer": 5})
        return True, None

    async def _wait_and_finalize_group(self, group_id: str, direction: str):
        try:
            await asyncio.sleep(5)
            await self.finalize_pending_group(group_id, direction)
        except asyncio.CancelledError:
            pass

    async def finalize_pending_group(self, group_id: str, direction: str):
        """특정 방향 그룹을 검증하고 처리합니다."""
        dir_key = 'h_group_id' if direction == 'h' else 'v_group_id'
        group_tiles = [t for t in self.pending_tiles if t.get(dir_key) == group_id]
        
        if not group_tiles: return

        t = group_tiles[0]
        dx, dy = (1, 0) if direction == 'h' else (0, 1)
        board_dict = self._get_combined_board_dict()
        
        # 1. 단어의 시작점 찾기
        curr_x, curr_y = t['x'], t['y']
        while (curr_x - dx, curr_y - dy) in board_dict:
            curr_x -= dx
            curr_y -= dy
        
        start_x, start_y = curr_x, curr_y # 시작 좌표 저장

        # 2. 단어 문자열 구성 및 좌표 리스트 생성
        word = ""
        word_coords = [] # 단어를 구성하는 모든 좌표 (기존 + 신규)
        while (curr_x, curr_y) in board_dict:
            word += board_dict[(curr_x, curr_y)]
            word_coords.append((curr_x, curr_y))
            curr_x += dx
            curr_y += dy

        result = get_word_in_cache(word) if len(word) > 1 else {"is_valid": False}
        
        if result.get("is_valid"):
            logger.debug(f"Valid {direction} word: {word}")
            
            # 이 단어를 완성한 플레이어의 색상 (첫 번째 펜딩 타일 기준)
            new_color = group_tiles[0].get('color', '#4f46e5')
            
            # A. 보드에 이미 있던 타일들의 색상을 새 색상으로 업데이트
            for bx, by in word_coords:
                for board_tile in self.board:
                    if board_tile['x'] == bx and board_tile['y'] == by:
                        board_tile['color'] = new_color
                        break

            # B. 신규 대기 타일들을 보드로 이동 (place_tile 내에서 color 적용)
            for gt in group_tiles:
                if self.place_tile(gt['x'], gt['y'], gt['letter'], gt['player_id'], 10, new_color):
                    if gt['player_id'] in self.players:
                        self.players[gt['player_id']].score += result['score'] // len(group_tiles)
            await self.broadcast_state()
            await self.broadcast({"type": "MODAL", "message": f"Word completed: {word}"})
            
            # pending_tiles 정리
            self.pending_tiles = [pt for pt in self.pending_tiles if not any(bt for bt in self.board if bt['x'] == pt['x'] and bt['y'] == pt['y'])]
        
        else:
            # ... (기존 Invalid 처리 로직 동일) ...
            for gt in group_tiles:
                gt[dir_key] = None
            
            def should_remove(pt):
                h_active = f"h:{pt['h_group_id']}" in self.group_timers if pt['h_group_id'] else False
                v_active = f"v:{pt['v_group_id']}" in self.group_timers if pt['v_group_id'] else False
                return not h_active and not v_active

            to_remove = [pt for pt in self.pending_tiles if should_remove(pt)]
            if to_remove:
                # 애니메이션을 위해 전체 타일 정보를 보냄
                await self.broadcast({"type": "TILE_REMOVED", "tiles": to_remove})
                

            self.pending_tiles = [pt for pt in self.pending_tiles if not should_remove(pt)]
            await self.broadcast_state()

    async def handle_end_game(self):
        """게임을 종료하고 결과를 저장합니다."""
        # 대기 중인 모든 그룹 즉시 처리
        for key in list(self.group_timers.keys()):
            self.group_timers[key].cancel()
            direction, group_id = key.split(':')
            await self.finalize_pending_group(group_id, direction)

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

class SessionManager:
    def __init__(self, code):
        self.code = code
        self.players = {}
        self.state = "LOBBY" # New state tracker
        self.board = []

    async def broadcast_state(self):
        await self.broadcast({"type": "UPDATE", "state": self.get_state()})

room_manager = RoomManager()
session_manager = SessionManager("GLOBAL")
from collections import defaultdict
from typing import Dict, List, Optional
import time
import asyncio
import uuid
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
        logger.debug(f"Player created: {self.name} ({self.player_id})")

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
        self.group_timers: Dict[str, asyncio.Task] = {} # "h:{id}" or "v:{id}" -> timer_task
        
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
        logger.debug(f"Adding player {player.name} to room {self.room_code}")
        self.players[player.player_id] = player

    def remove_player(self, player_id: str):
        logger.debug(f"Removing player {player_id} from room {self.room_code}")
        if player_id in self.players:
            del self.players[player_id]

    async def broadcast(self, message: dict):
        logger.debug(f"Broadcasting message type {message.get('type')} to {len(self.players)} players in {self.room_code}")
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

    def place_tile(self, x: int, y: int, letter: str, player_id: str, points: int, color: str = None):
        # 타일 존재 여부 체크 (보드 및 대기열)
        if any(t for t in self.board if t['x'] == x and t['y'] == y):
            return False
        
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

        # 단어 형성 및 검증
        # 그룹 내 어떤 타일로부터 시작해도 같은 한 줄의 단어가 나옴
        t = group_tiles[0]
        dx, dy = (1, 0) if direction == 'h' else (0, 1)
        board_dict = self._get_combined_board_dict()
        
        # 선형적으로 단어 찾기
        curr_x, curr_y = t['x'], t['y']
        while (curr_x - dx, curr_y - dy) in board_dict:
            curr_x -= dx
            curr_y -= dy
        
        word = ""
        while (curr_x, curr_y) in board_dict:
            word += board_dict[(curr_x, curr_y)]
            curr_x += dx
            curr_y += dy

        result = get_word_in_cache(word) if len(word) > 1 else {"is_valid": False}
        
        if result.get("is_valid"):
            logger.debug(f"Valid {direction} word: {word}")
            # 이 그룹의 모든 대기 타일을 보드로 이동 시도
            # (다른 방향 검증 결과와 상관없이 이 방향으로 유효하다면 보드로 이동)
            for gt in group_tiles:
                # 보드에 타일 영구 배치
                if self.place_tile(gt['x'], gt['y'], gt['letter'], gt['player_id'], 10, gt.get('color')):
                    # 점수 추가 (단어 점수)
                    if gt['player_id'] in self.players:
                        self.players[gt['player_id']].score += result['score'] // len(group_tiles)
            
            # 성공 메시지
            await self.broadcast({"type": "MODAL", "message": f"Word completed ({direction}): {word}"})
            
            # 보드로 이동한 타일들을 pending에서 제거
            self.pending_tiles = [pt for pt in self.pending_tiles if not any(bt for bt in self.board if bt['x'] == pt['x'] and bt['y'] == pt['y'])]
        else:
            logger.debug(f"Invalid {direction} word or single letter: {word}")
            # 이 방향으로는 유효하지 않음. 
            # 하지만 다른 방향(교차되는 방향)의 타이머가 아직 살아있거나 유효할 수 있음.
            # 이 방향의 그룹 ID를 제거하여 '이 방향으로는 더 이상 펜딩이 아님'을 표시
            for gt in group_tiles:
                gt[dir_key] = None
            
            # 만약 타일이 가로/세로 양쪽 모두에서 확정이 안 되거나 타이머가 끝났다면 제거
            def should_remove(pt):
                h_active = f"h:{pt['h_group_id']}" in self.group_timers if pt['h_group_id'] else False
                v_active = f"v:{pt['v_group_id']}" in self.group_timers if pt['v_group_id'] else False
                return not h_active and not v_active

            # 양쪽 다 끝났는데도 보드에 못 올라갔다면(유효한 단어가 없다면) 제거
            to_remove = [pt for pt in self.pending_tiles if should_remove(pt)]
            if to_remove:
                removed_coords = [{"x": rt["x"], "y": rt["y"]} for rt in to_remove]
                logger.debug(f"Broadcasting TILE_REMOVED for coordinates: {removed_coords}")
                await self.broadcast({"type": "TILE_REMOVED", "coords": removed_coords})

            self.pending_tiles = [pt for pt in self.pending_tiles if not should_remove(pt)]

        # 타이머 정리 및 업데이트
        key = f"{direction}:{group_id}"
        if key in self.group_timers: del self.group_timers[key]
        await self.broadcast({"type": "UPDATE", "state": self.get_state()})

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

room_manager = RoomManager()
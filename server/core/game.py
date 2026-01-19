from collections import defaultdict
from typing import Dict, List, Optional
import time
import asyncio
import uuid
import random
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
        self.hand: List[Optional[str]] = [None] * 10
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
        self.settings = {
            "mode": "classic",
            "max_players": 10
        }
        self.board: Dict[tuple, Dict] = {} # (x, y) -> {'x': x, 'y': y, 'letter': letter, 'color': color}
        self.pending_tiles: List[Dict] = []
        self.players: Dict[str, Player] = {}
        self.status = "LOBBY" # LOBBY, INGAME, FINISHED
        self.created_at = time.time()
        self.group_timers: Dict[str, asyncio.Task] = {} # "h:{id}" or "v:{id}" -> timer_task
        self.room_timer_task: Optional[asyncio.Task] = None
        self.duration: int = 0
        self.start_time: Optional[float] = None
        self.lock = asyncio.Lock()


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
        
        player = self.players[player_id]
        new_tiles = generate_weighted_tiles(count)
        drawn = []
        
        for tile in new_tiles:
            # Find first available None slot
            try:
                empty_idx = player.hand.index(None)
                player.hand[empty_idx] = tile
                drawn.append(tile)
            except ValueError:
                # Hand is full
                break
                
        logger.debug(f"Player {player.name} drew {len(drawn)} tiles: {drawn}")
        return drawn

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
        self.status = "INGAME"
        
        # Give each player a random 6-10 letter word as starting tiles
        for p_id, player in self.players.items():
            player.hand = [None] * 10 # Reset and fix size
            word = get_random_word(min_length=6, max_length=10)
            if word:
                letters = list(word.upper())[:10] # Cap at 10
                for i, letter in enumerate(letters):
                    player.hand[i] = letter
                logger.debug(f"Player {player.name} starting with word tiles: {word}")
            else:
                # Fallback if no word found
                logger.warning(f"No 6-10 letter word found for player {player.name}, falling back to random tiles.")
                self.draw_tiles_for_player(p_id, 8)
    
    def get_state(self):
        remaining_time = 0
        if self.start_time and self.duration:
            elapsed = time.time() - self.start_time
            remaining_time = max(0, self.duration - int(elapsed))

        return {
            "room_code": self.room_code,
            "status": self.status,
            "settings": self.settings,
            "players": {
                pid: p.to_dict() for pid, p in self.players.items()
            },
            "board": list(self.board.values()),
            "pending_tiles": self.pending_tiles,
            "remaining_time": remaining_time
        }

    def place_tile(self, x: int, y: int, letter: str, player_id: str, points: int, color: str = None, consume_hand: bool = True):
        # 타일 존재 여부 체크 (보드 및 대기열)
        if (x, y) in self.board:
            return False
        
        # Check hand
        if consume_hand and player_id in self.players:
            player = self.players[player_id]
            if letter.upper() not in player.hand:
                logger.warning(f"Player {player.name} tried to place {letter} but they don't have it in hand: {player.hand}")
                return False
            
            # Remove from hand
            if letter.upper() in player.hand:
                player.hand.remove(letter.upper())

        self.board[(x, y)] = {'x': x, 'y': y, 'letter': letter, 'color': color}
        if player_id in self.players:
            self.players[player_id].score += points
        return True

    def _get_combined_board_dict(self):
        board_dict = {pos: t['letter'] for pos, t in self.board.items()}
        for t in self.pending_tiles:
            board_dict[(t['x'], t['y'])] = t['letter']
        return board_dict

    def _get_word_at(self, x: int, y: int, direction: str) -> str:
        """지정된 좌표(x, y)를 포함하는 단어를 추출합니다."""
        dx, dy = (1, 0) if direction == 'h' else (0, 1)
        board_dict = self._get_combined_board_dict()
        
        # 선형적으로 단어의 시작 찾기
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

    def _get_connected_directional_group_ids(self, x: int, y: int, dx: int, dy: int) -> set:
        """지정된 방향(dx, dy)으로 연결된 모든 pending_tile의 group_id를 찾습니다."""
        pending_map = {(t['x'], t['y']): t for t in self.pending_tiles}
        board_tiles = self.board # Dictionary keys are coordinates
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

    async def handle_place_tile(self, x: int, y: int, letter: str, player_id: str, color: str = None, hand_index: int = None):
        """타일을 대기열에 추가하고 가로/세로 타이머를 처리합니다. 병합 로직 포함."""
        async with self.lock:
            logger.debug(f"handle_place_tile: x={x}, y={y}, letter={letter}, player={player_id}, color={color}, hand_index={hand_index}")
            
            if player_id not in self.players:
                return False, "Player not found"
                
            player = self.players[player_id]
            letter_upper = letter.upper()

            if (x, y) in self.board or \
               any(t for t in self.pending_tiles if t['x'] == x and t['y'] == y):
                return False, "Tile already exists at this position"

            # 핸드 체크
            if hand_index is not None and 0 <= hand_index < len(player.hand):
                if player.hand[hand_index] != letter_upper:
                    return False, f"Tile {letter_upper} not found at slot {hand_index}"
                # Consumption will happen below if valid
            else:
                # Fallback to search if index not provided
                if letter_upper not in player.hand:
                    return False, f"Not enough {letter_upper} in hand"

            # 연결성 체크 (첫 타일 제외)
            is_first_tile = not self.board and not self.pending_tiles
            if not is_first_tile:
                has_adj = False
                for dx, dy in [(1,0), (-1,0), (0,1), (0,-1)]:
                    nx, ny = x + dx, y + dy
                    if (nx, ny) in self.board or any(pt['x'] == nx and pt['y'] == ny for pt in self.pending_tiles):
                        has_adj = True
                        break
                if not has_adj:
                    return False, "Tile must be adjacent to existing or pending tiles"

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
                'v_group_id': v_group_id,
                'hand_index': hand_index
            })

            # Consume from hand
            if hand_index is not None:
                player.hand[hand_index] = None
            else:
                idx = player.hand.index(letter_upper)
                player.hand[idx] = None

            # 즉시 검증 시도
            finalized_h = False
            finalized_v = False
            
            # 가로 즉시 검증
            h_word = self._get_word_at(x, y, 'h')
            v_word = self._get_word_at(x, y, 'v')
            
            # 가로 단어가 유효하고, 세로 방향도 유효성(1글자거나 유효단어)을 충족할 때만 즉시 확정
            if len(h_word) > 1 and get_word_in_cache(h_word).get("is_valid"):
                if len(v_word) == 1 or get_word_in_cache(v_word).get("is_valid"):
                    await self.finalize_pending_group(h_group_id, 'h')
                    finalized_h = True
                
            # 세로 즉시 검증 (가로가 이미 확정되었더라도 독립적으로 체크)
            if len(v_word) > 1 and get_word_in_cache(v_word).get("is_valid"):
                # 세로 단어가 유효하고, 가로 방향도 유효성을 충족할 때
                if len(h_word) == 1 or get_word_in_cache(h_word).get("is_valid"):
                    # 중복 확정 방지: 가로 확정 시 이미 보드에 들어갔을 수 있음
                    await self.finalize_pending_group(v_group_id, 'v')
                    finalized_v = True

            # 확정되지 않은 방향만 타이머 시작
            if not finalized_h:
                key = f"h:{h_group_id}"
                if key in self.group_timers: self.group_timers[key].cancel()
                self.group_timers[key] = asyncio.create_task(self._wait_and_finalize_group(h_group_id, "h"))
                
            if not finalized_v:
                key = f"v:{v_group_id}"
                if key in self.group_timers: self.group_timers[key].cancel()
                self.group_timers[key] = asyncio.create_task(self._wait_and_finalize_group(v_group_id, "v"))

            if finalized_h or finalized_v:
                 await self.broadcast({"type": "UPDATE", "state": self.get_state()})
            else:
                 await self.broadcast({"type": "UPDATE", "state": self.get_state(), "timer": 3})
                 
            return True, None

    async def _wait_and_finalize_group(self, group_id: str, direction: str):
        key = f"{direction}:{group_id}"
        try:
            await asyncio.sleep(3)
            await self.finalize_pending_group(group_id, direction)
        except asyncio.CancelledError:
            pass
        finally:
            # 작업이 완료되거나 취소되었을 때 딕셔너리에서 제거
            # 단, 현재 태스크가 딕셔너리에 등록된 태스크와 일치할 때만 제거 (경합 방지)
            if self.group_timers.get(key) == asyncio.current_task():
                del self.group_timers[key]

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
        
        # 3. 모든 타일에 대해 교차 방향 단어도 유효한지 확인 (Scrabble Rule)
        if result.get("is_valid"):
            cross_direction = 'v' if direction == 'h' else 'h'
            for bx, by in word_coords:
                cross_word = self._get_word_at(bx, by, cross_direction)
                if len(cross_word) > 1:
                    cross_result = get_word_in_cache(cross_word)
                    if not cross_result.get("is_valid"):
                        logger.debug(f"Invalid cross word '{cross_word}' found at ({bx}, {by}) while validating '{word}'")
                        result["is_valid"] = False
                        break

        if result.get("is_valid"):
            logger.debug(f"Valid {direction} word: {word}")
            
            # 이 단어를 완성한 플레이어의 색상 (첫 번째 펜딩 타일 기준)
            new_color = group_tiles[0].get('color', '#4f46e5')
            
            # A. 보드에 이미 있던 타일들의 색상을 새 색상으로 업데이트
            for bx, by in word_coords:
                if (bx, by) in self.board:
                    self.board[(bx, by)]['color'] = new_color

            # B. 신규 대기 타일들을 보드로 이동 (place_tile 내에서 color 적용)
            # B. 신규 대기 타일들을 보드로 이동
            for gt in group_tiles:
                # 중복 방지: 이미 보드에 있는 타일인지 확인
                if (gt['x'], gt['y']) in self.board:
                    continue

                # IMPORTANT: consume_hand=False because it was already consumed in handle_place_tile
                if self.place_tile(gt['x'], gt['y'], gt['letter'], gt['player_id'], 10, new_color, consume_hand=False):
                    if gt['player_id'] in self.players:
                        self.players[gt['player_id']].score += result['score'] // len(group_tiles)
                        # 보충
                        self.draw_tiles_for_player(gt['player_id'], 1)

            # pending_tiles 정리 (Broadcasting 전에 수행해야 정확한 상태가 전달됨)
            self.pending_tiles = [pt for pt in self.pending_tiles if (pt['x'], pt['y']) not in self.board]

            await self.broadcast_state()
            await self.broadcast({"type": "MODAL", "message": f"Word completed: {word}"})
        
        else:
            # Invalid Word Penalty
            penalty_points = 10
            penalized_players = set()
            for gt in group_tiles:
                pid = gt['player_id']
                if pid in self.players:
                    self.players[pid].score = max(0, self.players[pid].score - penalty_points)
                    penalized_players.add(pid)
            
            if penalized_players:
                logger.info(f"Penalty applied to players {penalized_players} for invalid word: {word}")
                await self.broadcast({"type": "MODAL", "message": f"Invalid word: {word}. -{penalty_points} points penalty!"})

            # 4. 검증 실패 시 해당 방향 타이머 정보 제거 (현재 로직이 직접 실행 중이므로)
            key = f"{direction}:{group_id}"
            if self.group_timers.get(key) == asyncio.current_task() or \
               (key in self.group_timers and self.group_timers[key].done()):
                if key in self.group_timers:
                    del self.group_timers[key]

            def should_remove(pt):
                # 타일이 제거되려면 가로/세로 모든 연결 그룹의 타이머가 종료되어야 함
                h_active = f"h:{pt['h_group_id']}" in self.group_timers if pt['h_group_id'] else False
                v_active = f"v:{pt['v_group_id']}" in self.group_timers if pt['v_group_id'] else False
                return not h_active and not v_active

            to_remove = [pt for pt in self.pending_tiles if should_remove(pt)]
            if to_remove:
                # Return to hand
                for pt in to_remove:
                    pid = pt['player_id']
                    if pid in self.players:
                        p = self.players[pid]
                        h_idx = pt.get('hand_index')
                        if h_idx is not None and 0 <= h_idx < len(p.hand):
                            # Try to put it back in the original slot if empty
                            if p.hand[h_idx] is None:
                                p.hand[h_idx] = pt['letter']
                            else:
                                # Find another empty slot
                                for i in range(len(p.hand)):
                                    if p.hand[i] is None:
                                        p.hand[i] = pt['letter']
                                        break
                
                # 애니메이션을 위해 전체 타일 정보를 보냄
                await self.broadcast({"type": "TILE_REMOVED", "tiles": to_remove})
                
            self.pending_tiles = [pt for pt in self.pending_tiles if not should_remove(pt)]
            await self.broadcast_state()

    async def handle_end_game(self):
        """게임을 종료하고 결과를 저장합니다."""
        if self.room_timer_task:
            self.room_timer_task.cancel()
            self.room_timer_task = None

        # 대기 중인 모든 그룹 즉시 처리
        for key in list(self.group_timers.keys()):
            self.group_timers[key].cancel()
            direction, group_id = key.split(':')
            await self.finalize_pending_group(group_id, direction)

        players_data = {pid: p.to_dict() for pid, p in self.players.items()}
        game_id = await save_game_result(self.room_code, players_data)
        self.status = "FINISHED"
        
        # 방 제거 예약 (1분 뒤)
        asyncio.create_task(self._cleanup_room())
        
        return game_id

    async def _cleanup_room(self):
        await asyncio.sleep(60)
        room_manager.remove_room(self.room_code)
        logger.info(f"Room {self.room_code} cleaned up and removed.")

    def start_timer(self, duration: int):
        """방 전체 타이머를 시작합니다."""
        if self.room_timer_task:
            self.room_timer_task.cancel()
        
        self.duration = duration
        self.start_time = time.time()
        self.room_timer_task = asyncio.create_task(self._run_timer(duration))
        logger.info(f"Room timer started for {self.room_code}: {duration}s")

    def update_settings(self, settings: dict):
        """방 설정을 업데이트합니다."""
        self.settings.update(settings)
        logger.info(f"Room settings updated for {self.room_code}: {self.settings}")

    async def _run_timer(self, duration: int):
        try:
            await asyncio.sleep(duration)
            logger.info(f"Timer expired for room {self.room_code}. Finalizing game.")
            game_id = await self.handle_end_game()
            await self.broadcast({
                "type": "GAME_OVER",
                "game_id": game_id,
                "state": self.get_state(),
                "reason": "TIMER_EXPIRED"
            })
        except asyncio.CancelledError:
            logger.debug(f"Room timer for {self.room_code} cancelled.")

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
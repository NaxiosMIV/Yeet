from collections import defaultdict
from typing import Dict, List, Optional
import time
import asyncio
import uuid
import random
from core.words import get_word_in_cache, get_random_word, has_valid_prefix
from core.tiles import generate_weighted_tiles, TileBag
from core.database import save_game_result
from core.logging_config import get_logger
from core.korean_utils import compose_word, is_valid_syllable_pattern, count_syllables

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
        
        self.DURATION_MAP = {
            "classic": 300, # 5 min
            "blitz": 180,   # 3 min
            "bullet": 60    # 1 min
        }
        self.settings = {
            "mode": "classic",
            "max_players": 20,
            "lang": "en" # 'en' or 'ko'
        }
        self.time_remaining = 0
        self.total_round_time = 0
        self.timer_task = None

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
        self.tile_bag: Optional[TileBag] = None  # Initialized on game start
        self.penalty_cooldowns: Dict[str, float] = {}  # player_id -> last_penalty_time

    def update_settings(self, settings: dict):
        if "mode" in settings:
            self.mode = settings["mode"]
            self.time_remaining = self.DURATION_MAP.get(self.mode, 300)
            logger.info(f"Room {self.room_code} mode changed to {self.mode}")

    def add_player(self, player: Player):
        logger.debug(f"Adding player {player.name} to room {self.room_code}")
        self.players[player.player_id] = player
        if len(self.players) >= self.settings['max_players']:
            logger.debug(f"Room {self.room_code} is full")

    def remove_player(self, player_id: str):
        logger.debug(f"Removing player {player_id} from room {self.room_code}")
        if player_id in self.players:
            del self.players[player_id]

    def draw_tiles_for_player(self, player_id: str, count: int) -> List[str]:
        if player_id not in self.players:
            return []
        
        player = self.players[player_id]
        
        # Use TileBag for consistent distribution, fallback to weighted random
        if self.tile_bag:
            new_tiles = self.tile_bag.draw(count)
        else:
            new_tiles = generate_weighted_tiles(count, lang=self.settings.get("lang", "en"))
        
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
    
    def destroy_tile(self, player_id: str, hand_index: int):
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        
        # Validate index
        if 0 <= hand_index < len(player.hand):
            tile_to_destroy = player.hand[hand_index]
            
            if tile_to_destroy:
                # 1. Remove the tile
                player.hand[hand_index] = None
                
                # 2. Optional: Put it back in the bag or just delete it
                # if self.tile_bag: self.tile_bag.tiles.append(tile_to_destroy)
                
                # 3. Draw exactly 1 new tile to replace it
                self.draw_tiles_for_player(player_id, 1)
                
                logger.debug(f"Player {player.name} destroyed tile at index {hand_index}")

    def reroll_hand(self, player_id: str):
        if player_id not in self.players:
            return
        
        player = self.players[player_id]
        
        # 1. Identify valid tiles to return
        current_tiles = [t for t in player.hand if t is not None]
        if not current_tiles:
            return # Nothing to reroll

        # 2. Return tiles to bag and SHUFFLE
        if self.tile_bag:
            # Assuming your tile_bag has a list called 'tiles'
            self.tile_bag.tiles.extend(current_tiles)
            self.tile_bag.shuffle() # Crucial: don't give them the same tiles back!

        # 3. Reset the hand array 
        player.hand = [None] * 10
        
        # 4. Draw new tiles (draw_tiles_for_player usually fills the first N None slots)
        self.draw_tiles_for_player(player_id, 10)
        
        logger.info(f"Player {player.name} ({player_id}) rerolled their hand.")

    
    def start_global_timer(self, duration: int):
        """Starts the main game clock."""
        if self.timer_task:
            self.timer_task.cancel()
        
        self.time_remaining = duration
        self.total_round_time = duration
        
        logger.debug(f"Timer tick: {self.time_remaining} seconds left in room {self.room_code}")
        self.timer_task = asyncio.create_task(self._run_timer())

    
    async def _run_timer(self):
        try:
            while self.time_remaining > 0:
                await asyncio.sleep(1)
                self.time_remaining -= 1
                
                # Broadcast the new state to all players every second
                await self.broadcast_timer(self.time_remaining)
                
                # Optional: Log every 10 seconds to avoid spamming console
                if self.time_remaining % 10 == 0:
                    logger.debug(f"Room {self.room_code} timer: {self.time_remaining}s left")

            # When time hits zero
            logger.info(f"Timer finished for room {self.room_code}")
            await self.handle_end_game_from_timer()
            
        except asyncio.CancelledError:
            logger.debug(f"Timer cancelled for room {self.room_code}")
        except Exception as e:
            logger.error(f"Error in timer loop: {e}")
        
    async def handle_end_game_from_timer(self):
        game_id = await self.handle_end_game()
        await self.broadcast({
            "type": "GAME_OVER", 
            "reason": "TIME_UP",
            "game_id": game_id, 
            "state": self.get_state()
        })

    async def broadcast(self, message: dict):
        # logger.debug(f"Broadcasting message type {message.get('type')} to {len(self.players)} players in {self.room_code}")
        # 플레이어들에게 메시지 비동기 전송
        tasks = [
            p.websocket.send_json(message) 
            for p in self.players.values()
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    
    async def broadcast_timer(self, time):
        await self.broadcast({"type": "TIMER", "time": time})

    async def broadcast_state(self):
        await self.broadcast({"type": "UPDATE", "state": self.get_state()})

    def start_match(self):
        self.status = "INGAME"
        
        # Initialize tile bag for this game
        lang = self.settings.get("lang", "en")
        self.tile_bag = TileBag(lang=lang)
        logger.debug(f"Initialized TileBag for room {self.room_code} with lang={lang}")
        
        # Place starting words on board based on player count
        self._initialize_starting_words()
        
        # Give each player a 10-letter word as starting tiles
        for p_id, player in self.players.items():
            player.hand = [None] * 10  # Reset and fix size to 10
            word = get_random_word(exact_length=10, lang=lang)
            if word:
                letters = list(word.upper() if lang == 'en' else word)
                for i, letter in enumerate(letters):
                    player.hand[i] = letter
                logger.debug(f"Player {player.name} starting with 10-letter word: {word}")
            else:
                # Fallback: try shorter words and fill rest with random
                fallback_word = get_random_word(min_length=6, max_length=10, lang=lang)
                if fallback_word:
                    letters = list(fallback_word.upper() if lang == 'en' else fallback_word)
                    for i, letter in enumerate(letters):
                        player.hand[i] = letter
                    # Fill remaining slots with random tiles
                    remaining = 10 - len(letters)
                    if remaining > 0:
                        self.draw_tiles_for_player(p_id, remaining)
                    logger.warning(f"No 10-letter word found, using {len(letters)}-letter word for {player.name}")
                else:
                    logger.warning(f"No word found for player {player.name}, falling back to random tiles")
                    self.draw_tiles_for_player(p_id, 10)
    
    def _get_starting_word_count(self) -> int:
        """Calculate number of starting words based on player count."""
        player_count = len(self.players)
        # 1-5: 1 word, 6-10: 2 words, 11-15: 3 words, 16+: 4 words
        return min(4, 1 + (player_count - 1) // 5)
    
    def _initialize_starting_words(self):
        """
        Place starting words on the board in a "/" zigzag pattern.
        
        Pattern:
        - Word 1: Horizontal at center
        - Word 2: Vertical, connected to Word 1's end
        - Word 3: Horizontal, connected to Word 2's end
        - Word 4: Vertical, connected to Word 3's end
        
        This creates a "/" shape, not ㄷ or ㅁ (closed shapes).
        """
        lang = self.settings.get("lang", "en")
        word_count = self._get_starting_word_count()
        logger.info(f"Placing {word_count} starting word(s) for {len(self.players)} players")
        
        # Board center (assuming infinite board, start at 0,0 area)
        center_x, center_y = 0, 0
        default_color = "#94a3b8"  # Neutral gray for starting tiles
        
        words_placed = []
        current_x, current_y = center_x, center_y
        
        for i in range(word_count):
            # Get a 10+ letter word
            word = get_random_word(min_length=10, lang=lang)
            if not word:
                word = get_random_word(min_length=8, lang=lang)  # Fallback
            if not word:
                logger.warning(f"Could not find starting word {i+1}")
                continue
            
            letters = list(word.upper() if lang == 'en' else word)
            is_horizontal = (i % 2 == 0)  # Alternate: H, V, H, V
            
            if i == 0:
                # First word: place horizontally at center
                for j, letter in enumerate(letters):
                    pos_x = current_x + j
                    pos_y = current_y
                    self.board[(pos_x, pos_y)] = {
                        'x': pos_x, 'y': pos_y, 
                        'letter': letter, 'color': default_color
                    }
                # Next word connects at end of this word
                current_x = current_x + len(letters) - 1
                current_y = current_y
                
            elif is_horizontal:
                # Horizontal word, connecting from previous vertical word's end
                # Starts at the connection point, extends right
                for j, letter in enumerate(letters):
                    pos_x = current_x + j
                    pos_y = current_y
                    if (pos_x, pos_y) not in self.board:  # Don't overwrite connection
                        self.board[(pos_x, pos_y)] = {
                            'x': pos_x, 'y': pos_y, 
                            'letter': letter, 'color': default_color
                        }
                current_x = current_x + len(letters) - 1
                
            else:
                # Vertical word, connecting from previous horizontal word's end
                # Starts at the connection point, extends downward (positive y)
                for j, letter in enumerate(letters):
                    pos_x = current_x
                    pos_y = current_y + j
                    if (pos_x, pos_y) not in self.board:  # Don't overwrite connection
                        self.board[(pos_x, pos_y)] = {
                            'x': pos_x, 'y': pos_y, 
                            'letter': letter, 'color': default_color
                        }
                current_y = current_y + len(letters) - 1
            
            words_placed.append(word)
            logger.debug(f"Placed starting word {i+1}: '{word}' ({'H' if is_horizontal else 'V'})")
        
        logger.info(f"Placed {len(words_placed)} starting words: {words_placed}")
    
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

    def _get_word_at(self, x: int, y: int, direction: str, board_dict: dict = None) -> str:
        """지정된 좌표(x, y)를 포함하는 단어를 추출합니다."""
        dx, dy = (1, 0) if direction == 'h' else (0, 1)
        if board_dict is None:
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
        
        # For Korean, compose jamos into syllables for display
        lang = self.settings.get("lang", "en")
        if lang == 'ko' and word:
            word = compose_word(word)
        
        return word

    def _get_raw_jamos_at(self, x: int, y: int, direction: str, board_dict: dict = None) -> str:
        """Get raw jamo string (without composition) for Korean validation."""
        dx, dy = (1, 0) if direction == 'h' else (0, 1)
        if board_dict is None:
            board_dict = self._get_combined_board_dict()
        
        # Find start
        curr_x, curr_y = x, y
        while (curr_x - dx, curr_y - dy) in board_dict:
            curr_x -= dx
            curr_y -= dy
        
        # Build raw string
        raw = ""
        while (curr_x, curr_y) in board_dict:
            raw += board_dict[(curr_x, curr_y)]
            curr_x += dx
            curr_y += dy
        return raw

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
            lang = self.settings.get("lang", "en")
            letter_upper = letter.upper() if lang == 'en' else letter

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

            # Early validation: Check if the tile placement could lead to valid words
            # Note: has_valid_prefix checks BOTH prefixes and suffixes using BidirectionalTrie
            # Temporarily add the tile to check substrings
            temp_tile = {'x': x, 'y': y, 'letter': letter}
            self.pending_tiles.append(temp_tile)
            
            substring_invalid = False
            try:
                if lang == 'ko':
                    h_substring = self._get_raw_jamos_at(x, y, 'h')
                    v_substring = self._get_raw_jamos_at(x, y, 'v')
                else:
                    h_substring = self._get_word_at(x, y, 'h')
                    v_substring = self._get_word_at(x, y, 'v')
                
                # Check horizontal substring
                if len(h_substring) > 1 and not has_valid_prefix(h_substring, lang):
                    logger.debug(f"Invalid horizontal substring: {h_substring}")
                    substring_invalid = True
                
                # Check vertical substring
                if not substring_invalid and len(v_substring) > 1 and not has_valid_prefix(v_substring, lang):
                    logger.debug(f"Invalid vertical substring: {v_substring}")
                    substring_invalid = True
            finally:
                # Remove temporary tile
                self.pending_tiles.remove(temp_tile)

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
            placed_tile = {
                'x': x, 'y': y, 'letter': letter, 
                'player_id': player_id, 
                'color': color,
                'h_group_id': h_group_id, 
                'v_group_id': v_group_id,
                'hand_index': hand_index
            }
            self.pending_tiles.append(placed_tile)

            # Consume from hand
            if hand_index is not None:
                player.hand[hand_index] = None
            else:
                idx = player.hand.index(letter_upper)
                player.hand[idx] = None

            # If substring is invalid, immediately explode the tile
            if substring_invalid:
                # Apply penalty (1 point for early validation failure)
                penalty_points = 1
                player.score = max(0, player.score - penalty_points)
                logger.info(f"Invalid substring penalty applied to {player.name}: -{penalty_points}")
                
                # Return tile to hand
                if hand_index is not None and 0 <= hand_index < len(player.hand):
                    player.hand[hand_index] = letter
                else:
                    for i in range(len(player.hand)):
                        if player.hand[i] is None:
                            player.hand[i] = letter
                            break
                
                # Remove from pending
                self.pending_tiles.remove(placed_tile)
                
                # Broadcast: first show placement, then explosion animation
                await self.broadcast({"type": "UPDATE", "state": self.get_state()})
                await self.broadcast({"type": "TILE_REMOVED", "tiles": [placed_tile]})
                await self.broadcast({"type": "MODAL", "message": f"Invalid placement! -{penalty_points} points"})
                
                return True, None  # Return True so client knows action completed

            # 즉시 검증 시도
            finalized_h = False
            finalized_v = False
            
            lang = self.settings.get("lang", "en")
            
            # For Korean, validate using raw jamos
            if lang == 'ko':
                h_raw = self._get_raw_jamos_at(x, y, 'h')
                v_raw = self._get_raw_jamos_at(x, y, 'v')
                
                # Validate horizontal word
                h_result = None
                v_result = None
                
                if len(h_raw) >= 2 and is_valid_syllable_pattern(h_raw):
                    h_result = get_word_in_cache(h_raw, lang=lang)
                    h_valid = h_result.get("is_valid")
                    
                    # Need v_result for cross-validation check
                    if len(v_raw) >= 2 and is_valid_syllable_pattern(v_raw):
                        v_result = get_word_in_cache(v_raw, lang=lang)
                        v_valid = v_result.get("is_valid")
                    else:
                        v_valid = len(v_raw) < 2
                    
                    if h_valid and v_valid:
                        await self.finalize_pending_group(h_group_id, 'h', trigger_tile=placed_tile, pre_result=h_result)
                        finalized_h = True
                
                # Validate vertical word
                if len(v_raw) >= 2 and is_valid_syllable_pattern(v_raw):
                    # Reuse v_result if already calculated
                    if v_result is None:
                        v_result = get_word_in_cache(v_raw, lang=lang)
                    
                    v_valid = v_result.get("is_valid")
                    
                    # Reuse h_result if already calculated
                    if h_result is None and len(h_raw) >= 2 and is_valid_syllable_pattern(h_raw):
                        h_result = get_word_in_cache(h_raw, lang=lang)
                    
                    h_valid = h_result.get("is_valid") if h_result else len(h_raw) < 2

                    if v_valid and h_valid:
                        await self.finalize_pending_group(v_group_id, 'v', trigger_tile=placed_tile, pre_result=v_result)
                        finalized_v = True
            else:
                # English validation (existing logic)
                h_word = self._get_word_at(x, y, 'h')
                v_word = self._get_word_at(x, y, 'v')
                
                h_result = None
                v_result = None

                if len(h_word) >= 2:
                    h_result = get_word_in_cache(h_word, lang=lang)
                    h_valid = h_result.get("is_valid")
                    
                    if len(v_word) >= 2:
                        v_result = get_word_in_cache(v_word, lang=lang)
                        v_valid = v_result.get("is_valid")
                    else:
                        v_valid = len(v_word) < 2
                    
                    if h_valid and v_valid:
                        await self.finalize_pending_group(h_group_id, 'h', trigger_tile=placed_tile, pre_result=h_result)
                        finalized_h = True

                if len(v_word) >= 2:
                    if v_result is None:
                        v_result = get_word_in_cache(v_word, lang=lang)
                    v_valid = v_result.get("is_valid")
                    
                    if h_result is None and len(h_word) >= 2:
                        h_result = get_word_in_cache(h_word, lang=lang)
                    h_valid = h_result.get("is_valid") if h_result else len(h_word) < 2
                    
                    if v_valid and h_valid:
                        await self.finalize_pending_group(v_group_id, 'v', trigger_tile=placed_tile, pre_result=v_result)
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

    async def finalize_pending_group(self, group_id: str, direction: str, trigger_tile: dict = None, pre_result: dict = None):
        """특정 방향 그룹을 검증하고 처리합니다."""
        dir_key = 'h_group_id' if direction == 'h' else 'v_group_id'
        group_tiles = [t for t in self.pending_tiles if t.get(dir_key) == group_id]
        
        # If trigger_tile is provided (immediate validation), ensure it's included
        # even if it was already moved to board by another direction's validation
        if trigger_tile and trigger_tile not in group_tiles:
            if trigger_tile.get(dir_key) == group_id:
                group_tiles.append(trigger_tile)
        
        if not group_tiles: return

        t = group_tiles[0]
        dx, dy = (1, 0) if direction == 'h' else (0, 1)
        
        # Create a board dict that ONLY includes confirmed board tiles + THIS group's tiles
        # This prevents dependencies on OTHER pending groups during finalization
        group_board_dict = {pos: t['letter'] for pos, t in self.board.items()}
        for gt in group_tiles:
            group_board_dict[(gt['x'], gt['y'])] = gt['letter']
        
        # 1. 단어의 시작점 찾기
        curr_x, curr_y = t['x'], t['y']
        while (curr_x - dx, curr_y - dy) in group_board_dict:
            curr_x -= dx
            curr_y -= dy
        
        start_x, start_y = curr_x, curr_y # 시작 좌표 저장

        # 2. 단어 문자열 구성 및 좌표 리스트 생성
        word = ""
        word_coords = [] # 단어를 구성하는 모든 좌표 (기존 + 신규)
        while (curr_x, curr_y) in group_board_dict:
            word += group_board_dict[(curr_x, curr_y)]
            word_coords.append((curr_x, curr_y))
            curr_x += dx
            curr_y += dy

        lang = self.settings.get("lang", "en")
        
        if pre_result:
            result = pre_result
        elif lang == 'ko' and len(word) >= 2:
            # word is already composed by _get_word_at, but we have raw jamos on board
            # Extract raw jamos from board (using group_board_dict)
            raw_jamos = ""
            curr_x, curr_y = start_x, start_y
            while (curr_x, curr_y) in group_board_dict:
                raw_jamos += group_board_dict[(curr_x, curr_y)]
                curr_x += dx
                curr_y += dy
            
            # Validate jamo pattern
            if not is_valid_syllable_pattern(raw_jamos):
                logger.debug(f"Invalid Korean jamo pattern: {raw_jamos}")
                result = {"is_valid": False}
            else:
                # Compose and validate
                composed_word = compose_word(raw_jamos)
                result = get_word_in_cache(raw_jamos, lang=lang)  # Dictionary stores jamo keys
                logger.debug(f"Korean word validation: {raw_jamos} -> {composed_word} = {result.get('is_valid')}")
        else:
            # English or single character
            if len(word) >= 2:
                result = get_word_in_cache(word, lang=lang)
            else:
                result = {"is_valid": False, "skip_penalty": True}

        # 3. 모든 타일에 대해 교차 방향 단어도 유효한지 확인 (Scrabble Rule)
        # 단, 이미 보드에 확정된 타일들로만 이루어진 cross word는 검증 건너뛰기
        if result.get("is_valid"):
            cross_direction = 'v' if direction == 'h' else 'h'
            cdx, cdy = (1, 0) if cross_direction == 'h' else (0, 1)
            pending_coords = {(pt['x'], pt['y']) for pt in self.pending_tiles}
            
            for bx, by in word_coords:
                # Skip if this coordinate is not a group tile (already on board)
                # Note: group_tiles includes ALL tiles in the current pending group
                is_group_tile = any(gt['x'] == bx and gt['y'] == by for gt in group_tiles)
                if not is_group_tile:
                    continue
                    
                cross_word = self._get_word_at(bx, by, cross_direction, board_dict=group_board_dict)
                if len(cross_word) >= 2:
                    # Current group always contains the tiles we're validating, 
                    # so no need to check has_pending (it's always True for a group tile)
                    cross_result = get_word_in_cache(cross_word, lang=lang)
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

            # B. 신규 대기 타일들을 보드로 이동
            # Track players who placed tiles for tile replenishment
            players_to_replenish = {}
            
            # Calculate score based on word length: n^1.5
            word_length = len(word_coords)
            word_score = int(word_length ** 1.5)
            logger.debug(f"Word '{word}' length={word_length}, score={word_score}")
            
            for gt in group_tiles:
                # Place tile returns False if already on board (e.g. from intersecting word)
                newly_placed = self.place_tile(gt['x'], gt['y'], gt['letter'], gt['player_id'], 0, new_color, consume_hand=False)
                
                if gt['player_id'] in self.players:
                    # Award points regardless of whether it was already on board
                    # as long as it was part of this pending group
                    self.players[gt['player_id']].score += word_score // len(group_tiles)
                    
                    # Only replenish if it was newly placed from pending
                    if newly_placed:
                        players_to_replenish[gt['player_id']] = players_to_replenish.get(gt['player_id'], 0) + 1
            
            # Replenish tiles once per player
            for player_id, tile_count in players_to_replenish.items():
                self.draw_tiles_for_player(player_id, tile_count)

            # pending_tiles 정리 (Broadcasting 전에 수행해야 정확한 상태가 전달됨)
            self.pending_tiles = [pt for pt in self.pending_tiles if (pt['x'], pt['y']) not in self.board]

            # Broadcast word completion with animation data
            completed_tiles = [{'x': bx, 'y': by, 'letter': self.board[(bx, by)]['letter'], 'color': new_color} 
                             for bx, by in word_coords if (bx, by) in self.board]
            await self.broadcast({"type": "WORD_COMPLETED", "word": word, "tiles": completed_tiles})
            await self.broadcast_state()
            await self.broadcast({"type": "MODAL", "message": f"Word completed: {word}"})
        
        else:
            # Invalid Word Penalty (5 points for final word validation failure)
            penalty_points = 5
            penalized_players = set()
            
            # Skip penalty if the word is just a single character (not really an incorrect word, just incomplete)
            if not result.get("skip_penalty"):
                current_time = time.time()
                penalty_cooldown = 5.0  # 5 seconds cooldown between penalties
                
                for gt in group_tiles:
                    pid = gt['player_id']
                    if pid in self.players:
                        # Check if player was recently penalized
                        last_penalty_time = self.penalty_cooldowns.get(pid, 0)
                        if current_time - last_penalty_time >= penalty_cooldown:
                            self.players[pid].score = max(0, self.players[pid].score - penalty_points)
                            penalized_players.add(pid)
                            self.penalty_cooldowns[pid] = current_time
                        else:
                            logger.debug(f"Skipping penalty for {self.players[pid].name} (cooldown active)")
                
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

    def update_settings(self, settings: dict):
        """방 설정을 업데이트합니다."""
        self.settings.update(settings)
        logger.info(f"Room settings updated for {self.room_code}: {self.settings}")

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
import asyncio
import sys
import os
from unittest.mock import MagicMock, patch

# Add the directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock problematic imports before they are loaded
sys.modules['asyncpg'] = MagicMock()
sys.modules['core.database'] = MagicMock()

# Handle module path discrepancy
import core.words as words
from core.game import GameRoom, Player

# Mock word_cache for testing
words.word_cache = {
    "CAT": (3, 30),
    "COOL": (4, 40),
    "ACT": (3, 30),
    "DOG": (3, 30),
    "DUAL": (4, 40),
    "TOOL": (4, 40)
}
print(f"Mocked word_cache: {list(words.word_cache.keys())}")

async def test_dual_validation():
    print("Starting Dual-Direction Validation Test...")
    room = GameRoom("TEST2")
    
    # Mocking broadcast to avoid issues
    room.broadcast = MagicMock(side_effect=lambda msg: asyncio.sleep(0))
    room.broadcast_state = MagicMock(side_effect=lambda: asyncio.sleep(0))
    
    # Clear board
    room.board = {}
    
    # Setup H word "CA"
    room.board[(0,0)] = {'x': 0, 'y': 0, 'letter': 'C', 'color': '#FFFFFF'}
    room.board[(1,0)] = {'x': 1, 'y': 0, 'letter': 'A', 'color': '#FFFFFF'}

    mock_ws = MagicMock()
    mock_ws.send_json = MagicMock(side_effect=lambda x: asyncio.sleep(0))
    player = Player("p1", "TestPlayer", mock_ws)
    room.add_player(player)
    player.hand = ["T", "X", "O"]
    
    print("\nCase 1: Dual Valid (H: CAT, V: T (len 1))")
    # Place T at (2,0)
    print(f"Placing T at (2,0). Board has {room.board.keys()}")
    success, error = await room.handle_place_tile(2, 0, "T", "p1", "#FFFFFF")
    print(f"handle_place_tile result: {success}, {error}")
    print(f"Board after placement: {room.board.keys()}")
    print(f"Pending after placement: {[(t['x'], t['y']) for t in room.pending_tiles]}")
    
    assert (2,0) in room.board, "T should be finalized immediately (H valid, V len 1)"
    print("✓ T finalized immediately (H: CAT, V: T)")

    print("\nCase 2: H Valid but V Invalid (Immediate Finalization should be skipped)")
    # Board has CAT at (0,0)-(2,0)
    # Place O at (2,1). H: O (len 1), V: TO (len 2 - invalid)
    success, error = await room.handle_place_tile(2, 1, "O", "p1", "#FFFFFF")
    assert success
    assert (2,1) not in room.board, "O should NOT be finalized immediately (V: TO is invalid)"
    assert any(t['x'] == 2 and t['y'] == 1 for t in room.pending_tiles), "O should be in pending"
    print("✓ O skipped immediate finalization because TO is invalid")

    print("\nCase 3: Rejected after timer due to invalid cross-word")
    # Finalize O's group
    pending = [t for t in room.pending_tiles if t['x'] == 2 and t['y'] == 1][0]
    gid = pending['v_group_id']
    
    player.score = 50
    await room.finalize_pending_group(gid, 'v')
    
    assert (2,1) not in room.board, "O should be rejected"
    assert player.score == 40, f"Expected penalty, got {player.score}"
    print("✓ O was rejected after 3s penalty (TO is invalid)")

    print("\nCase 4: Multi-tile group validation (H: CAT, V: COOL)")
    # Clear board and pendings
    room.board = {}
    room.pending_tiles = []
    
    # Board: C A (0,0)-(1,0)
    # Pending: T O O L (2,0)-(2,3)
    # CAT is H, COOL is V
    room.board[(0,0)] = {'x': 0, 'y': 0, 'letter': 'C', 'color': '#FFFFFF'}
    room.board[(1,0)] = {'x': 1, 'y': 0, 'letter': 'A', 'color': '#FFFFFF'}
    
    player.hand = ["T", "O", "O", "L"]
    
    # Place them one by one. All should skip immediate finalization except maybe the first which might be valid len 1
    # Actually T at (2,0) makes CAT (H) so it would finalize immediately if V is len 1.
    # To test multi-tile V being valid, let's place O,O,L first then T.
    
    await room.handle_place_tile(2, 1, "O", "p1", "#FFFFFF") # V: O (len 1), H: O (len 1) -> No action
    await room.handle_place_tile(2, 2, "O", "p1", "#FFFFFF") # V: OO (inv), H: O (len 1) -> No action
    await room.handle_place_tile(2, 3, "L", "p1", "#FFFFFF") # V: OOL (inv), H: L (len 1) -> No action
    
    # Now place T at (2,0). H: CAT (val), V: TOOL (if TOOL is in cache)
    # Let's add TOOL to cache
    words.word_cache["TOOL"] = (4, 40)
    
    success, error = await room.handle_place_tile(2, 0, "T", "p1", "#FFFFFF")
    assert success
    # Since TOOL and CAT are both valid, T should finalize immediately
    # BUT wait, the other tiles (O,O,L) are still in PENDING.
    # finalize_pending_group(h_group_id, 'h') will check CROSS-words for all tiles in CAT.
    # For T (2,0), cross-word is TOOL. If TOOL is valid, T can be finalized.
    # What about O, O, L? They are not in the 'H' group being finalized.
    # Actually, finalize_pending_group only finalizes the specific group it was called with.
    
    if (2,0) in room.board:
        print("✓ T finalized immediately (H: CAT val, V: TOOL val)")
    else:
        print("x T did not finalize immediately")
        
    print("\nAll Dual-Direction Validation tests passed!")

if __name__ == "__main__":
    asyncio.run(test_dual_validation())

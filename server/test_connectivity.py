import asyncio
import sys
import os
from unittest.mock import MagicMock

# Add the directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Mock problematic imports
sys.modules['asyncpg'] = MagicMock()
sys.modules['core.database'] = MagicMock()

import core.words as words
from core.game import GameRoom, Player

# Mock word_cache
words.word_cache = {"CAT": (3, 30), "ACT": (3, 30)}

async def test_connectivity():
    print("Starting Connectivity Rule Verification...")
    room = GameRoom("TEST_CONN")
    
    # Mock broadcast
    room.broadcast = MagicMock(side_effect=lambda msg: asyncio.sleep(0))
    room.broadcast_state = MagicMock(side_effect=lambda: asyncio.sleep(0))
    
    player = Player("p1", "TestPlayer", MagicMock())
    room.add_player(player)
    player.hand = ["C", "A", "T", "X"]
    
    print("\n1. Verify board is initially empty")
    assert len(room.board) == 0, "Board should be empty"
    print("✓ Board is empty")

    print("\n2. Verify first tile can be placed anywhere (e.g., 10, 10)")
    success, error = await room.handle_place_tile(10, 10, "C", "p1")
    assert success, f"First tile failed: {error}"
    assert any(t['x'] == 10 and t['y'] == 10 for t in room.pending_tiles), "C should be in pending"
    print("✓ First tile placed at (10, 10)")

    print("\n3. Verify second tile far away is REJECTED")
    success, error = await room.handle_place_tile(0, 0, "A", "p1")
    assert not success, "Far away tile should have failed"
    assert error == "Tile must be adjacent to existing or pending tiles"
    print("✓ Far away tile rejected correctly")

    print("\n4. Verify tile adjacent to PENDING is ALLOWED")
    success, error = await room.handle_place_tile(11, 10, "A", "p1")
    assert success, f"Adjacent to pending failed: {error}"
    print("✓ Tile adjacent to pending allowed")

    print("\n5. Verify tile adjacent to BOARD (finalized) is ALLOWED")
    # Manually finalize (10,10) to board
    room.board[(10, 10)] = {'x': 10, 'y': 10, 'letter': 'C', 'color': '#FFFFFF'}
    # Clear pending for (10,10)
    room.pending_tiles = [t for t in room.pending_tiles if not (t['x'] == 10 and t['y'] == 10)]
    
    success, error = await room.handle_place_tile(10, 11, "T", "p1")
    assert success, f"Adjacent to board failed: {error}"
    print("✓ Tile adjacent to board allowed")

    print("\nAll Connectivity tests passed!")

if __name__ == "__main__":
    asyncio.run(test_connectivity())

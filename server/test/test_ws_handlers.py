import asyncio
import json
import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocketDisconnect

# Mocking FastAPI and other dependencies
import sys
from types import ModuleType

# Create mock objects for the modules that are hard to import without full environment
core_game = ModuleType("core.game")
core_game.room_manager = MagicMock()
core_game.Player = MagicMock()
sys.modules["core.game"] = core_game

core_auth = ModuleType("core.auth_utils")
core_auth.decode_access_token = MagicMock()
sys.modules["core.auth_utils"] = core_auth

core_logging = ModuleType("core.logging_config")
core_logging.get_logger = MagicMock()
sys.modules["core.logging_config"] = core_logging

# Now import the handler
from websocket.handlers import handle_websocket

async def test_key_error_fix():
    print("Testing START_GAME without x/y (KeyError fix)...")
    ws = AsyncMock()
    ws.query_params = {"room": "TEST"}
    ws.cookies = {}
    
    # Mock room and players
    room = AsyncMock() # Use AsyncMock for the whole room if it has async methods
    room.players = {"user1": MagicMock()}
    room.broadcast = AsyncMock()
    room.broadcast_state = AsyncMock()
    core_game.room_manager.get_or_create_room.return_value = room
    
    # Sequence of messages: START_GAME then something to exit loop
    ws.receive_json.side_effect = [
        {"type": "START_GAME"},
        WebSocketDisconnect() # To break the loop
    ]
    
    try:
        await handle_websocket(ws)
    except WebSocketDisconnect:
        pass
    except KeyError as e:
        print(f"FAILED: Caught unexpected KeyError: {e}")
        return False
    except Exception as e:
        print(f"Caught other: {type(e).__name__}: {e}")

    print("SUCCESS: START_GAME processed without KeyError.")
    return True

async def test_place_message():
    print("Testing PLACE message handling...")
    ws = AsyncMock()
    ws.query_params = {"room": "TEST"}
    ws.cookies = {}
    
    room = AsyncMock()
    room.players = {"user1": MagicMock()}
    room.handle_place_tile = AsyncMock(return_value=(True, None))
    room.broadcast = AsyncMock()
    room.broadcast_state = AsyncMock()
    core_game.room_manager.get_or_create_room.return_value = room
    
    ws.receive_json.side_effect = [
        {"type": "PLACE", "x": 10, "y": 20, "letter": "A", "color": "#ff0000", "hand_index": 0},
        WebSocketDisconnect()
    ]
    
    try:
        await handle_websocket(ws)
    except WebSocketDisconnect:
        pass
    
    # Verify handle_place_tile was called
    room.handle_place_tile.assert_called_with(10, 20, "A", unittest.mock.ANY, "#ff0000", 0)
    print("SUCCESS: PLACE message handled correctly.")
    return True

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_key_error_fix())
    asyncio.run(test_place_message())

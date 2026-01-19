from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from core.words import load_words_to_memory
from api.routes import router as api_router
from websocket.handlers import handle_websocket
from core.database import init_db
from core.game import RoomManager
from core.logging_config import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server is starting up...")
    logger.debug("Initializing database and loading words...")
    await init_db() 
    await load_words_to_memory()
    logger.info("Database and words loaded.")
    yield
    logger.info("Server is shutting down...")

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="../client"), name="static")

app.include_router(api_router)

@app.get("/health")
async def health_check():
    logger.info("Health check requested")
    return {"status": "ok"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    logger.debug(f"New websocket connection attempt from {websocket.client}")
    await handle_websocket(websocket)

# room_manager is managed in core/game.py
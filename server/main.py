from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from core.words import load_words_to_memory
from api.routes import router as api_router
from websocket.handlers import handle_websocket

@asynccontextmanager
async def lifespan(app: FastAPI):
    await load_words_to_memory()
    yield

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="../client"), name="static")

app.include_router(api_router)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_websocket(websocket)
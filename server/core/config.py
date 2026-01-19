import os
from pathlib import Path
from core.logging_config import get_logger

logger = get_logger(__name__)

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
WORDS_JSON_PATH = DATA_DIR / "words.json"

# Server
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

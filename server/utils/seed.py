import json
import asyncio
import asyncpg
from core.logging_config import get_logger
from core.config import WORDS_JSON_PATH
from dotenv import load_dotenv
import os

logger = get_logger(__name__)

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

# data/words.json 파일의 단어들을 DB로 옮기는 함수
# 서버 생성후 최초 1회만 시행하면 됨
async def migrate_words():
    logger.info(f"Loading words from {WORDS_JSON_PATH}...")
    try:
        if not WORDS_JSON_PATH.exists():
            logger.error("Error: words.json not found.")
            return

        with open(WORDS_JSON_PATH, "r") as f:
            word_data = json.load(f)
        
        values = [(word.upper(), info[0], info[1]) for word, info in word_data.items()]
        logger.info(f"Preparing to insert {len(values)} words...")

        conn = await asyncpg.connect(DATABASE_URL)
        try:
            # 테이블 초기화
            await conn.execute("DROP TABLE IF EXISTS dictionary;")
            await conn.execute("""
                CREATE TABLE dictionary (
                    word TEXT PRIMARY KEY,
                    length INTEGER,
                    score INTEGER
                );
            """)

            # Bulk Insert
            # asyncpg copy_records_to_table is very fast for bulk inserts
            await conn.copy_records_to_table(
                'dictionary', 
                records=values, 
                columns=['word', 'length', 'score']
            )

            logger.info(f"Successfully migrated {len(values)} words to the database.")
        finally:
            await conn.close()

    except Exception as e:
        logger.error(f"Error during migration: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_words())
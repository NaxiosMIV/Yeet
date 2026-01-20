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

# 단어들을 DB로 옮기는 함수
async def migrate_words():
    from core.config import KOREAN_WORDS_JSON_PATH
    
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        # 테이블 초기화 (새 스키마 적용)
        logger.info("Initializing dictionary table...")
        await conn.execute("DROP TABLE IF EXISTS dictionary;")
        await conn.execute("""
            CREATE TABLE dictionary (
                word TEXT,
                lang TEXT DEFAULT 'en',
                length INTEGER,
                score INTEGER,
                PRIMARY KEY (word, lang)
            );
        """)

        async def migrate_one_lang(path, lang):
            logger.info(f"Loading {lang} words from {path}...")
            if not path.exists():
                logger.error(f"Error: {path} not found.")
                return

            with open(path, "r", encoding="utf-8") as f:
                word_data = json.load(f)
            
            values = [(word.upper() if lang == 'en' else word, lang, info[0], info[1]) for word, info in word_data.items()]
            logger.info(f"Preparing to insert {len(values)} {lang} words...")

            await conn.copy_records_to_table(
                'dictionary', 
                records=values, 
                columns=['word', 'lang', 'length', 'score']
            )
            logger.info(f"Successfully migrated {len(values)} {lang} words.")

        await migrate_one_lang(WORDS_JSON_PATH, 'en')
        await migrate_one_lang(KOREAN_WORDS_JSON_PATH, 'ko')

    except Exception as e:
        logger.error(f"Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_words())
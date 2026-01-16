import json
import asyncio
import asyncpg
from server.core.config import DATABASE_URL, WORDS_JSON_PATH

async def migrate_words():
    print(f"Loading words from {WORDS_JSON_PATH}...")
    try:
        if not WORDS_JSON_PATH.exists():
            print("Error: words.json not found.")
            return

        with open(WORDS_JSON_PATH, "r") as f:
            word_data = json.load(f)
        
        values = [(word.upper(), info[0], info[1]) for word, info in word_data.items()]
        print(f"Preparing to insert {len(values)} words...")

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

            print(f"Successfully migrated {len(values)} words to the database.")
        finally:
            await conn.close()

    except Exception as e:
        print(f"Error during migration: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_words())
import json
import psycopg2
from psycopg2.extras import execute_values

# DB 연결 설정 (docker-compose 설정 반영)
DB_CONFIG = {
    "dbname": "yeet_db",
    "user": "user",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

def migrate_words():
    conn = None
    try:
        # JSON 파일 로드 (unemployables: [13, 18] 구조)
        with open("words.json", "r") as f:
            word_data = json.load(f)
        
        # 데이터 변환: (단어, 길이, 점수) 튜플 리스트 생성
        values = [(word.upper(), info[0], info[1]) for word, info in word_data.items()]

        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        # 테이블 생성 (기존 테이블 있으면 삭제 후 재생성)
        cur.execute("DROP TABLE IF EXISTS dictionary;")
        cur.execute("""
            CREATE TABLE dictionary (
                word TEXT PRIMARY KEY,
                length INTEGER,
                score INTEGER
            );
        """)

        # Bulk Insert (17만 개를 한 번에 넣기 위해 execute_values 사용)
        query = "INSERT INTO dictionary (word, length, score) VALUES %s"
        execute_values(cur, query, values)

        conn.commit()

    except Exception as e:
        print(f"오류 발생: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    migrate_words()
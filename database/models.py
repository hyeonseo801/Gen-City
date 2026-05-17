import sqlite3
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_tables(conn):
    cursor = conn.cursor()

    # 지하철역
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subway_stations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            line TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL
        )
    """)

    # 학교
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schools (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT,
            lat REAL NOT NULL,
            lng REAL NOT NULL
        )
    """)

    # 공원
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS parks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            area REAL,
            lat REAL NOT NULL,
            lng REAL NOT NULL
        )
    """)

    # 용도지역 규제 테이블 (RAG 레이어)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS zoning_regulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            zone_code TEXT NOT NULL,
            zone_name TEXT NOT NULL,
            building_coverage_ratio REAL NOT NULL,
            floor_area_ratio REAL NOT NULL,
            allowed_uses TEXT NOT NULL,
            restrictions TEXT
        )
    """)

    conn.commit()

if __name__ == "__main__":
    conn = get_connection()
    init_tables(conn)
    print("테이블 생성 완료")
    conn.close()

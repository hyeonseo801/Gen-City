import pandas as pd
import sqlite3
from database.models import get_connection, init_tables


def insert_subway_stations(conn):
    df = pd.read_excel("data/전체_도시철도역사정보_20250930.xlsx")

    # 컬럼명 확인 후 맞게 조정 필요
    df = df[["역사명", "노선명", "역위도", "역경도"]].dropna()
    df.columns = ["name", "line", "lat", "lng"]

    df.to_sql("subway_stations", conn, if_exists="replace", index=False)
    print(f"지하철역 {len(df)}개 삽입 완료")

def insert_schools(conn):
    df = pd.read_csv("data/학교.csv", encoding="utf-8")

    df = df[["학교명", "학교급구분", "위도", "경도"]].dropna()
    df.columns = ["name", "type", "lat", "lng"]

    df.to_sql("schools", conn, if_exists="replace", index=False)
    print(f"학교 {len(df)}개 삽입 완료")

def insert_parks(conn):
    df = pd.read_csv("data/전국도시공원정보표준데이터.csv", encoding="cp949")

    df = df[["공원명", "공원면적", "위도", "경도"]].dropna()
    df.columns = ["name", "area", "lat", "lng"]

    df.to_sql("parks", conn, if_exists="replace", index=False)
    print(f"공원 {len(df)}개 삽입 완료")

def insert_zoning_regulations(conn):
    regulations = [
        ("1종전용주거", "제1종전용주거지역", 50, 100, "단독주택", "공동주택 불가"),
        ("2종전용주거", "제2종전용주거지역", 50, 150, "단독주택, 공동주택", None),
        ("1종일반주거", "제1종일반주거지역", 60, 200, "단독주택, 근린생활시설", None),
        ("2종일반주거", "제2종일반주거지역", 60, 250, "공동주택, 근린생활시설", None),
        ("3종일반주거", "제3종일반주거지역", 50, 300, "공동주택, 근린생활시설", None),
        ("준주거", "준주거지역", 70, 500, "주거+상업 복합", None),
        ("일반상업", "일반상업지역", 80, 1300, "판매, 업무, 숙박", None),
        ("근린상업", "근린상업지역", 70, 900, "판매, 근린생활", None),
    ]

    cursor = conn.cursor()
    cursor.executemany("""
        INSERT OR REPLACE INTO zoning_regulations
        (zone_code, zone_name, building_coverage_ratio, floor_area_ratio, allowed_uses, restrictions)
        VALUES (?, ?, ?, ?, ?, ?)
    """, regulations)
    conn.commit()
    print("용도지역 규제 데이터 삽입 완료 (수치 검증 필요)")

if __name__ == "__main__":
    conn = get_connection()
    init_tables(conn)
    insert_subway_stations(conn)
    insert_schools(conn)
    insert_parks(conn)
    insert_zoning_regulations(conn)
    conn.close()
    print("DB 초기화 완료")

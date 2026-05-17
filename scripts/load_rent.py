"""
국토부 전월세 실거래가 CSV → SQLite (rent_by_dong 테이블)

사용법:
  python scripts/load_rent.py                  # data/rent.csv 기본 경로
  python scripts/load_rent.py data/rent2.csv   # 경로 직접 지정

CSV 컬럼(국토부 표준):
  법정동코드, 법정동, 지번, 건물명, 전월세구분, 전용면적, 보증금(만원), 월세(만원), 계약년, 계약월
"""

import sys
import os
import re
import sqlite3
import pandas as pd

# 프로젝트 루트에서 실행해도 config 임포트 가능하도록
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import DB_PATH

CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/rent.csv"

# 동 이름 정규화: '성수동1가' → '성수동', '봉천동' → '봉천동'
def normalize_dong(name: str) -> str:
    if not isinstance(name, str):
        return ""
    name = name.strip()
    # 말미의 숫자+가/나/다 제거 (예: 1가, 2가, 1동)
    name = re.sub(r"\d+[가나다라동]?$", "", name).strip()
    return name


def load(csv_path: str):
    print(f"CSV 읽는 중: {csv_path}")
    try:
        df = pd.read_csv(csv_path, encoding="utf-8")
    except UnicodeDecodeError:
        df = pd.read_csv(csv_path, encoding="cp949")

    # 컬럼명 공백 제거
    df.columns = df.columns.str.strip()

    # 필수 컬럼 확인
    required = {"전월세구분", "법정동", "전용면적", "보증금(만원)", "월세(만원)"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV에 필요한 컬럼이 없습니다: {missing}\n실제 컬럼: {list(df.columns)}")

    # 월세만 필터
    df = df[df["전월세구분"].str.strip() == "월세"].copy()
    print(f"월세 거래 건수: {len(df)}")

    # 숫자 변환 (쉼표 포함 문자열 대비)
    for col in ["보증금(만원)", "월세(만원)", "전용면적"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "").str.strip(),
            errors="coerce"
        )

    df = df.dropna(subset=["보증금(만원)", "월세(만원)", "전용면적"])

    # 실질 월세 = 월세 + 보증금 × 0.0004  (연 4.8% ÷ 12)
    df["effective_monthly_rent"] = df["월세(만원)"] + df["보증금(만원)"] * 0.0004

    # 동 이름 정규화
    df["dong_name"] = df["법정동"].apply(normalize_dong)
    df = df[df["dong_name"] != ""]

    # 동별 집계
    agg = (
        df.groupby("dong_name")
        .agg(
            avg_monthly_rent=("effective_monthly_rent", "mean"),
            avg_area=("전용면적", "mean"),
            count=("effective_monthly_rent", "count"),
        )
        .reset_index()
    )

    print(f"동 집계 결과: {len(agg)}개 동")

    # DB 저장
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rent_by_dong (
            dong_name TEXT PRIMARY KEY,
            avg_monthly_rent REAL,
            avg_area REAL,
            count INTEGER
        )
    """)
    # 기존 데이터 교체
    conn.execute("DELETE FROM rent_by_dong")
    agg.to_sql("rent_by_dong", conn, if_exists="append", index=False)
    conn.commit()
    conn.close()

    print("rent_by_dong 테이블 저장 완료")
    print(agg.sort_values("count", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    load(CSV_PATH)

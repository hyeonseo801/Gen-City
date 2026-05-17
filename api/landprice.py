from flask import Blueprint, request, jsonify
import requests
from database.models import get_connection
import os

landprice_bp = Blueprint("landprice", __name__)

KAKAO_API_KEY = os.getenv("KAKAO_API_KEY")

def get_pnu(lat, lng):
    """카카오 역지오코딩 → PNU 생성"""
    url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"x": lng, "y": lat, "input_coord": "WGS84"}

    res = requests.get(url, headers=headers, params=params).json()

    # region_type == 'B' 가 법정동 코드
    for doc in res.get("documents", []):
        if doc.get("region_type") == "B":
            bjd_code = doc["code"]  # 10자리 법정동코드
            return bjd_code
    return None

@landprice_bp.route("/landprice")
def get_landprice():
    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "lat, lng 파라미터 필요"}), 400

    bjd_code = get_pnu(lat, lng)
    if not bjd_code:
        return jsonify({"land_price": None})

    # 법정동코드로 해당 동 평균 공시지가 조회
    conn = get_connection()
    row = conn.execute("""
        SELECT AVG(land_price) as avg_price
        FROM land_prices
        WHERE pnu LIKE ?
    """, (bjd_code + "%",)).fetchone()
    conn.close()

    avg_price = int(row["avg_price"]) if row and row["avg_price"] else None
    return jsonify({"land_price": avg_price})

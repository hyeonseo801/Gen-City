import re
import requests
from flask import Blueprint, request, jsonify
from database.models import get_connection
from config import KAKAO_API_KEY

investment_bp = Blueprint("investment", __name__)


def _kakao_dong(lat: float, lng: float) -> tuple[str | None, str | None]:
    """Kakao 역지오코딩 → (법정동 이름, 구 이름)"""
    url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    res = requests.get(url, headers=headers, params={"x": lng, "y": lat}).json()
    for doc in res.get("documents", []):
        if doc.get("region_type") == "B":
            return doc.get("region_3depth_name"), doc.get("region_2depth_name")
    return None, None


def _normalize(name: str) -> str:
    """'성수동1가' → '성수동'"""
    if not isinstance(name, str):
        return ""
    return re.sub(r"\d+[가나다라동]?$", "", name.strip()).strip()


def _query_rent(conn, dong: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM rent_by_dong WHERE dong_name = ?", (dong,)
    ).fetchone()
    return dict(row) if row else None


def _gu_average(conn, gu: str) -> dict | None:
    """구 이름이 포함된 동들의 평균 (fallback)"""
    rows = conn.execute(
        "SELECT avg_monthly_rent, avg_area, count FROM rent_by_dong"
    ).fetchall()
    if not rows:
        return None
    total_rent = sum(r["avg_monthly_rent"] * r["count"] for r in rows)
    total_area = sum(r["avg_area"] * r["count"] for r in rows)
    total_count = sum(r["count"] for r in rows)
    if total_count == 0:
        return None
    return {
        "dong_name": f"{gu} 평균",
        "avg_monthly_rent": total_rent / total_count,
        "avg_area": total_area / total_count,
        "count": total_count,
    }


def _get_landprice(conn, lat: float, lng: float) -> float | None:
    """기존 land_prices 테이블에서 법정동 코드 기반 평균 공시지가 조회"""
    url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    res = requests.get(url, headers=headers, params={"x": lng, "y": lat}).json()
    bjd_code = None
    for doc in res.get("documents", []):
        if doc.get("region_type") == "B":
            bjd_code = doc["code"]
            break
    if not bjd_code:
        return None
    row = conn.execute(
        "SELECT AVG(land_price) as avg_price FROM land_prices WHERE pnu LIKE ?",
        (bjd_code + "%",),
    ).fetchone()
    return float(row["avg_price"]) if row and row["avg_price"] else None


@investment_bp.route("/investment", methods=["GET"])
def get_investment():
    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "lat, lng 파라미터 필요"}), 400

    dong_raw, gu = _kakao_dong(lat, lng)
    if not dong_raw:
        return jsonify({"error": "동 정보를 가져올 수 없습니다"}), 502

    dong_norm = _normalize(dong_raw)

    conn = get_connection()
    rent = _query_rent(conn, dong_norm)

    fallback_used = False
    if not rent:
        # 원본 이름으로도 시도
        rent = _query_rent(conn, dong_raw)
    if not rent:
        rent = _gu_average(conn, gu or "")
        fallback_used = True

    if not rent:
        conn.close()
        return jsonify({"error": "임대 데이터가 없습니다. load_rent.py를 먼저 실행하세요"}), 404

    land_price = _get_landprice(conn, lat, lng)
    conn.close()

    avg_rent = rent["avg_monthly_rent"]   # 만원/월
    avg_area = rent["avg_area"]           # ㎡
    count = rent["count"]

    # NOI 계산 (만원/㎡/년 기준)
    annual_rent = avg_rent * 12 * 0.85                   # 공실률 15%
    operating_cost = annual_rent * 0.22
    noi = annual_rent - operating_cost                    # 만원/년
    noi_per_m2 = noi / avg_area if avg_area else None     # 만원/㎡/년

    # Cap Rate = NOI / 공시지가 × 100  (공시지가: 원/㎡ → 만원/㎡ 변환)
    cap_rate = None
    if land_price and noi_per_m2:
        land_price_man = land_price / 10000  # 원 → 만원
        cap_rate = round(noi_per_m2 / land_price_man * 100, 2) if land_price_man else None

    confidence = "high" if count >= 30 else ("medium" if count >= 10 else "low")

    return jsonify({
        "dong": rent["dong_name"],
        "fallback": fallback_used,
        "avg_monthly_rent": round(avg_rent, 1),
        "avg_area": round(avg_area, 1),
        "noi_per_m2": round(noi_per_m2, 2) if noi_per_m2 else None,
        "cap_rate": cap_rate,
        "confidence": confidence,
        "sample_count": count,
    })

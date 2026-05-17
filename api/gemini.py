from flask import Blueprint, request, jsonify
import sqlite3
from google import genai
from config import GEMINI_API_KEY, DB_PATH

gemini_bp = Blueprint("gemini", __name__)
client = genai.Client(api_key=GEMINI_API_KEY)

def get_zoning_regulation(zone_name):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM zoning_regulations
        WHERE zone_name LIKE ?
    """, (f"%{zone_name}%",))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def build_prompt(data, goal, scores=None, address=None):
    infra = data.get("infrastructure", {})
    land = data.get("landprice", {})
    hospital = data.get("infrastructure", {}).get("hospitals", {})
    zone_name = data.get("landuse", {}).get("zone_name", "알 수 없음")
    reg = get_zoning_regulation(zone_name)

    reg_text = ""
    if reg:
        reg_text = f"""
용도지역: {reg['zone_name']}
건폐율 상한: {reg['building_coverage_ratio']}%
용적률 상한: {reg['floor_area_ratio']}%
허용 용도: {reg['allowed_uses']}
제한 사항: {reg.get('restrictions') or '없음'}
"""
    else:
        reg_text = f"용도지역: {zone_name} (규제 데이터 없음)"

    context_text = ""
    if address:
        context_text = f"""
[부지 위치 및 지역 맥락]
주소: {address}
※ 위 주소를 기반으로 다음을 반드시 분석에 포함하세요:
- 이 동네(행정동/법정동)의 지역 정체성과 특성 (예: 교육특구, 상업중심, 주거밀집 등)
- 해당 지역의 역사적 맥락과 현재 도시적 위상
- 주변 지역과의 관계 (인접 상권, 생활권 등)
- 이 맥락을 고려했을 때 개발 목표의 적합성 평가
"""

    score_text = ""
    if scores:
        score_text = f"""
[부지 종합 점수: {scores.get('total', 0)}/100]
- 교통 접근성: {scores.get('transit', 0)}/25
- 교육 환경: {scores.get('edu', 0)}/20
- 생활 편의: {scores.get('life', 0)}/20
- 자연 환경: {scores.get('nature', 0)}/15
- 토지 개발가치: {scores.get('land', 0)}/20
  (공시지가 {land.get('land_price', '정보없음')}원/㎡ 기준, 낮을수록 개발 여지 큼)
"""

    prompt = f"""
당신은 도시계획 전문가입니다. 아래 부지 데이터를 분석해 토지이용계획을 추천해주세요.

{context_text}
[규제 정보]
{reg_text}
{score_text}
[인프라 분석]
- 반경 내 지하철역: {infra.get('subway', {}).get('count', 0)}개
- 반경 내 학교: {infra.get('schools', {}).get('count', 0)}개
- 반경 내 공원: {infra.get('parks', {}).get('count', 0)}개
- 반경 내 병원: {hospital.get('count', 0)}개

[공시지가]
- {land.get('land_price', '정보 없음')}원/㎡ (기준연도: {land.get('year', '-')})

[개발 목표]
{goal}

위 조건을 바탕으로 다음을 작성해주세요:
1. 부지 종합 평가 (3줄 이내)
2. 추천 토지이용계획 (용도, 규모, 이유)
3. 기대 효과
4. 주의사항 및 보완점

반드시 규제 범위(건폐율/용적률) 안에서 추천하세요.
"""
    return prompt

@gemini_bp.route("/recommend", methods=["POST"])
def recommend():
    body = request.get_json()
    goal = body.get("goal", "")
    data = body.get("data", {})

    if not goal or not data:
        return jsonify({"error": "goal, data 필요"}), 400

    scores = body.get("scores")
    address = body.get("address", "")
    prompt = build_prompt(data, goal, scores, address)

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    return jsonify({
        "recommendation": response.text,
        "zone": data.get("landprice", {}).get("zone", "알 수 없음")
    })

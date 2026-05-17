from flask import Blueprint, request, jsonify
import requests
from config import KAKAO_API_KEY

geocode_bp = Blueprint("geocode", __name__)

@geocode_bp.route("/geocode", methods=["GET"])
def reverse_geocode():
    lat = request.args.get("lat")
    lng = request.args.get("lng")

    if not lat or not lng:
        return jsonify({"error": "lat, lng 파라미터 필요"}), 400

    url = "https://dapi.kakao.com/v2/local/geo/coord2regioncode.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"x": lng, "y": lat}

    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    if not data.get("documents"):
        return jsonify({"error": "주소 변환 실패"}), 404

    region = data["documents"][0]
    return jsonify({
        "address": region.get("address_name"),
        "region_1": region.get("region_1depth_name"),
        "region_2": region.get("region_2depth_name"),
        "region_3": region.get("region_3depth_name"),
    })

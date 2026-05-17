from flask import Blueprint, request, jsonify
import sqlite3
import math
from config import DB_PATH, RADIUS_PRIMARY, RADIUS_SECONDARY, RADIUS_TERTIARY

infra_bp = Blueprint("infrastructure", __name__)

def haversine(lat1, lng1, lat2, lng2):
    R = 6371000  # 지구 반지름 (미터)
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def query_nearby(conn, table, lat, lng, radius):
    cursor = conn.cursor()
    cursor.execute(f"SELECT *, lat, lng FROM {table}")
    rows = cursor.fetchall()
    nearby = []
    for row in rows:
        dist = haversine(lat, lng, row["lat"], row["lng"])
        if dist <= radius:
            nearby.append({"name": row["name"], "distance": round(dist)})
    return sorted(nearby, key=lambda x: x["distance"])

def query_hospitals_nearby(conn, lat, lng, radius):
    cursor = conn.cursor()
    cursor.execute("SELECT name, lat, lng, type FROM hospitals")
    rows = cursor.fetchall()
    nearby = []
    for row in rows:
        dist = haversine(lat, lng, row["lat"], row["lng"])
        if dist <= radius:
            nearby.append({"name": row["name"], "distance": round(dist), "type": row["type"]})
    return sorted(nearby, key=lambda x: x["distance"])

def get_radius_result(conn, table, lat, lng):
    for radius in [RADIUS_PRIMARY, RADIUS_SECONDARY, RADIUS_TERTIARY]:
        result = query_nearby(conn, table, lat, lng, radius)
        if result:
            return result, radius
    return [], RADIUS_TERTIARY

def get_hospital_radius_result(conn, lat, lng):
    for radius in [RADIUS_PRIMARY, RADIUS_SECONDARY, RADIUS_TERTIARY]:
        result = query_hospitals_nearby(conn, lat, lng, radius)
        if result:
            return result, radius
    return [], RADIUS_TERTIARY

MAJOR_TYPES = {"종합병원", "상급종합", "병원"}
GENERAL_TYPES = {"의원", "치과의원", "한의원"}

def build_type_breakdown(hospitals):
    major, general, special = [], [], []
    for h in hospitals:
        t = h.get("type", "")
        if t in MAJOR_TYPES:
            major.append(h)
        elif t in GENERAL_TYPES:
            general.append(h)
        else:
            special.append(h)
    return {"major": major, "general": general, "special": special}

@infra_bp.route("/infrastructure", methods=["GET"])
def analyze_infrastructure():
    lat = float(request.args.get("lat"))
    lng = float(request.args.get("lng"))

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    subway, subway_radius = get_radius_result(conn, "subway_stations", lat, lng)
    schools, school_radius = get_radius_result(conn, "schools", lat, lng)
    schools_500m = query_nearby(conn, "schools", lat, lng, 500)
    parks, park_radius = get_radius_result(conn, "parks", lat, lng)
    parks_500m = query_nearby(conn, "parks", lat, lng, 500)

    hospitals, hospital_radius = get_hospital_radius_result(conn, lat, lng)
    hospitals_500m = query_hospitals_nearby(conn, lat, lng, 500)

    conn.close()

    return jsonify({
        "subway": {
            "count": len(subway),
            "radius_used": subway_radius,
            "nearest": subway[:3]
        },
        "schools": {
            "count": len(schools),
            "radius_used": school_radius,
            "nearest": schools[:3],
            "count_500m": len(schools_500m)
        },
        "parks": {
            "count": len(parks),
            "radius_used": park_radius,
            "nearest": parks[:3],
            "count_500m": len(parks_500m)
        },
        "hospitals": {
            "count": len(hospitals),
            "radius_used": hospital_radius,
            "nearest": hospitals[:3],
            "type_breakdown": build_type_breakdown(hospitals),
            "count_500m": len(hospitals_500m)
        }
    })

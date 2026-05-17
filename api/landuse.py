from flask import Blueprint, request, jsonify
import shapefile
from shapely.geometry import Point, shape
from pyproj import Transformer
import os

landuse_bp = Blueprint("landuse", __name__)

# 서버 시작 시 SHP 로딩
_polygons = []  # [(shapely_polygon, zone_name), ...]

def _load_shp():
    global _polygons
    shp_path = os.path.join(os.path.dirname(__file__), "..", "data", "UPIS_C_UQ111.shp")

    # EPSG:5174 → EPSG:4326 변환기
    transformer = Transformer.from_crs("EPSG:5174", "EPSG:4326", always_xy=True)

    sf = shapefile.Reader(shp_path, encoding="cp949")
    fields = [f[0] for f in sf.fields[1:]]  # DeletionFlag 제외
    dgm_idx = fields.index("DGM_NM")

    for sr in sf.shapeRecords():
        zone_name = sr.record[dgm_idx]
        geom = shape(sr.shape.__geo_interface__)

        # 좌표 변환: 5174 → 4326
        if geom.geom_type == "Polygon":
            exterior = [transformer.transform(x, y) for x, y in geom.exterior.coords]
            from shapely.geometry import Polygon
            poly = Polygon(exterior)
        elif geom.geom_type == "MultiPolygon":
            from shapely.geometry import MultiPolygon, Polygon
            polys = []
            for p in geom.geoms:
                exterior = [transformer.transform(x, y) for x, y in p.exterior.coords]
                polys.append(Polygon(exterior))
            poly = MultiPolygon(polys)
        else:
            continue

        _polygons.append((poly, zone_name))

    print(f"용도지역 폴리곤 {len(_polygons)}개 로딩 완료")

_load_shp()

@landuse_bp.route("/landuse")
def get_landuse():
    try:
        lat = float(request.args.get("lat"))
        lng = float(request.args.get("lng"))
    except (TypeError, ValueError):
        return jsonify({"error": "lat, lng 파라미터 필요"}), 400

    point = Point(lng, lat)  # shapely는 (x, y) = (lng, lat)

    for poly, zone_name in _polygons:
        if poly.contains(point):
            return jsonify({"zone_name": zone_name})

    return jsonify({"zone_name": "미지정"})

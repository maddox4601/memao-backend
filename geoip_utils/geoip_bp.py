from flask import Blueprint, request, jsonify
import geoip2.database
import os

geoip_bp = Blueprint('geoip', __name__)
# 确保路径正确（按你项目实际放置的路径写）
db_path = os.path.join(os.path.dirname(__file__), 'GeoLite2-Country.mmdb')
reader = geoip2.database.Reader(db_path)

@geoip_bp.route('/api/get-country-code', methods=['GET'])
def get_country_code():
    ip = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
    try:
        response = reader.country(ip)
        country_code = response.country.iso_code or 'UNKNOWN'
    except Exception as e:
        print(f"GeoIP 查询失败: {e}")
        country_code = 'UNKNOWN'
    return jsonify({'country_code': country_code})

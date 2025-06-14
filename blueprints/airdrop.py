from flask import Blueprint, request, jsonify
from models import AirdropAddress
from extensions import db  # 你存放db实例的地方
from datetime import datetime, timezone
import re

airdrop_bp = Blueprint('airdrop', __name__, url_prefix='/api/airdrop')

@airdrop_bp.route('/collect_address', methods=['POST'])
def collect_address():
    data = request.get_json() or {}
    address = data.get('address', '').strip()
    comment = data.get('comment', '').strip()

    # 简单地址格式校验
    if not address or not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return jsonify({'success': False, 'message': '钱包地址无效'}), 400

    # 查询是否已存在
    existing = AirdropAddress.query.filter_by(address=address).first()
    if existing:
        return jsonify({'success': False, 'message': '该地址已参加过空投活动'}), 200

    try:
        new_entry = AirdropAddress(
            address=address,
            comment=comment,
            submitted_at=datetime.now(timezone.utc)
        )
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({'success': True, 'message': '地址提交成功'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'提交失败: {str(e)}'}), 500


@airdrop_bp.route('/addresses', methods=['GET'])
def list_addresses():
    try:
        addresses = AirdropAddress.query.all()
        result = [{
            'address': addr.address,
            'comment': addr.comment,
            'submitted_at': addr.submitted_at.isoformat() if addr.submitted_at else None
        } for addr in addresses]
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败: {str(e)}'}), 500

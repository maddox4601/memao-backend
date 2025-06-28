from flask import Blueprint, request, jsonify
from models import AirdropAddress, AirdropConfig
from extensions import db
from datetime import datetime, timezone
from utils.blockchain_batch_airdrop import blockchain_batch_airdrop
from utils.auth_utils import jwt_required
import re

airdrop_bp = Blueprint('airdrop', __name__, url_prefix='/api/airdrop')


# 🟢 用户提交地址接口
@airdrop_bp.route('/collect_address', methods=['POST'])
def collect_address():
    data = request.get_json() or {}
    address = data.get('address', '').strip()
    comment = data.get('comment', '').strip()

    # Validate wallet address format
    if not address or not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return jsonify({'success': False, 'message': 'Invalid wallet address'}), 400

    # Check if the address already exists
    existing = AirdropAddress.query.filter_by(address=address).first()
    if existing:
        return jsonify({'success': False, 'message': 'This address has already participated in the airdrop'}), 200

    try:
        new_entry = AirdropAddress(
            address=address,
            comment=comment,
            submitted_at=datetime.now(timezone.utc)
        )
        db.session.add(new_entry)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Address submitted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'Submission failed: {str(e)}'}), 500


# Admin管理员手动发放接口

@airdrop_bp.route('/distribute', methods=['POST'])
@jwt_required
def manual_distribute():
    try:
        config = AirdropConfig.query.first()
        batch_size = config.batch_size if config else 20
        airdrop_amount = int(config.airdrop_amount) if config and config.airdrop_amount else 0

        pending_addresses = AirdropAddress.query.filter_by(is_distributed=False).limit(batch_size).all()

        if not pending_addresses:
            return jsonify({'success': False, 'message': 'No addresses to distribute.'}), 200

        addresses = [user.address for user in pending_addresses]
        amounts = [airdrop_amount for _ in pending_addresses]  # 所有地址都用统一数量

        # 调用链上空投合约
        success = blockchain_batch_airdrop(addresses, amounts)

        if success:
            for user in pending_addresses:
                user.is_distributed = True
                user.distributed_at = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({'success': True, 'message': f'{len(pending_addresses)} addresses processed successfully.'}), 200
        else:
            return jsonify({'success': False, 'message': 'Blockchain transaction failed.'}), 500

    except Exception as e:
        return jsonify({'success': False, 'message': f'Distribution failed: {str(e)}'}), 500



# 查询地址列表接口（含发放状态）
@airdrop_bp.route('/addresses', methods=['GET'])
def list_addresses():
    try:
        addresses = AirdropAddress.query.all()
        result = [{
            'address': addr.address,
            'comment': addr.comment,
            'submitted_at': addr.submitted_at.isoformat() if addr.submitted_at else None,
            'is_distributed': addr.is_distributed,
            'distributed_at': addr.distributed_at.isoformat() if addr.distributed_at else None
        } for addr in addresses]
        return jsonify({'success': True, 'data': result}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Query failed: {str(e)}'}), 500


# Admin配置接口：控制定时任务开关和批量数量
@airdrop_bp.route('/config', methods=['POST'])
@jwt_required
def update_config():
    try:
        data = request.get_json() or {}
        is_enabled = data.get('is_task_enabled')
        batch_size = data.get('batch_size')
        airdrop_amount = data.get('airdrop_amount')  # 新增字段

        config = AirdropConfig.query.first()
        if not config:
            config = AirdropConfig()

        if is_enabled is not None:
            config.is_task_enabled = bool(is_enabled)
        if batch_size:
            config.batch_size = int(batch_size)
        if airdrop_amount is not None:
            # 字符串转 int 存数据库
            config.airdrop_amount = int(airdrop_amount)

        db.session.add(config)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully.',
            'data': {
                'is_task_enabled': config.is_task_enabled,
                'batch_size': config.batch_size,
                'airdrop_amount': str(config.airdrop_amount or 0)  # 返回给前端
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Configuration update failed: {str(e)}'}), 500

# Admin 查询当前配置接口
@airdrop_bp.route('/config', methods=['GET'])
def get_config():
    try:
        config = AirdropConfig.query.first()
        if not config:
            return jsonify({'success': True, 'data': {
                'is_task_enabled': True,
                'batch_size': 20,
                'airdrop_amount': '0'  # 默认返回字符串，防止前端 BigInt 出错
            }}), 200

        return jsonify({'success': True, 'data': {
            'is_task_enabled': config.is_task_enabled,
            'batch_size': config.batch_size,
            'airdrop_amount': str(config.airdrop_amount or 0)  # 一定要转字符串，兼容大数
        }}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to retrieve configuration: {str(e)}'}), 500


#查询空投领取状态
@airdrop_bp.route('/status', methods=['GET'])
def claim_status():
    address = request.args.get('address', '').strip()
    if not address or not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return jsonify({'success': False, 'message': 'Invalid wallet address'}), 400

    entry = AirdropAddress.query.filter_by(address=address).first()
    if not entry:
        # 地址没提交过，默认未发放
        return jsonify({'success': True, 'data': {'is_distributed': False}}), 200

    return jsonify({'success': True, 'data': {'is_distributed': entry.is_distributed}}), 200

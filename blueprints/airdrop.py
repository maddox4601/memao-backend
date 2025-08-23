from decimal import Decimal
from flask import Blueprint, request, jsonify
from models import AirdropAddress, AirdropConfig,UserPointsAccount,PointsHistory, WalletUser
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


def distribute_points_to_users(addresses, base_reward):
    from sqlalchemy.exc import SQLAlchemyError
    import logging

    for addr in addresses:
        try:
            user = WalletUser.query.filter_by(wallet_address=addr).first()
            if not user:
                logging.warning(f"User not found for address: {addr}")
                continue

            points_account = (
                UserPointsAccount.query
                .filter_by(wallet_user_id=user.id)
                .with_for_update()
                .first()
            )
            if not points_account:
                points_account = UserPointsAccount(wallet_user_id=user.id, total_points=Decimal('0'), consecutive_days=0)
                db.session.add(points_account)
                db.session.flush()

            points_account.total_points = (points_account.total_points or Decimal('0')) + base_reward

            points_history = PointsHistory(
                wallet_user_id=user.id,
                change_type="airdrop_points",
                change_amount=base_reward,
                created_at=datetime.now(timezone.utc),
                description=f"Airdrop points granted: {base_reward}"
            )
            db.session.add(points_history)

        except SQLAlchemyError as e:
            logging.error(f"Failed to distribute points to {addr}: {str(e)}")
            db.session.rollback()  # 回滚当前事务，继续处理其他用户
    try:
        db.session.commit()
    except SQLAlchemyError as e:
        logging.error(f"Failed to commit points distribution transaction: {str(e)}")
        db.session.rollback()


# Admin管理员手动发放接口
@airdrop_bp.route('/distribute', methods=['POST'])
def manual_distribute():
    try:
        config = AirdropConfig.query.first()
        if not config:
            return jsonify({'success': False, 'message': 'Airdrop configuration not found.'}), 400

        batch_size = config.batch_size if config.batch_size else 20
        airdrop_amount = int(config.airdrop_amount) if config.airdrop_amount else 0
        distribution_type = config.distribution_type or "points"

        # 查询待发放地址
        pending_addresses = AirdropAddress.query.filter_by(is_distributed=False).limit(batch_size).all()
        if not pending_addresses:
            return jsonify({'success': False, 'message': 'No addresses to distribute.'}), 200

        if distribution_type == "points":
            # 积分发放逻辑
            addresses = [user.address for user in pending_addresses]
            # 这里假设airdrop_amount是字符串类型wei，转换成Decimal积分
            base_reward = Decimal(airdrop_amount) / Decimal(1e18)

            distribute_points_to_users(addresses, base_reward)
            for user in pending_addresses:
                # 这里可以调用积分发放相关函数，比如发积分给 user.address
                user.is_distributed = True
                user.distributed_at = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({'success': True, 'message': f'{len(pending_addresses)} addresses distributed points successfully.'}), 200

        elif distribution_type == "contract":
            # 合约发放逻辑
            addresses = [user.address for user in pending_addresses]
            amounts = [airdrop_amount for _ in pending_addresses]  # 统一数量

            # 调用链上空投合约函数，示例调用
            success = blockchain_batch_airdrop(addresses, amounts)
            if success:
                for user in pending_addresses:
                    user.is_distributed = True
                    user.distributed_at = datetime.now(timezone.utc)
                db.session.commit()
                return jsonify({'success': True, 'message': f'{len(pending_addresses)} addresses distributed tokens successfully.'}), 200
            else:
                return jsonify({'success': False, 'message': 'Blockchain transaction failed.'}), 500

        else:
            return jsonify({'success': False, 'message': f'Unknown distribution type: {distribution_type}'}), 400

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
        airdrop_amount = data.get('airdrop_amount')  # 字符串形式
        distribution_type = data.get('distribution_type')  # 新增字段

        config = AirdropConfig.query.first()
        if not config:
            config = AirdropConfig()

        if is_enabled is not None:
            config.is_task_enabled = bool(is_enabled)
        if batch_size is not None:
            config.batch_size = int(batch_size)
        if airdrop_amount is not None:
            config.airdrop_amount = int(airdrop_amount)  # 转为 int 存储
        if distribution_type in ['points', 'contract']:
            config.distribution_type = distribution_type

        db.session.add(config)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully.',
            'data': {
                'is_task_enabled': config.is_task_enabled,
                'batch_size': config.batch_size,
                'airdrop_amount': str(config.airdrop_amount or 0),
                'distribution_type': config.distribution_type
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': f'Configuration update failed: {str(e)}'}), 500


@airdrop_bp.route('/config', methods=['GET'])
def get_config():
    try:
        config = AirdropConfig.query.first()
        if not config:
            return jsonify({'success': True, 'data': {
                'is_task_enabled': True,
                'batch_size': 20,
                'airdrop_amount': '0',
                'distribution_type': 'points'
            }}), 200

        return jsonify({'success': True, 'data': {
            'is_task_enabled': config.is_task_enabled,
            'batch_size': config.batch_size,
            'airdrop_amount': str(config.airdrop_amount or 0),
            'distribution_type': config.distribution_type
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

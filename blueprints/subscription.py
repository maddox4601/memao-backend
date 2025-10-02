from flask import Blueprint, jsonify, request
from models import VIPSubscription, WalletUser
from extensions import db
from datetime import datetime,timedelta

membership_bp = Blueprint('membership', __name__, url_prefix='/api/membership')

@membership_bp.route('/status', methods=['GET'])
def get_membership_status():
    wallet_address = request.args.get('wallet')
    if not wallet_address:
        return jsonify({"error": "wallet parameter required"}), 400

    # 查询钱包用户
    wallet_user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not wallet_user:
        return jsonify({"subscribed": False, "expire_at": None})

    # 查询最新有效会员订阅
    subscription = VIPSubscription.query.filter(
        VIPSubscription.wallet_user_id == wallet_user.id,
        VIPSubscription.is_active == True,
        VIPSubscription.end_date > datetime.utcnow()
    ).order_by(VIPSubscription.end_date.desc()).first()

    if subscription:
        return jsonify({
            "subscribed": True,
            "expire_at": subscription.end_date.isoformat()
        })
    else:
        return jsonify({
            "subscribed": False,
            "expire_at": None
        })


@membership_bp.route('/pay', methods=['POST'])
def record_payment():
    data = request.json
    wallet_address = data.get('wallet')
    tx_hash = data.get('tx_hash')  # 可选，用于链上验证
    duration_days = data.get('duration_days', 30)

    if not wallet_address:
        return jsonify({"error": "wallet required"}), 400

    wallet_user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not wallet_user:
        return jsonify({"error": "wallet not found"}), 404

    # 查询最新会员订阅
    subscription = VIPSubscription.query.filter_by(wallet_user_id=wallet_user.id).order_by(VIPSubscription.end_date.desc()).first()

    if subscription:
        subscription.extend_subscription(duration_days)
        subscription.tx_hash = tx_hash
    else:
        now = datetime.utcnow()
        subscription = VIPSubscription(
            wallet_user_id=wallet_user.id,
            start_date=now,
            end_date=now + timedelta(days=duration_days),
            is_active=True,
            tx_hash=tx_hash
        )
        db.session.add(subscription)

    db.session.commit()

    return jsonify(subscription.to_dict())

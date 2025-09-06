from flask import Blueprint, request, jsonify
from datetime import datetime
from decimal import Decimal, getcontext
from extensions import db
from models import WalletUser, MiningHistory,UserPointsAccount,PointsHistory
from utils.mining_service import calculate_user_weight, calculate_reward
from sqlalchemy.exc import SQLAlchemyError

mining_bp = Blueprint('mining', __name__,url_prefix='/api/mining')

getcontext().prec = 30  # 设置高精度环境
@mining_bp.route('/start', methods=['POST'])
def mining_start():
    wallet_address = request.json.get('wallet_address')
    if not wallet_address:
        return jsonify({"error": "wallet_address is required"}), 400

    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    last = MiningHistory.query.filter_by(wallet_user_id=user.id, is_settled=False)\
        .order_by(MiningHistory.mined_at.desc()).first()

    if last and (not last.end_time or (datetime.utcnow() - last.mined_at).total_seconds() < 86400):
        return jsonify({"error": "Mining already in progress"}), 400

    # weight = user.daily_weight if hasattr(user, 'daily_weight') else calculate_user_weight(user)

    weight = user.daily_weight if (
                hasattr(user, 'daily_weight') and user.daily_weight is not None) else calculate_user_weight(user)
    print(f"[DEBUG] weight: {weight}")

    # 提取实际的权重值
    if isinstance(weight, tuple) and len(weight) > 0:
        weight_value = weight[0]  # 取元组的第一个元素（权重值）
    else:
        weight_value = weight

    print(f"[DEBUG] weight: {weight_value}")

    if weight_value is None:
        weight = 0

    mining = MiningHistory(
        wallet_user_id=user.id,
        mined_at=datetime.utcnow(),
        weight_snapshot=weight_value
    )
    db.session.add(mining)
    db.session.commit()

    return jsonify({"message": "Mining started", "weight": weight})


@mining_bp.route('/stop', methods=['POST'])
def mining_stop():
    wallet_address = request.json.get('wallet_address')
    if not wallet_address:
        return jsonify({"error": "wallet_address is required"}), 400

    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    last = MiningHistory.query.filter_by(wallet_user_id=user.id, is_settled=False)\
        .order_by(MiningHistory.mined_at.desc()).with_for_update().first()

    if not last:
        return jsonify({"error": "No active mining session found"}), 400

    now = datetime.utcnow()
    if not last.end_time:
        last.end_time = now

    elapsed = (last.end_time - last.mined_at).total_seconds()
    elapsed = min(elapsed, 86400)  # 最多记24小时

    reward = calculate_reward(last.mined_at, last.weight_snapshot, end_time=last.end_time)


    try:
        with db.session.begin_nested():
            # 1. 更新 MiningHistory
            last.points_earned = str(reward)
            last.end_time = now
            last.is_settled = True
            last.is_mining = False
            db.session.add(last)

            # 2. 更新 UserPointsAccount
            points_account = UserPointsAccount.query.filter_by(wallet_user_id=user.id).with_for_update().first()
            if not points_account:
                points_account = UserPointsAccount(
                    wallet_user_id=user.id,
                    total_points=0,
                    consecutive_days=0,
                    milestone_reached=0
                )
                db.session.add(points_account)
                db.session.flush()

            points_account.total_points += Decimal(reward)
            db.session.add(points_account)

            # 3. 新增 PointsHistory 记录
            points_history_record = PointsHistory(
                wallet_user_id=user.id,
                change_type='Manual stop mining',
                change_amount=Decimal(reward),
                description='Mining points',
                created_at=datetime.utcnow()
            )
            db.session.add(points_history_record)

        db.session.commit()

        return jsonify({
            "message": "Mining stopped",
            "earned_points": reward,
            "duration_seconds": int(elapsed)
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500



@mining_bp.route('/status', methods=['GET'])
def mining_status():
    wallet_address = request.args.get('wallet_address')
    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # 查询当前未结算的挖矿（进行中）
    last_active = MiningHistory.query.filter_by(wallet_user_id=user.id, is_settled=False)\
        .order_by(MiningHistory.mined_at.desc()).first()

    # 查询最近一次已结算的挖矿（历史）
    last_settled = MiningHistory.query.filter_by(wallet_user_id=user.id, is_settled=True)\
        .order_by(MiningHistory.mined_at.desc()).first()

    if last_active:
        now = datetime.utcnow()
        elapsed = (now - last_active.mined_at).total_seconds()
        if elapsed >= 86400:
            elapsed = 86400
            isMining = False
        else:
            isMining = True

        reward = calculate_reward(last_active.mined_at, last_active.weight_snapshot, end_time=now)

        return jsonify({
            "isMining": isMining,
            "start_time": last_active.mined_at.isoformat(),
            "current_reward": str(reward),
            "elapsed_seconds": int(elapsed),
            "weight_snapshot": last_active.weight_snapshot,
            "last_earned_points": None,
            "last_earned_time": None
        })
    else:
        # 没有活动挖矿了，返回最近一次结算奖励信息
        if last_settled:
            return jsonify({
                "isMining": False,
                "last_earned_points": last_settled.points_earned,
                "last_earned_time": last_settled.end_time.isoformat() if last_settled.end_time else None
            })
        else:
            return jsonify({"isMining": False, "last_earned_points": None, "last_earned_time": None})



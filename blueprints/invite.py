from flask import Blueprint, request, jsonify
from models import InviteRecord, WalletUser,UserPointsAccount,PointsHistory
from extensions import db
from datetime import datetime, timezone
from decimal import Decimal

invite_bp = Blueprint('invite', __name__,url_prefix='/api/referrals')

@invite_bp.route('/bind', methods=['POST'])
def bind_referral():
    data = request.get_json()
    referrer = data.get('referrer_address', '').lower()
    invited = data.get('invited_address', '').lower()

    if not referrer or not invited:
        return jsonify({"error": "Missing parameters"}), 400
    if referrer == invited:
        return jsonify({"error": "Cannot refer yourself"}), 400

    # 校验邀请人和被邀请人是否存在
    inviter_user = WalletUser.query.filter_by(wallet_address=referrer).first()
    invited_user = WalletUser.query.filter_by(wallet_address=invited).first()
    if not inviter_user or not invited_user:
        return jsonify({"error": "Invalid referrer or invited address"}), 400

    # 检查是否已经被邀请过
    existing = InviteRecord.query.filter_by(invitee_address=invited).first()
    if existing:
        return jsonify({"message": "You’ve already accepted an invitation"}), 200

    # 创建邀请关系
    new_record = InviteRecord(inviter_address=referrer, invitee_address=invited)
    db.session.add(new_record)

    base_reward = Decimal('10')  # 每次邀请奖励积分

    # --- 加锁查询用户积分账户 ---
    points_account = (
        UserPointsAccount.query
        .filter_by(wallet_user_id=inviter_user.id)
        .with_for_update()  # 加行级锁，防止并发修改
        .first()
    )
    if not points_account:
        return jsonify({"error": "User points account not found"}), 400

    # 更新总积分
    points_account.total_points = (points_account.total_points or Decimal('0')) + base_reward

    # 保存积分变动记录
    points_history = PointsHistory(
        wallet_user_id=inviter_user.id,
        change_type="invite_reward",
        change_amount=base_reward,
        created_at=datetime.now(timezone.utc),
        description=f"Invited {invited} get {base_reward} points"
    )
    db.session.add(points_history)

    # 提交事务
    db.session.commit()

    return jsonify({"message": "Referral bound successfully"})


@invite_bp.route('/stats', methods=['GET'])
def get_referral_stats():
    address = request.args.get('address', '').lower()
    if not address:
        return jsonify({"error": "Missing address parameter"}), 400

    # 1. 获取邀请总人数
    invite_count = InviteRecord.query.filter_by(inviter_address=address).count()

    # 2. 计算累计奖励 (假设每个邀请奖励100积分)
    base_reward = 10
    total_rewards = invite_count * base_reward

    # 3. 计算邀请等级 (自定义规则)
    if invite_count >= 30:
        level = 3  # 黄金级
    elif invite_count >= 10:
        level = 2  # 白银级
    elif invite_count >= 5:
        level = 1  # 青铜级
    else:
        level = 0  # 普通级

    # 4. 获取最近邀请记录 (可选)
    recent_invites = InviteRecord.query.filter_by(
        inviter_address=address
    ).order_by(
        InviteRecord.created_at.desc()
    ).limit(5).all()

    recent_invites_data = [{
        "invitee": record.invitee_address,
        "date": record.created_at.isoformat()
    } for record in recent_invites]

    return jsonify({
        "success": True,
        "data": {
            "inviteCount": invite_count,
            "totalRewards": total_rewards,
            "level": level,
            "recentInvites": recent_invites_data,
            # 可以添加更多统计信息
            "nextLevelRequirement": max(
                0,
                (
                    5 if level == 0 else
                    10 if level == 1 else
                    20 if level == 2 else
                    0
                ) - invite_count
            )
        }
    })
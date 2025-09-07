import math
from sqlalchemy import func
from datetime import datetime
from extensions import db
from models import InviteRecord


def calculate_user_weight(user, invite_counts=None):
    """
    计算用户权重（包含连续签到4档位分级）
    :param user: WalletUser实例（必须已预加载points_account）
    :param invite_counts: 预查询的邀请字典 {address: count}
    :return: (总权重, 权重明细)
    """
    weight = 0.0
    breakdown = {
        'consecutive_days': 0.0,
        'total_points': 0.0,
        'invite_count': 0.0,
        'vip_status': 0.0,
        'extra': 0.0
    }

    # 1. 连续签到权重（4档位）
    if user.points_account and user.points_account.consecutive_days is not None:
        cd = user.points_account.consecutive_days
        if cd >= 30:
            breakdown['consecutive_days'] = 1.0
        elif cd >= 15:
            breakdown['consecutive_days'] = 0.8
        elif cd >= 7:
            breakdown['consecutive_days'] = 0.5
        else:
            breakdown['consecutive_days'] = 0.1
        weight += breakdown['consecutive_days']

    # 2. 总积分权重
    if user.points_account and user.points_account.total_points is not None:
        tp = float(user.points_account.total_points)
        if tp >= 5000:
            breakdown['total_points'] = 1.0
        elif tp >= 3000:
            breakdown['total_points'] = 0.5
        elif tp >= 1000:
            breakdown['total_points'] = 0.3
        weight += breakdown['total_points']

    # 3. 邀请好友权重
    invite_count = invite_counts.get(user.wallet_address, 0) if invite_counts else 0
    if invite_count >= 30:
        breakdown['invite_count'] = 1.0
    elif invite_count >= 10:
        breakdown['invite_count'] = 0.5
    elif invite_count >= 5:
        breakdown['invite_count'] = 0.2
    weight += breakdown['invite_count']

    # 4. VIP权重（预留接口）
    # if getattr(user, 'is_vip', False):
    #     breakdown['vip_status'] = 1.0
    #     weight += 1.0

    # 5. 其他权重（预留接口）
    # extra_weight = getattr(user, 'extra_weight', 0)
    # breakdown['extra'] = min(extra_weight, 0.5)
    # weight += breakdown['extra']

    return min(weight, 5.0), breakdown

def calculate_reward(start_time, weight, end_time):
    """
       计算用户挖矿积分持续24小时
       挖矿速率decay_rate：0.0001

       """
    now = end_time or datetime.utcnow()
    elapsed = (now - start_time).total_seconds()
    elapsed = max(0, elapsed)
    max_duration = 86400  # 24小时
    elapsed = min(elapsed, max_duration)

    decay_rate = 0.0001
    # 权重=5,单日最多100*5
    base_reward = 100

    reward = base_reward * (1 - math.exp(-decay_rate * elapsed)) * weight
    return str(round(reward, 18))
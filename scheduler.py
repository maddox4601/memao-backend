from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from decimal import Decimal
from datetime import datetime, timezone,timedelta
from models import AirdropAddress, AirdropConfig,WalletUser,MiningHistory,PointsHistory,UserPointsAccount,InviteRecord
from extensions import db
from utils.mining_service import calculate_user_weight,calculate_reward
from sqlalchemy.orm import joinedload
from sqlalchemy import func
import traceback

scheduler = BackgroundScheduler()


def scheduled_withdrawal_job(app):
    with app.app_context():
        try:
            print(f"[{datetime.now()}] Running scheduled withdrawal task...")
            from blueprints.withdraw import process_withdrawals
            process_withdrawals()
            print(f"[{datetime.now()}] Withdrawal task completed.")
        except Exception:
            print(f"[{datetime.now()}] Withdrawal task failed:")
            traceback.print_exc()


def distribute_airdrop_job(app):
    with app.app_context():
        try:
            from models import AirdropConfig  # 根据你的项目结构调整

            config = AirdropConfig.query.first()
            if not config or not config.is_task_enabled:
                print(f"[{datetime.now()}] 定时任务已关闭，跳过执行。")
                return

            print(f"[{datetime.now()}] Running scheduled airdrop task...")
            from blueprints.airdrop import manual_distribute
            manual_distribute()
            print(f"[{datetime.now()}] Airdrop task completed.")
        except Exception:
            print(f"[{datetime.now()}] Airdrop task failed:")
            traceback.print_exc()


# 更新用户权重
def update_all_users_daily_weight(app):
    with app.app_context():
        try:
            start_time = datetime.now(timezone.utc)
            print(f"[{start_time}] Starting daily weight update task...")

            # 1. 批量查询用户及关联数据（关键优化）
            users = WalletUser.query.options(
                joinedload(WalletUser.points_account),  # 预加载积分账户
                joinedload(WalletUser.checkin_history)  # 按需加载其他关联
            ).all()

            # 2. 预查询所有邀请数据（避免N+1）
            invite_counts = get_invite_counts([u.wallet_address for u in users])

            # 3. 分批更新权重（每1000用户提交一次）
            batch_size = 1000
            for i in range(0, len(users), batch_size):
                batch = users[i:i + batch_size]
                for user in batch:
                    weight, _ = calculate_user_weight(user, invite_counts)
                    user.daily_weight = weight
                    user.last_weight_update = datetime.now(timezone.utc)

                db.session.commit()
                print(f"Processed {min(i + batch_size, len(users))}/{len(users)} users")

            # 4. 记录任务完成
            duration = (datetime.now(timezone.utc) - start_time).total_seconds()
            print(f"[{datetime.now(timezone.utc)}] Task completed in {duration:.2f}s")

        except Exception as e:
            db.session.rollback()
            error_time = datetime.now(timezone.utc)
            print(f"[{error_time}] Task failed: {str(e)}")
            traceback.print_exc()
            # 可以添加邮件/钉钉告警
            # send_alert(f"权重更新失败: {str(e)}")


def get_invite_counts(addresses):
    """批量获取邀请数量 {address: count}"""
    if not addresses:
        return {}

    return dict(db.session.query(
        InviteRecord.inviter_address,
        func.count(InviteRecord.id)
    ).filter(
        InviteRecord.inviter_address.in_(addresses)
    ).group_by(
        InviteRecord.inviter_address
    ).all())


# 计算并终止已挖矿24小时的钱包地址
def settle_expired_sessions(app):
    with app.app_context():
        try:
            now = datetime.utcnow()
            sessions = MiningHistory.query.filter_by(is_settled=False).all()

            for session in sessions:
                elapsed = (now - session.mined_at).total_seconds()
                if elapsed >= 86400:
                    session.end_time = session.mined_at + timedelta(seconds=86400)
                    session.points_earned = calculate_reward(
                        session.mined_at,
                        session.weight_snapshot,
                        session.end_time
                    )
                    session.is_settled = True
                    session.is_mining = False

                    # 获取用户
                    user = session.wallet_user

                    # 查询或创建积分账户（加锁防并发）
                    points_account = UserPointsAccount.query.filter_by(wallet_user_id=user.id).with_for_update().first()
                    if not points_account:
                        points_account = UserPointsAccount(
                            wallet_user_id=user.id,
                            total_points=0,
                            consecutive_days=0,
                            milestone_reached=0
                        )
                        db.session.add(points_account)

                    # 更新积分账户
                    points_account.total_points += Decimal(session.points_earned)

                    # 添加积分记录
                    points_history = PointsHistory(
                        wallet_user_id=user.id,
                        change_type="mining_reward",
                        change_amount=Decimal(session.points_earned),
                        description="Mining session reward settled",
                        created_at=datetime.utcnow()
                    )
                    db.session.add(points_history)

            db.session.commit()
            print(f"[{datetime.utcnow()}] Expired mining sessions settled.")

        except Exception:
            db.session.rollback()
            print(f"[{datetime.utcnow()}] Settling expired sessions failed:")
            traceback.print_exc()


def start_scheduler(app):
    scheduler.add_job(lambda: scheduled_withdrawal_job(app), 'interval', hours=24)
    scheduler.add_job(lambda: distribute_airdrop_job(app), 'interval', minutes=5)
    # 每天凌晨0点执行一次挖矿权重更新任务
    scheduler.add_job(lambda: update_all_users_daily_weight(app), 'cron', hour=0, minute=0)
    #每5min执行一次
    scheduler.add_job(lambda: settle_expired_sessions(app), 'interval', minutes=5)


    scheduler.start()
    print("Scheduler started: withdrawal every 24h, airdrop every 5min")

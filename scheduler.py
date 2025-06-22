from apscheduler.schedulers.background import BackgroundScheduler
from flask import current_app
from datetime import datetime, timezone
from models import db, AirdropAddress, AirdropConfig
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


def start_scheduler(app):
    scheduler.add_job(lambda: scheduled_withdrawal_job(app), 'interval', hours=24)
    scheduler.add_job(lambda: distribute_airdrop_job(app), 'interval', minutes=5)
    scheduler.start()
    print("Scheduler started: withdrawal every 24h, airdrop every 5min")

from apscheduler.schedulers.background import BackgroundScheduler

scheduler = BackgroundScheduler()

def scheduled_job(app):
    with app.app_context():
        print("Running scheduled withdrawal task...")
        from blueprints.withdraw import process_withdrawals  # 延迟导入
        process_withdrawals()

def start_scheduler(app):
    scheduler.add_job(lambda: scheduled_job(app), 'interval', minutes=5)
    scheduler.start()
    print("Scheduler started: running every 5 minutes")

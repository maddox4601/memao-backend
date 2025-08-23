from flask import Flask, jsonify
from flask_cors import CORS
from flask_session import Session
from flask_migrate import Migrate
from extensions import db
from dotenv import load_dotenv
import os

# 提前导入模型注册函数（明确显示依赖关系）
from models import register_models

# 蓝图导入（保持原样）
from blueprints.contact import contact_bp
from blueprints.airdrop import airdrop_bp
from blueprints.auth import auth_bp
from blueprints.withdraw import withdraw_bp
from blueprints.checkin import checkin_bp
from blueprints.activity import activity_bp
from blueprints.mining import mining_bp
from blueprints.invite import invite_bp
from blueprints.socialauth import socialauth_bp
from geoip_utils.geoip_bp import geoip_bp

load_dotenv()

def create_app():
    app = Flask(__name__)

    # CORS 允许前端携带 Cookie
    CORS(app, supports_credentials=True)

    # ===== 配置 =====
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY'),
        JWT_SECRET=os.getenv('JWT_SECRET'),
        SESSION_TYPE=os.getenv('SESSION_TYPE', 'filesystem'),
        SESSION_PERMANENT=os.getenv('SESSION_PERMANENT', 'False') == 'True',
        SQLALCHEMY_DATABASE_URI=os.getenv('DB_URI'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False
    )

    # ===== 初始化扩展 =====
    db.init_app(app)
    Migrate(app, db)
    Session(app)

    # ===== 关键改进：安全注册模型 =====
    with app.app_context():
        register_models()  # 确保在应用上下文中注册

    # ===== 注册蓝图 =====
    blueprints = [
        contact_bp,
        airdrop_bp,
        auth_bp,
        checkin_bp,
        withdraw_bp,
        geoip_bp,
        activity_bp,
        mining_bp,
        invite_bp,
        socialauth_bp
    ]
    for bp in blueprints:
        app.register_blueprint(bp)

    # 健康检查
    @app.route('/')
    def health_check():
        return jsonify({'status': 'healthy'})

    return app

if __name__ == '__main__':
    from scheduler import start_scheduler  # 延迟导入
    app = create_app()
    start_scheduler(app)
    app.run(host='0.0.0.0', port=5000)
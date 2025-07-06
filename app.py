from flask import Flask, jsonify
from flask_cors import CORS
from flask_session import Session
from flask_migrate import Migrate


from blueprints.contact import contact_bp
from blueprints.airdrop import airdrop_bp
from blueprints.auth import auth_bp
from blueprints.withdraw import withdraw_bp
from blueprints.checkin import checkin_bp
from extensions import db
from dotenv import load_dotenv
import os

def create_app():
    app = Flask(__name__)

    # CORS 允许前端携带 Cookie
    CORS(app, supports_credentials=True)

    # ===== 安全 & Session 配置 =====
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
    app.config['JWT_SECRET'] = os.getenv('JWT_SECRET')
    app.config['SESSION_TYPE'] = os.getenv('SESSION_TYPE', 'filesystem')
    app.config['SESSION_PERMANENT'] = os.getenv('SESSION_PERMANENT', 'False') == 'True'

    # ===== 数据库配置 =====
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DB_URI')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ===== 初始化组件 =====
    db.init_app(app)
    Migrate(app, db)
    Session(app)  # 初始化 session 支持

    # ===== 注册蓝图 =====
    app.register_blueprint(contact_bp)
    app.register_blueprint(airdrop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(withdraw_bp)

    # 健康检查
    @app.route('/')
    def health_check():
        return jsonify({'status': 'healthy'})

    return app


if __name__ == '__main__':
    from scheduler import start_scheduler  # ✅ 延迟导入，避免循环依赖

    app = create_app()
    start_scheduler(app)
    app.run(debug=True)

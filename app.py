from flask import Flask, jsonify
from flask_cors import CORS
from blueprints.contact import contact_bp
from blueprints.airdrop import airdrop_bp
from blueprints.auth import auth_bp
from blueprints.withdraw import withdraw_bp
from blueprints.checkin import checkin_bp
from flask_migrate import Migrate
from extensions import db

def create_app():
    app = Flask(__name__)
    CORS(app)

    # 数据库配置
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Maddox1988%40@localhost:3306/memao_portal?charset=utf8mb4'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    Migrate(app, db)

    # 注册蓝图
    app.register_blueprint(contact_bp)
    app.register_blueprint(airdrop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(checkin_bp)
    app.register_blueprint(withdraw_bp)

    @app.route('/')
    def health_check():
        return jsonify({'status': 'healthy'})

    return app


if __name__ == '__main__':
    from scheduler import start_scheduler  # ✅ 延迟导入，避免循环

    app = create_app()

    # 启动 scheduler
    start_scheduler(app)

    app.run(debug=True)

from datetime import datetime, timezone
from extensions import db

class MiningHistory(db.Model):
    __tablename__ = 'mining_history'

    id = db.Column(db.Integer, primary_key=True)
    wallet_user_id = db.Column(db.Integer, db.ForeignKey('wallet_users.id'), nullable=False)
    mined_at = db.Column(db.DateTime, default=lambda: datetime.utcnow())
    end_time = db.Column(db.DateTime, nullable=True)  # 主动停止时设置
    points_earned = db.Column(db.String(64), default='0')
    weight_snapshot = db.Column(db.Float, nullable=False)
    is_settled = db.Column(db.Boolean, default=False)
    is_mining = db.Column(db.Boolean, default=True)

    wallet_user = db.relationship('WalletUser', backref='mining_history')

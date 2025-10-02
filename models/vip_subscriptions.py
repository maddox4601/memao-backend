from datetime import datetime, timedelta
from extensions import db

class VIPSubscription(db.Model):
    __tablename__ = 'vip_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    wallet_user_id = db.Column(db.Integer, db.ForeignKey('wallet_users.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    tx_hash = db.Column(db.String(66), nullable=True)  # 记录交易哈希，ETH tx hash 长度为 66
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    wallet_user = db.relationship('WalletUser', backref='vip_subscriptions')

    def to_dict(self):
        return {
            "id": self.id,
            "wallet_user_id": self.wallet_user_id,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "is_active": self.is_active,
            "tx_hash": self.tx_hash
        }

    def extend_subscription(self, days: int):
        """延长会员有效期"""
        if self.end_date < datetime.utcnow():
            self.start_date = datetime.utcnow()
            self.end_date = datetime.utcnow() + timedelta(days=days)
        else:
            self.end_date += timedelta(days=days)
        self.is_active = True

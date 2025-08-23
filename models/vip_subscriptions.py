from datetime import datetime
from extensions import db

class VIPSubscription(db.Model):
    __tablename__ = 'vip_subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    wallet_user_id = db.Column(db.Integer, db.ForeignKey('wallet_users.id'), nullable=False)
    start_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)

    wallet_user = db.relationship('WalletUser', backref='vip_subscriptions')

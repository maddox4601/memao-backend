# models.py

from extensions import db
from datetime import datetime

class InviteRecord(db.Model):
    __tablename__ = 'invite_records'

    id = db.Column(db.Integer, primary_key=True)
    inviter_address = db.Column(db.String(66), nullable=False, index=True)  # 发起邀请的钱包地址
    invitee_address = db.Column(db.String(66), nullable=False, unique=True, index=True)  # 被邀请的钱包地址
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

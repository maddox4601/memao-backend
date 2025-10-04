import uuid
from extensions import db
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint, ForeignKey

class User(db.Model):
    # 钱包用户记录
    __tablename__ = 'users'
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(64), unique=True, nullable=True)
    email = db.Column(db.String(128), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    wallets = relationship("WalletUser", back_populates="user")
    oauth_accounts = relationship("UserAccount", back_populates="user")

    # 三方用户记录
class UserAccount(db.Model):
    __tablename__ = 'user_accounts'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), ForeignKey('users.id'), nullable=False)
    provider = db.Column(db.String(32), nullable=False)
    provider_uid = db.Column(db.String(128), nullable=False)

    user = relationship("User", back_populates="oauth_accounts")

    __table_args__ = (
        UniqueConstraint('provider', 'provider_uid', name='uix_provider_uid'),
    )

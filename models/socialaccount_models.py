from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from extensions import db


class SocialAccount(db.Model):
    __tablename__ = 'social_accounts'

    id = db.Column(db.Integer, primary_key=True)
    wallet_user_id = db.Column(db.Integer, ForeignKey('wallet_users.id'), nullable=False)

    provider = db.Column(db.String(32), nullable=False)   # 平台名: "twitter", "discord", "telegram"
    social_id = db.Column(db.String(100), nullable=False) # 平台用户唯一ID (Twitter 的 user_id)
    handle = db.Column(db.String(64), nullable=True)      # 用户名/handle (@xxx)
    verified = db.Column(db.Boolean, default=False)       # 是否验证完成

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    wallet_user = relationship("WalletUser", backref="social_accounts")

    __table_args__ = (
        UniqueConstraint('provider', 'social_id', name='uix_provider_social_id'),
        UniqueConstraint('wallet_user_id', 'provider', name='uix_wallet_provider'),
    )

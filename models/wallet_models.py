from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy import Numeric
from extensions import db

class WalletUser(db.Model):
    __tablename__ = 'wallet_users'

    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(42), unique=True, nullable=False)
    nickname = db.Column(db.String(64), nullable=True)
    registered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # 新增：关联统一用户
    user_id = db.Column(db.String(36), ForeignKey('users.id'), nullable=True)
    user = relationship("User", back_populates="wallets")

    daily_weight = db.Column(db.Float, default=1.0)  # 每日权重
    last_weight_update = db.Column(db.DateTime)      # 更新时间

    checkin_history = relationship("CheckinHistory", back_populates="wallet_user")
    points_account = relationship("UserPointsAccount", uselist=False, back_populates="wallet_user")


class CheckinHistory(db.Model):
    __tablename__ = 'checkin_history'

    id = db.Column(db.Integer, primary_key=True)
    wallet_user_id = db.Column(db.Integer, ForeignKey('wallet_users.id'), nullable=False)
    checkin_date = db.Column(db.Date, nullable=False)
    points_earned = db.Column(db.Integer, default=1)
    reward_type = db.Column(db.String(20))

    wallet_user = relationship("WalletUser", back_populates="checkin_history")

    __table_args__ = (
        UniqueConstraint('wallet_user_id', 'checkin_date', name='uix_wallet_checkin_date'),
    )

class UserPointsAccount(db.Model):
    __tablename__ = 'user_points_accounts'

    wallet_user_id = db.Column(db.Integer, ForeignKey('wallet_users.id'), primary_key=True)
    total_points = db.Column(Numeric(36, 18), default=0, nullable=False)
    consecutive_days = db.Column(db.Integer, default=0, nullable=False)
    last_checkin_date = db.Column(db.Date)
    milestone_reached = db.Column(db.Integer, default=0, nullable=False)
    withdraw_nonce = db.Column(db.Integer, default=0, nullable=False)  # 新增提现nonce字段
    wallet_user = relationship("WalletUser", back_populates="points_account")

class WithdrawalHistory(db.Model):
    __tablename__ = 'withdrawal_history'

    id = db.Column(db.Integer, primary_key=True)
    wallet_user_id = db.Column(db.Integer, db.ForeignKey('wallet_users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')
    processed_at = db.Column(db.DateTime, nullable=True)
    tx_hash = db.Column(db.String(100), nullable=True)
    remarks = db.Column(db.Text, nullable=True)

    wallet_user = db.relationship('WalletUser', backref='withdrawal_history')

class PointsHistory(db.Model):
    __tablename__ = 'points_history'

    id = db.Column(db.Integer, primary_key=True)
    wallet_user_id = db.Column(db.Integer, db.ForeignKey('wallet_users.id'), nullable=False)
    change_type = db.Column(db.String(60), nullable=False)
    change_amount = db.Column(Numeric(36, 18), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    description = db.Column(db.String(255), nullable=True)

    wallet_user = db.relationship('WalletUser', backref='points_history')
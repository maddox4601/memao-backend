from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import UniqueConstraint, ForeignKey
from sqlalchemy.orm import relationship
from extensions import db  # 你的 extensions.py 中的 db = SQLAlchemy()


from datetime import datetime, timezone

class WithdrawalHistory(db.Model):
    __tablename__ = 'withdrawal_history'

    id = db.Column(db.Integer, primary_key=True)
    wallet_user_id = db.Column(db.Integer, db.ForeignKey('wallet_users.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)  # 单位可以是最小计量单位，比如wei或points，确保一致
    requested_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')  # pending, completed, rejected
    processed_at = db.Column(db.DateTime, nullable=True)  # 处理完成时间
    tx_hash = db.Column(db.String(100), nullable=True)  # 交易哈希
    remarks = db.Column(db.Text, nullable=True)  # 失败原因或备注

    wallet_user = db.relationship('WalletUser', backref='withdrawal_history')



class WalletUser(db.Model):
    __tablename__ = 'wallet_users'

    id = db.Column(db.Integer, primary_key=True)
    wallet_address = db.Column(db.String(42), unique=True, nullable=False)
    nickname = db.Column(db.String(64), nullable=True)
    registered_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
    total_points = db.Column(db.Integer, default=0, nullable=False)
    consecutive_days = db.Column(db.Integer, default=0, nullable=False)
    last_checkin_date = db.Column(db.Date)
    milestone_reached = db.Column(db.Integer, default=0, nullable=False)

    wallet_user = relationship("WalletUser", back_populates="points_account")

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100))
    message = db.Column(db.String(1000))
    replied = db.Column(db.Boolean, default=False)
    replay_content = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    replied_at = db.Column(db.DateTime)


# 空投模型


class AirdropAddress(db.Model):
    __tablename__ = 'airdrop_addresses'

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), nullable=False, unique=True)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    comment = db.Column(db.String(100))

    # ✅ 新增防重复字段
    is_distributed = db.Column(db.Boolean, default=False)  # 是否已发放
    distributed_at = db.Column(db.DateTime, nullable=True)  # 发放时间（可为空）


class AirdropConfig(db.Model):
    __tablename__ = 'airdrop_config'

    id = db.Column(db.Integer, primary_key=True)
    is_task_enabled = db.Column(db.Boolean, default=True)  # 定时任务是否开启
    batch_size = db.Column(db.Integer, default=20)  # 每批发放人数ETH defalut=20
    airdrop_amount = db.Column(db.String(50), default=str(1 * 10 ** 18))

class TokenTransfer(db.Model):
    __tablename__ = 'token_transfers'

    id = db.Column(db.Integer, primary_key=True)
    from_address = db.Column(db.String(255), nullable=False)
    to_address = db.Column(db.String(255), nullable=False)
    token_symbol = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    tx_hash = db.Column(db.String(255), nullable=False, unique=True)
    transferred_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='pending')

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

from datetime import datetime, timezone
from extensions import db

class AirdropAddress(db.Model):
    __tablename__ = 'airdrop_addresses'

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(255), nullable=False, unique=True)
    submitted_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    comment = db.Column(db.String(100))
    is_distributed = db.Column(db.Boolean, default=False)
    distributed_at = db.Column(db.DateTime, nullable=True)

class AirdropConfig(db.Model):
    __tablename__ = 'airdrop_config'

    id = db.Column(db.Integer, primary_key=True)
    is_task_enabled = db.Column(db.Boolean, default=True)
    batch_size = db.Column(db.Integer, default=20)
    airdrop_amount = db.Column(db.String(50), default=str(1 * 10 ** 18))
    distribution_type = db.Column(db.String(20), default="points")  # "points" 或 "contract"

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
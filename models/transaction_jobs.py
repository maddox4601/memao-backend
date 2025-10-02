from extensions import db
from enum import Enum
from datetime import datetime
class JobStatusEnum(Enum):
    pending = "pending"  # 任务已提交，待执行
    sent = "sent"        # 已发送交易（有 tx_hash）
    success = "success"  # 成功确认
    failed = "failed"    # 失败（可重试）

class TransactionJob(db.Model):
    __tablename__ = "transaction_jobs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(128), db.ForeignKey("paypal_orders.order_id"), nullable=False)
    wallet_address = db.Column(db.String(128), nullable=False)
    payload = db.Column(db.JSON, nullable=True)  # 可以存 token_name、symbol、supply 等信息
    status = db.Column(db.Enum(JobStatusEnum), default=JobStatusEnum.pending, nullable=False)
    tx_hash = db.Column(db.String(128), nullable=True)     # 交易哈希
    error_message = db.Column(db.Text, nullable=True)      # 失败原因
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 反向引用：job.order 就能访问对应订单
    order = db.relationship("PayPalOrder", backref="jobs")

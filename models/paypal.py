from datetime import datetime
from extensions import db
from enum import Enum



class PaymentStatusEnum(Enum):
    pending = "pending"  # 订单创建，但未支付完成
    paid = "paid"        # 支付完成
    failed = "failed"    # 支付失败

class DeployStatusEnum(Enum):
    pending = "pending"  # 钱包未绑定 / 未 mint
    processing = "processing"  # 添加这个状态
    success = "success"  # 已 mint 到用户钱包
    failed = "failed"    # mint 失败

class PayPalOrder(db.Model):
    __tablename__ = "paypal_orders"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(128), unique=True, nullable=False)  # PayPal 订单号
    user_id = db.Column(db.String(128), db.ForeignKey("users.id"), nullable=True)  # 关联用户，可为空（兼容未登录）
    token_name = db.Column(db.String(64), nullable=False)
    symbol = db.Column(db.String(16), nullable=False)
    supply = db.Column(db.BigInteger, nullable=False)
    wallet_address = db.Column(db.String(128), nullable=True)            # 用户绑定钱包地址，可为空
    contract_address = db.Column(db.String(128), nullable=True)          # 合约地址
    minted = db.Column(db.Boolean, default=False)                         # 是否已 mint
    amount = db.Column(db.Numeric(18, 8), nullable=False)                # 支付金额
    payment_status = db.Column(db.Enum(PaymentStatusEnum), default=PaymentStatusEnum.pending)
    deploy_status = db.Column(db.Enum(DeployStatusEnum), default=DeployStatusEnum.pending)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<PayPalOrder {self.order_id} - {self.payment_status} - {self.deploy_status}>"

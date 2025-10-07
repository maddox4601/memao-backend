# models.py
from datetime import datetime
from extensions import db

class EthOrder(db.Model):
    """
    存储用户链上自助部署的订单记录，表名 eth_orders
    """
    __tablename__ = "eth_orders"

    id = db.Column(db.BigInteger, primary_key=True, autoincrement=True)
    order_id = db.Column(db.String(64), unique=True, nullable=False, index=True)   # 前端生成的订单 id（如 eth-<timestamp>）
    token_address = db.Column(db.String(66), nullable=True, index=True)            # token 合约地址（0x...）
    wallet_address = db.Column(db.String(66), nullable=True, index=True)           # 用户钱包地址
    tx_hash = db.Column(db.String(100), nullable=True, index=True)                 # 交易哈希
    token_name = db.Column(db.String(200), nullable=True)                          # 代币名称
    symbol = db.Column(db.String(50), nullable=True)                               # 代币符号
    supply = db.Column(db.Text, nullable=True)                                     # 初始供应量（保为字符串，兼容大数）
    decimals = db.Column(db.Integer, nullable=True)                                # 可选：代币 decimals
    deploy_status = db.Column(db.String(20), nullable=False, default="pending")     # pending | success | failed
    payment_type = db.Column(db.String(20), nullable=True)                         # eth / bnb / usdt ...
    amount = db.Column(db.Numeric(38, 18), nullable=True)                          # 支付金额（精度高，适合链上金额）
    error = db.Column(db.Text, nullable=True)                                      # 错误信息（部署失败时记录）
    meta = db.Column(db.JSON, nullable=True)                                       # 可选：保存额外数据（前端传过来的其它字段）
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<EthOrder {self.order_id} {self.deploy_status}>"

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "token_address": self.token_address,
            "wallet_address": self.wallet_address,
            "tx_hash": self.tx_hash,
            "token_name": self.token_name,
            "symbol": self.symbol,
            "supply": self.supply,
            "decimals": self.decimals,
            "deploy_status": self.deploy_status,
            "payment_type": self.payment_type,
            "amount": str(self.amount) if self.amount is not None else None,
            "error": self.error,
            "meta": self.meta,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def create_or_update(cls, data: dict):
        """
        根据 order_id 做 create 或 update（方便前端多次回调时幂等处理）
        - data 字典应包含 order_id（必需）和其它可选字段
        """
        if not data.get("order_id"):
            raise ValueError("order_id is required")

        order = cls.query.filter_by(order_id=data["order_id"]).first()
        if order:
            # 更新已存在字段（仅更新非 None 值）
            for key, value in data.items():
                if key == "id":
                    continue
                if hasattr(order, key) and value is not None:
                    setattr(order, key, value)
        else:
            order = cls(**data)
            db.session.add(order)

        db.session.commit()
        return order

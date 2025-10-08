from flask import Blueprint, request, jsonify
from models import EthOrder
from extensions import db

eth_bp = Blueprint("deploy", __name__,url_prefix="/api/eth")

# 1️⃣ 保存订单接口
@eth_bp.route("/save_eth_order", methods=["POST"])
def save_eth_order():
    """
    保存用户链上部署记录（成功或失败）
    """
    data = request.get_json() or {}
    try:
        order = EthOrder(
            order_id=data.get("order_id"),
            token_address=data.get("token_address"),
            wallet_address=data.get("wallet_address"),
            tx_hash=data.get("tx_hash"),
            token_name=data.get("token_name"),
            symbol=data.get("symbol"),
            supply=data.get("supply"),
            deploy_status=data.get("deploy_status", "unknown"),
            payment_type=data.get("payment_type", "eth"),
            amount=data.get("amount"),
            error=data.get("error"),
        )

        db.session.add(order)
        db.session.commit()

        return jsonify({"message": "订单保存成功", "data": order.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"保存失败: {str(e)}"}), 500

#2️⃣ 查询部署列表（可按钱包过滤）
@eth_bp.route("/list", methods=["GET"])
def list_orders():
    wallet_address = request.args.get("wallet_address")
    query = EthOrder.query

    if wallet_address:
        query = query.filter_by(wallet_address=wallet_address)

    orders = query.order_by(EthOrder.created_at.desc()).all()
    return jsonify([o.to_dict() for o in orders])


# 3️⃣ 查询单个订单
@eth_bp.route("/<order_id>", methods=["GET"])
def get_order(order_id):
    order = EthOrder.query.filter_by(order_id=order_id).first()
    if not order:
        return jsonify({"error": "订单不存在"}), 404
    return jsonify(order.to_dict())

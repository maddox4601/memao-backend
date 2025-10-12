from flask import Blueprint, request, jsonify
from models import EthOrder,PayPalOrder
from extensions import db
from sqlalchemy import or_
from flask_jwt_extended import jwt_required, get_jwt_identity

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
            user_id=data.get("user_id"),
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



#统一订单查询（包括ETH和paypal订单）
@eth_bp.route("/orders", methods=["GET"])
@jwt_required(optional=True)
def get_orders():
    """查询指定用户的所有订单"""
    user_id = request.args.get("userId")
    if not user_id:
        return jsonify({"code": 1, "message": "user_id 缺失"}), 400

    eth_orders = EthOrder.query.filter_by(user_id=user_id).order_by(EthOrder.created_at.desc()).all()
    paypal_orders = PayPalOrder.query.filter_by(user_id=user_id).order_by(PayPalOrder.created_at.desc()).all()

    def format_eth(order):
        return {
            "order_id": order.order_id,
            "payment_type": order.payment_type or "eth",
            "deploy_status": order.deploy_status,
            "token_address": order.token_address,
            "wallet_address": order.wallet_address,
            "timestamp": order.created_at.strftime("%Y/%m/%d %H:%M:%S"),
        }

    def format_paypal(order):
        return {
            "order_id": order.order_id,
            "payment_type": "paypal",
            "deploy_status": order.deploy_status.value if order.deploy_status else "pending",
            "token_address": order.contract_address,
            "wallet_address": order.wallet_address,
            "timestamp": order.created_at.strftime("%Y/%m/%d %H:%M:%S"),
        }

    all_orders = [format_eth(o) for o in eth_orders] + [format_paypal(o) for o in paypal_orders]
    all_orders.sort(key=lambda x: x["timestamp"], reverse=True)

    return jsonify({"code": 0, "message": "success", "data": all_orders})

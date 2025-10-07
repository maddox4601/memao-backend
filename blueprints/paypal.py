# paypal.py
from flask import Blueprint, request, jsonify
from extensions import db, tx_queue, redis_conn, socketio
from models import PayPalOrder, PaymentStatusEnum, DeployStatusEnum
from utils.tx_jobs import deploy_contract
from flask_socketio import join_room, leave_room
from rq.job import Job
from web3 import Web3
import os, requests, json

paypal_bp = Blueprint("paypal", __name__, url_prefix="/api/paypal")

PAYPAL_API = os.getenv("PAYPAL_API")  # 沙箱环境
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")

# -------------------------------
# 1️⃣ capture & 验证 PayPal 订单
# -------------------------------
def verify_paypal_order(order_id):
    # 获取 Access Token
    auth_resp = requests.post(
        f"{PAYPAL_API}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        data={"grant_type": "client_credentials"}
    )
    if auth_resp.status_code != 200:
        return False, "无法获取 PayPal token"
    access_token = auth_resp.json().get("access_token")

    # 捕获订单
    capture_resp = requests.post(
        f"{PAYPAL_API}/v2/checkout/orders/{order_id}/capture",
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {access_token}"}
    )
    if capture_resp.status_code not in (200, 201):
        return False, f"订单 capture 失败: {capture_resp.text}"

    capture_data = capture_resp.json()
    if capture_data.get("status") != "COMPLETED":
        return False, f"支付未完成，状态: {capture_data.get('status')}"
    return True, capture_data

# -------------------------------
# 2️⃣ 支付完成回调-paypal订单
# -------------------------------
@paypal_bp.route("/payment-complete", methods=["POST"])
def payment_complete():
    data = request.json
    order_id = data.get("order_id")
    if not order_id:
        return jsonify({"error": "order_id 必填"}), 400

    order = PayPalOrder.query.filter_by(order_id=order_id).first()
    if order:
        return jsonify({"message": "订单已存在"}), 200

    success, result = verify_paypal_order(order_id)
    if not success:
        return jsonify({"error": f"支付验证失败: {result}"}), 400

    try:
        capture = result["purchase_units"][0]["payments"]["captures"][0]
        amount_value = float(capture["amount"]["value"])
        currency = capture["amount"]["currency_code"]

        EXPECTED_PRICE = float(os.getenv("TOKEN_PRICE", "0.01"))
        EXPECTED_CURRENCY = os.getenv("TOKEN_CURRENCY", "USD")

        if amount_value != EXPECTED_PRICE or currency != EXPECTED_CURRENCY:
            return jsonify({"error": "支付金额或币种不匹配"}), 400

        order = PayPalOrder(
            order_id=order_id,
            token_name=data.get("token_name", "UserCoin"),
            symbol=data.get("symbol", "UC"),
            supply=int(data.get("supply", 1000000)),
            amount=float(amount_value),
            payment_status=PaymentStatusEnum.paid,
            deploy_status=DeployStatusEnum.pending
        )
        db.session.add(order)
        db.session.commit()
    except Exception as e:
        return jsonify({"error": f"数据库保存失败: {e}"}), 500

    return jsonify({"message": "支付记录保存成功"}), 200

# -------------------------------
# 3️⃣ 查询未绑定钱包的订单列表
# -------------------------------
@paypal_bp.route("/pending-orders", methods=["GET"])
def get_pending_orders():
    orders = PayPalOrder.query.filter_by(payment_status=PaymentStatusEnum.paid,
                                         deploy_status=DeployStatusEnum.pending).all()
    result = [
        {
            "order_id": o.order_id,
            "token_name": o.token_name,
            "symbol": o.symbol,
            "token_amount": o.token_amount,
            "amount": float(o.amount),
            "wallet_address": o.wallet_address,
            "created_at": o.created_at.isoformat()
        } for o in orders
    ]
    return jsonify(result), 200

# -------------------------------
# 4️⃣ 用户绑定钱包并 mint（入队异步）
# -------------------------------
@paypal_bp.route("/bind-wallet", methods=["POST"])
def bind_wallet():
    data = request.json
    order_id = data.get("order_id")
    wallet_address = data.get("wallet_address")
    if not order_id or not wallet_address:
        return jsonify({"error": "order_id 和 wallet_address 必填"}), 400

    try:
        wallet_address = Web3.to_checksum_address(wallet_address)
    except Exception:
        return jsonify({"error": "无效的钱包地址"}), 400

    order = PayPalOrder.query.filter_by(
        order_id=order_id,
        payment_status=PaymentStatusEnum.paid,
        deploy_status=DeployStatusEnum.pending
    ).first()
    if not order:
        return jsonify({"error": "未找到可 mint 的订单"}), 404

    # 入队异步任务
    job = tx_queue.enqueue(deploy_contract, order_id, wallet_address, job_id=None)
    # 再把 job_id 传给 deploy_contract 用于推送
    job = tx_queue.enqueue(deploy_contract, order_id, wallet_address, job.id)

    return jsonify({"message": "任务已加入队列，正在异步处理", "job_id": job.id}), 200

# -------------------------------
# 5️⃣ 查询部署任务状态
#   前端定时轮训需要该接口（目前socketio模式不需要该接口）
# -------------------------------
@paypal_bp.route("/bind-wallet-status/<job_id>", methods=["GET"])
def bind_wallet_status(job_id):
    try:
        job = Job.fetch(job_id, connection=redis_conn)
    except Exception:
        return jsonify({"error": "任务不存在"}), 404

    status = job.get_status()  # queued, started, finished, failed
    response = {"job_id": job_id, "status": status}

    if status == "finished":
        if job.args:
            order_id = job.args[0]
            order = PayPalOrder.query.filter_by(order_id=order_id).first()
            if order:
                response.update({
                    "deploy_status": order.deploy_status.value,
                    "tokenAddress": order.contract_address,
                    "wallet_address": order.wallet_address
                })
    elif status == "failed":
        response["error"] = str(job.exc_info)

    return jsonify(response), 200

# -------------------------------
# 6️ 处理完成后通知前端
# -------------------------------
@paypal_bp.route("/notify-deploy-complete", methods=["POST"])
def notify_deploy_complete():
    """
    Worker 调用接口通知前端部署完成
    """
    data = request.json
    order_id = data.get("order_id")
    if not order_id:
        return jsonify({"error": "order_id 必填"}), 400

    order = PayPalOrder.query.filter_by(order_id=order_id).first()
    if not order:
        return jsonify({"error": "订单不存在"}), 404

    # 更新数据库状态
    deploy_status = data.get("deploy_status")
    token_address = data.get("token_address")
    wallet_address = data.get("wallet_address")
    error = data.get("error")

    if deploy_status:
        order.deploy_status = DeployStatusEnum[deploy_status]
    if token_address:
        order.contract_address = token_address
    if wallet_address:
        order.wallet_address = wallet_address
    db.session.commit()

    # 通过 Socket.IO 推送给前端
    socketio.emit('deploy_status_update', {
        'order_id': order_id,
        'deploy_status': deploy_status,
        'token_address': token_address,
        'wallet_address': wallet_address,
        'error': error
    }, room=order_id)

    return jsonify({"message": "通知成功"}), 200


# -------------------------------
# 6️ Socket.IO 事件处理 - 放在文件最后
# -------------------------------
@socketio.on('connect')
def handle_connect():
    """客户端连接事件"""
    print(f"客户端连接: {request.sid}")


@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开事件"""
    print(f"客户端断开: {request.sid}")


@socketio.on('subscribe_orders')
def handle_subscribe_orders(order_ids):
    """客户端订阅订单状态更新"""
    from flask_socketio import join_room
    for order_id in order_ids:
        join_room(order_id)
        print(f"客户端 {request.sid} 订阅订单 {order_id}")


@socketio.on('join')
def on_join(data):
    job_id = data.get('job_id')
    if job_id:
        join_room(job_id)
        print(f"客户端 {request.sid} 加入房间 {job_id}")

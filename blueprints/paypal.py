# paypal.py
from flask import Blueprint, request, jsonify
from extensions import db, tx_queue, redis_conn, socketio
from models import PayPalOrder, PaymentStatusEnum, DeployStatusEnum
from utils.tx_jobs import deploy_contract
from flask_socketio import join_room, leave_room
from rq.job import Job
from rq.registry import StartedJobRegistry
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

    # 检查订单是否已存在
    order = PayPalOrder.query.filter_by(order_id=order_id).first()
    if order:
        # 检查订单状态，避免重复处理
        if order.payment_status == PaymentStatusEnum.paid:
            print(f"订单 {order_id} 已支付完成，跳过重复处理")
            return jsonify({"message": "订单已存在且已支付", "order_id": order.order_id}), 200
        else:
            # 如果订单存在但未支付，更新状态
            order.payment_status = PaymentStatusEnum.paid
            order.deploy_status = DeployStatusEnum.pending
            db.session.commit()
            print(f"更新订单 {order_id} 状态为已支付")
            return jsonify({"message": "订单状态已更新", "order_id": order.order_id}), 200

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
            user_id=data.get("user_id"),
            token_name=data.get("token_name", "UserCoin"),
            symbol=data.get("symbol", "UC"),
            supply=int(data.get("supply", 1000000)),
            amount=float(amount_value),
            payment_status=PaymentStatusEnum.paid,
            deploy_status=DeployStatusEnum.pending
        )
        db.session.add(order)
        db.session.commit()
        print(f"创建新订单 {order_id}")
    except Exception as e:
        print(f"数据库保存失败: {e}")
        return jsonify({"error": f"数据库保存失败: {e}"}), 500

    # 返回 order_id 给前端
    return jsonify({"message": "支付记录保存成功", "order_id": order.order_id}), 200


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
# 检查订单是否正在处理中
# -------------------------------
def is_order_processing(order_id):
    """检查订单是否已经有正在处理的任务"""
    try:
        # 检查已开始的任务注册表
        registry = StartedJobRegistry('tx_queue', connection=redis_conn)
        started_job_ids = registry.get_job_ids()

        # 检查队列中的任务
        queued_jobs = tx_queue.get_job_ids()

        all_job_ids = started_job_ids + queued_jobs

        for job_id in all_job_ids:
            try:
                job = Job.fetch(job_id, connection=redis_conn)
                # 检查任务参数中是否包含当前订单ID
                if job.args and len(job.args) >= 1 and job.args[0] == order_id:
                    print(f"订单 {order_id} 已有处理中的任务: {job_id}")
                    return True
            except Exception as e:
                print(f"检查任务 {job_id} 时出错: {e}")
                continue

        return False
    except Exception as e:
        print(f"检查订单处理状态时出错: {e}")
        return False


# -------------------------------
# 4️⃣ 用户绑定钱包并 mint（入队异步）- 修复重复入队问题
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
        payment_status=PaymentStatusEnum.paid
    ).first()

    if not order:
        return jsonify({"error": "未找到已支付的订单"}), 404

    # 检查订单是否已经在处理中
    if is_order_processing(order_id):
        return jsonify({"error": "该订单正在处理中，请勿重复提交"}), 409

    # 检查订单状态，避免重复部署
    if order.deploy_status != DeployStatusEnum.pending:
        current_status = order.deploy_status.value
        if current_status == 'success':
            return jsonify({"error": "该订单已部署成功，不可重复部署"}), 409
        elif current_status == 'failed':
            # 允许失败的订单重新部署
            print(f"订单 {order_id} 之前部署失败，允许重新部署")
        else:
            return jsonify({"error": f"订单当前状态为 {current_status}，不可重复部署"}), 409

    print(f"开始处理订单 {order_id}，钱包地址: {wallet_address}")

    try:
        # ✅ 修复：只入队一次，传递正确的参数
        job = tx_queue.enqueue(
            deploy_contract,
            order_id,
            wallet_address,
            job_timeout=600  # 设置超时时间
        )

        print(f"订单 {order_id} 已加入队列，任务ID: {job.id}")

        # 立即更新订单状态为处理中，防止重复提交
        order.deploy_status = DeployStatusEnum.processing
        order.wallet_address = wallet_address
        db.session.commit()

    except Exception as e:
        print(f"入队任务失败: {e}")
        return jsonify({"error": f"任务入队失败: {e}"}), 500

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

    print(f"订单 {order_id} 部署完成，状态: {deploy_status}")

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
# 7️ Socket.IO 事件处理 - 放在文件最后
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
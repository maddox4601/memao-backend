from flask import Blueprint, request, jsonify
from extensions import db
from models import PayPalOrder, PaymentStatusEnum, DeployStatusEnum
import requests
from web3 import Web3
import os,json

paypal_bp = Blueprint("paypal", __name__, url_prefix="/api/paypal")

PAYPAL_API = os.getenv("PAYPAL_API")  # 沙箱环境，正式环境改为 https://api-m.paypal.com
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_SECRET = os.getenv("PAYPAL_SECRET")

# -------------------------------
# 1️⃣ capture & 验证 PayPal 订单
# -------------------------------
def verify_paypal_order(order_id):
    """调用 PayPal API 捕获并验证订单是否完成支付"""
    print(f"[verify_paypal_order] 开始校验并 capture order_id={order_id}")

    # 1️⃣ 获取 Access Token
    auth_resp = requests.post(
        f"{PAYPAL_API}/v1/oauth2/token",
        auth=(PAYPAL_CLIENT_ID, PAYPAL_SECRET),
        data={"grant_type": "client_credentials"}
    )
    print(f"[verify_paypal_order] 获取 token 返回码={auth_resp.status_code}, body={auth_resp.text}")
    if auth_resp.status_code != 200:
        return False, "无法获取 PayPal token"

    access_token = auth_resp.json().get("access_token")

    # 2️⃣ 捕获订单（capture）
    capture_resp = requests.post(
        f"{PAYPAL_API}/v2/checkout/orders/{order_id}/capture",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }
    )
    print(f"[verify_paypal_order] capture 返回码={capture_resp.status_code}, body={capture_resp.text}")
    if capture_resp.status_code not in (200, 201):
        return False, f"订单 capture 失败: {capture_resp.text}"

    capture_data = capture_resp.json()
    print(f"[verify_paypal_order] capture 结果解析={capture_data}")

    # 3️⃣ 检查 capture 状态
    status = capture_data.get("status")
    if status != "COMPLETED":
        return False, f"支付未完成，状态: {status}"

    return True, capture_data


# -------------------------------
# 支付完成回调
# -------------------------------
@paypal_bp.route("/payment-complete", methods=["POST"])
def payment_complete():
    data = request.json
    print(f"[payment_complete] 收到前端请求: {data}")

    order_id = data.get("order_id")
    if not order_id:
        print("[payment_complete] 缺少 order_id")
        return jsonify({"error": "order_id 必填"}), 400

    # 先检查数据库是否存在该订单
    order = PayPalOrder.query.filter_by(order_id=order_id).first()
    if order:
        print(f"[payment_complete] 订单已存在: {order_id}")
        return jsonify({"message": "订单已存在"}), 200

    # 调用 PayPal API capture & 验证订单
    success, result = verify_paypal_order(order_id)
    if not success:
        print(f"[payment_complete] 支付验证失败: {result}")
        return jsonify({"error": f"支付验证失败: {result}"}), 400

    print(f"[payment_complete] 验证成功，准备保存订单: {result}")

    try:
        capture = result["purchase_units"][0]["payments"]["captures"][0]
        amount_value = float(capture["amount"]["value"])  # 支付金额
        currency = capture["amount"]["currency_code"] #币种信息

        EXPECTED_PRICE = float(os.getenv("TOKEN_PRICE", "0.01"))  # 配置或数据库里定义
        EXPECTED_CURRENCY = os.getenv("TOKEN_CURRENCY", "USD")

        # ✅ 校验金额和币种
        if amount_value != EXPECTED_PRICE or currency != EXPECTED_CURRENCY:
            print(
                f"[payment_complete] 金额或币种不匹配: paid={amount_value}{currency}, expected={EXPECTED_PRICE}{EXPECTED_CURRENCY}")
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
        print(f"[payment_complete] 保存成功: order_id={order_id}")
    except Exception as e:
        print(f"[payment_complete] 数据库保存失败: {e}")
        return jsonify({"error": "数据库保存失败"}), 500

    return jsonify({"message": "支付记录保存成功"}), 200


# -------------------------------
# 2️⃣ 查询未绑定钱包的订单列表
# -------------------------------
@paypal_bp.route("/pending-orders", methods=["GET"])
def get_pending_orders():
    """
    查询未绑定钱包的订单
    GET 参数: 可选 payment_email 或 order_id
    """
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
        }
        for o in orders
    ]
    return jsonify(result), 200


# -------------------------------
# 3️⃣ 用户绑定钱包并 mint
# -------------------------------

# 读取环境变量
WEB3_PROVIDER = os.getenv('WEB3_PROVIDER')
FACTORY_CONTRACT_ADDRESS = os.getenv('FACTORY_ADDRESS')
PLATFORM_WALLET = os.getenv("DEV_WALLET_ADDRESS")
PLATFORM_PRIVATE_KEY = os.getenv("DEV_PRIVATE_KEY")

if not WEB3_PROVIDER:
    raise RuntimeError("Missing WEB3_PROVIDER environment variable")
if not FACTORY_CONTRACT_ADDRESS:
    raise RuntimeError("Missing FACTORY_CONTRACT_ADDRESS environment variable")
if not PLATFORM_WALLET:
    raise RuntimeError("Missing DEV_WALLET_ADDRESS environment variable")
if not PLATFORM_PRIVATE_KEY:
    raise RuntimeError("Missing DEV_PRIVATE_KEY environment variable")

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# 转换为 checksum address
FACTORY_CONTRACT_ADDRESS = Web3.to_checksum_address(FACTORY_CONTRACT_ADDRESS)
PLATFORM_WALLET = Web3.to_checksum_address(PLATFORM_WALLET)

# 当前文件目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# abis目录（相对上级目录）
ABIS_DIR = os.path.join(BASE_DIR, '..', 'abis')

# 读取 TokenFactory ABI
with open(os.path.join(ABIS_DIR, 'TokenFactory.json'), 'r') as f:
    full_json = json.load(f)
FACTORY_ABI = full_json['abi']

factory_contract = w3.eth.contract(address=FACTORY_CONTRACT_ADDRESS, abi=FACTORY_ABI)


@paypal_bp.route("/bind-wallet", methods=["POST"])
def bind_wallet():
    data = request.json
    order_id = data.get("order_id")
    wallet_address = data.get("wallet_address")
    if not order_id or not wallet_address:
        return jsonify({"error": "order_id 和 wallet_address 必填"}), 400

    # 转换用户钱包地址为 checksum 格式
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

    try:
        # ===== 1. 构建链上交易 =====
        nonce = w3.eth.get_transaction_count(PLATFORM_WALLET)

        # 预估 gas
        gas_estimate = factory_contract.functions.platformDeploy(
            order.token_name,
            order.symbol,
            order.supply,
            wallet_address
        ).estimate_gas({"from": Web3.to_checksum_address(PLATFORM_WALLET)})

        # 获取 EIP-1559 动态费用
        latest_block = w3.eth.get_block("latest")
        base_fee = latest_block.get("baseFeePerGas", 0)
        priority_fee = w3.to_wei("2", "gwei")
        max_fee_per_gas = base_fee + priority_fee

        # 构建交易
        tx = factory_contract.functions.platformDeploy(
            order.token_name,
            order.symbol,
            order.supply,
            wallet_address
        ).build_transaction({
            "from": PLATFORM_WALLET,
            "nonce": nonce,
            "gas": int(gas_estimate * 1.2),
            "maxFeePerGas": max_fee_per_gas,
            "maxPriorityFeePerGas": priority_fee,
        })

        # ===== 2. 平台签名并发送交易 =====
        signed_tx = w3.eth.account.sign_transaction(tx, private_key=PLATFORM_PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # ===== 3. 等待交易确认 =====
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        # ===== 4. 解析 TokenCreated 事件 =====
        token_address = None
        for log in factory_contract.events.TokenCreated().process_receipt(receipt):
            token_address = log["args"]["tokenAddress"]
            break

        if not token_address:
            return jsonify({"error": "未能获取到新 Token 地址"}), 500

        # ===== 5. 更新数据库 =====
        order.wallet_address = wallet_address
        order.contract_address = token_address
        order.deploy_status = DeployStatusEnum.success
        order.minted = True
        db.session.commit()

        return jsonify({
            "message": "代币已成功生成并发送到用户钱包",
            "tokenAddress": token_address,
            "txHash": tx_hash.hex()
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500




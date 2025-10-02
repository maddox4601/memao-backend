# utils/tx_jobs.py
import os
import json
import requests
from web3 import Web3
from extensions import db
from models import PayPalOrder, DeployStatusEnum

# ----------------- Web3 初始化 -----------------
WEB3_PROVIDER = os.getenv('WEB3_PROVIDER')
FACTORY_CONTRACT_ADDRESS = Web3.to_checksum_address(os.getenv('FACTORY_ADDRESS'))
PLATFORM_WALLET = Web3.to_checksum_address(os.getenv("DEV_WALLET_ADDRESS"))
PLATFORM_PRIVATE_KEY = os.getenv("DEV_PRIVATE_KEY")

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# 读取 TokenFactory ABI
with open(os.path.join(os.path.dirname(__file__), '..', 'abis', 'TokenFactory.json'), 'r') as f:
    full_json = json.load(f)
FACTORY_ABI = full_json['abi']

factory_contract = w3.eth.contract(address=FACTORY_CONTRACT_ADDRESS, abi=FACTORY_ABI)

# ----------------- 主服务接口 -----------------
MAIN_SERVER_URL = os.getenv("MAIN_SERVER_URL")  # e.g., http://localhost:5000

def notify_deploy_complete(order_id, data):
    """
    调用主服务接口通知前端部署完成
    """
    url = f"{MAIN_SERVER_URL}/api/paypal/notify-deploy-complete"
    payload = {"order_id": order_id, **data}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.status_code == 200:
            print(f"[notify_deploy_complete] 通知成功: {resp.json()}")
        else:
            print(f"[notify_deploy_complete] 通知失败: {resp.status_code}, {resp.text}")
    except Exception as e:
        print(f"[notify_deploy_complete] 调用异常: {e}")

# ----------------- 异步任务 -----------------
def deploy_contract(order_id, wallet_address, job_id=None):
    """
    异步部署合约任务，支持独立容器和 HTTP 通知前端
    """
    try:
        # 🔹 延迟导入 create_app，解决 app_context 问题
        from app import create_app
        app = create_app()

        with app.app_context():
            order = PayPalOrder.query.filter_by(order_id=order_id).first()
            if not order:
                print(f"[deploy_contract] 订单 {order_id} 不存在")
                return

            # 更新状态为 pending
            order.deploy_status = DeployStatusEnum.pending
            order.wallet_address = wallet_address
            db.session.commit()
            print(f"[deploy_contract] 订单 {order_id} 开始部署")

            # 查询 nonce
            nonce = w3.eth.get_transaction_count(PLATFORM_WALLET)

            # 估算 gas
            gas_estimate = factory_contract.functions.platformDeploy(
                order.token_name,
                order.symbol,
                order.supply,
                wallet_address
            ).estimate_gas({"from": PLATFORM_WALLET})

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

            # 签名并发送
            signed_tx = w3.eth.account.sign_transaction(tx, private_key=PLATFORM_PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"[deploy_contract] 订单 {order_id} 交易已发送: {tx_hash.hex()}")

            # 等待确认
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            print(f"[deploy_contract] 订单 {order_id} 交易已确认，区块: {receipt.blockNumber}")

            # 获取 Token 地址
            token_address = None
            for log in factory_contract.events.TokenCreated().process_receipt(receipt):
                token_address = log["args"]["tokenAddress"]
                break

            if token_address:
                order.contract_address = token_address
                order.deploy_status = DeployStatusEnum.success
                order.minted = True
                db.session.commit()
                notify_deploy_complete(order_id, {
                    "deploy_status": "success",
                    "token_address": token_address,
                    "wallet_address": wallet_address,
                    "tx_hash": tx_hash.hex()
                })
                print(f"[deploy_contract] 订单 {order_id} 部署成功，Token 地址: {token_address}")
            else:
                order.deploy_status = DeployStatusEnum.failed
                db.session.commit()
                notify_deploy_complete(order_id, {
                    "deploy_status": "failed",
                    "error": "未找到 Token 地址，请检查合约事件",
                    "wallet_address": wallet_address
                })
                print(f"[deploy_contract] 订单 {order_id} 部署失败：未找到 Token 地址")

    except Exception as e:
        error_msg = str(e)
        print(f"[deploy_contract] 订单 {order_id} 异常: {error_msg}")
        try:
            with app.app_context():
                order = PayPalOrder.query.filter_by(order_id=order_id).first()
                if order:
                    order.deploy_status = DeployStatusEnum.failed
                    db.session.commit()
                    notify_deploy_complete(order_id, {
                        "deploy_status": "failed",
                        "error": error_msg,
                        "wallet_address": wallet_address
                    })
        except Exception as inner_e:
            print(f"[deploy_contract] 异常处理时出错: {inner_e}")

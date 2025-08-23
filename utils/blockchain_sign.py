import os
from web3 import Web3
from eth_account import Account
from decimal import Decimal
from eth_account.messages import encode_defunct
from flask import current_app
from extensions import db
from models import WalletUser, WithdrawalHistory  # 请替换为你的实际导入路径
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, timezone

PRIVATE_KEY = os.getenv('COMMUNITY_PRIVATE_KEY')

if not PRIVATE_KEY:
    raise ValueError("COMMUNITY_PRIVATE_KEY not found in environment variables")


def sign_withdrawal(wallet_address: str, amount_points: Decimal, nonce: int) -> str:
    try:
        # 计算签名数据，与前端/合约保持一致
        amount_wei = int(amount_points * Decimal(10 ** 18))  # 转换成wei单位
        addr = wallet_address.lower()
        if addr.startswith("0x"):
            addr = addr[2:]
        message = f"{addr}:{amount_wei}:{nonce}"

        current_app.logger.info(f"Raw message to sign: '{message}'")

        message_bytes = message.encode('utf-8')
        message_hash = Web3.keccak(message_bytes)
        current_app.logger.info(f"Message hash: {message_hash.hex()}")

        signable_message = encode_defunct(primitive=message_hash)
        current_app.logger.info(f"Signable message hash: {Web3.keccak(signable_message.body).hex()}")

        signed_message = Account.sign_message(signable_message, private_key=PRIVATE_KEY)

        recovered_address = Account.recover_message(signable_message, signature=signed_message.signature)
        expected_address = Account.from_key(PRIVATE_KEY).address
        current_app.logger.info(f"Recovered address: {recovered_address}")
        current_app.logger.info(f"Expected signer: {expected_address}")

        if recovered_address.lower() != expected_address.lower():
            raise ValueError("Recovered address does not match signer")

        return signed_message.signature.hex()

    except Exception as e:
        current_app.logger.error(f"Signature generation failed: {e}")
        raise RuntimeError(f"Signature generation failed: {e}")


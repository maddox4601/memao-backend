from web3 import Web3
import json
import os
import traceback
from web3.exceptions import ContractLogicError
from dotenv import load_dotenv
from models import AirdropConfig

# 加载 .env 配置
load_dotenv()

# 环境变量
WEB3_PROVIDER = os.getenv('WEB3_PROVIDER')
DEV_PRIVATE_KEY = os.getenv('DEV_PRIVATE_KEY')
AIRDROP_CONTRACT_ADDRESS = os.getenv('AIRDROP_CONTRACT_ADDRESS')
COMMUNITY_PRIVATE_KEY = os.getenv('COMMUNITY_PRIVATE_KEY')
MEMAO_TOKEN_ADDRESS = os.getenv('MEMAO_TOKEN_ADDRESS')

# 连接区块链
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# ABI 路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ABIS_DIR = os.path.join(BASE_DIR, '..', 'abis')

# 加载 Airdrop 合约 ABI
with open(os.path.join(ABIS_DIR, 'Airdrop_ABI.json'), 'r') as f:
    AIRDROP_ABI = json.load(f)

with open(os.path.join(ABIS_DIR, 'MEMAO_ABI.json'), 'r') as f:
    ERC20_ABI = json.load(f)
def get_airdrop_amount_from_config():
    config = AirdropConfig.query.first()
    if config and config.airdrop_amount:
        return int(config.airdrop_amount)
    return 0  # 默认 0 wei
def blockchain_batch_airdrop(recipients,amount):
    try:
        recipients = [w3.to_checksum_address(addr) for addr in recipients]

        community_account = w3.eth.account.from_key(COMMUNITY_PRIVATE_KEY)
        dev_account = w3.eth.account.from_key(DEV_PRIVATE_KEY)

        # 加载代币合约
        token_contract = w3.eth.contract(address=MEMAO_TOKEN_ADDRESS, abi=ERC20_ABI)
        airdrop_contract = w3.eth.contract(address=AIRDROP_CONTRACT_ADDRESS, abi=AIRDROP_ABI)

        # 读取数据库空投数量（int）
        airdrop_amount = get_airdrop_amount_from_config()
        amounts = [airdrop_amount for _ in recipients]

        total_amount = airdrop_amount * len(recipients)

        # Step 1: Approve 授权空投合约从 community_account 扣代币
        print(f"Starting approve for total amount: {total_amount}")
        nonce = w3.eth.get_transaction_count(community_account.address)
        approve_tx = token_contract.functions.approve(AIRDROP_CONTRACT_ADDRESS, total_amount)
        gas_estimate = approve_tx.estimate_gas({'from': community_account.address})
        approve_tx_build = approve_tx.build_transaction({
            'from': community_account.address,
            'nonce': nonce,
            'gas': gas_estimate + 10000,
            'maxFeePerGas': w3.to_wei('10', 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei('2', 'gwei'),
        })
        signed_approve_tx = w3.eth.account.sign_transaction(approve_tx_build, private_key=COMMUNITY_PRIVATE_KEY)
        approve_tx_hash = w3.eth.send_raw_transaction(signed_approve_tx.raw_transaction)
        print(f"Approve transaction sent: {w3.to_hex(approve_tx_hash)}")
        w3.eth.wait_for_transaction_receipt(approve_tx_hash)
        print("Approve transaction confirmed.")

        # Step 2: 执行空投
        nonce = w3.eth.get_transaction_count(dev_account.address)
        batch_airdrop_tx = airdrop_contract.functions.airdrop(recipients, amounts)
        gas_estimate = batch_airdrop_tx.estimate_gas({'from': dev_account.address})
        batch_airdrop_tx_build = batch_airdrop_tx.build_transaction({
            'from': dev_account.address,
            'nonce': nonce,
            'gas': gas_estimate + 10000,
            'maxFeePerGas': w3.to_wei('10', 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei('2', 'gwei'),
        })
        signed_airdrop_tx = w3.eth.account.sign_transaction(batch_airdrop_tx_build, private_key=DEV_PRIVATE_KEY)
        airdrop_tx_hash = w3.eth.send_raw_transaction(signed_airdrop_tx.raw_transaction)
        print(f"Airdrop transaction sent: {w3.to_hex(airdrop_tx_hash)}")
        w3.eth.wait_for_transaction_receipt(airdrop_tx_hash)
        print("Airdrop transaction confirmed.")

        return True

    except ContractLogicError as logic_error:
        print(f"Contract logic error: {logic_error}")
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"Airdrop transaction failed: {str(e)}")
        traceback.print_exc()
        return False



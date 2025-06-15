from web3 import Web3
import json
import os
import traceback
from web3.exceptions import ContractLogicError
from dotenv import load_dotenv

# 加载 .env 配置
load_dotenv()

# 读取环境变量
WEB3_PROVIDER = os.getenv('WEB3_PROVIDER')
COMMUNITY_PRIVATE_KEY = os.getenv('COMMUNITY_PRIVATE_KEY')
DEV_PRIVATE_KEY = os.getenv('DEV_PRIVATE_KEY')
AIRDROP_CONTRACT_ADDRESS = os.getenv('AIRDROP_CONTRACT_ADDRESS')
MEMAO_TOKEN_ADDRESS = os.getenv('MEMAO_TOKEN_ADDRESS')

# 连接区块链
w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 当前文件目录
ABIS_DIR = os.path.join(BASE_DIR, '..', 'abis')       # abis 目录

with open(os.path.join(ABIS_DIR, 'Airdrop_ABI.json'), 'r') as f:
    AIRDROP_ABI = json.load(f)

with open(os.path.join(ABIS_DIR, 'MEMAO_ABI.json'), 'r') as f:
    ERC20_ABI = json.load(f)


def blockchain_batch_transfer(recipients, amounts):
    """
    批量转账函数，调用链上合约进行转账操作。
    recipients: list of str (钱包地址)
    amounts: list of int or str (对应的转账金额，单位根据合约)
    返回: True 表示成功或已知交易，False 表示失败
    """
    try:
        recipients = [w3.to_checksum_address(addr) for addr in recipients]
        community_account = w3.eth.account.from_key(COMMUNITY_PRIVATE_KEY)
        dev_account = w3.eth.account.from_key(DEV_PRIVATE_KEY)
        memao_token = w3.eth.contract(address=MEMAO_TOKEN_ADDRESS, abi=ERC20_ABI)
        airdrop_contract = w3.eth.contract(address=AIRDROP_CONTRACT_ADDRESS, abi=AIRDROP_ABI)
        total_amount = sum(int(amount) for amount in amounts)

        # Step 1: Approve
        try:
            print(f"Starting approve step for total amount: {total_amount}")
            nonce = w3.eth.get_transaction_count(community_account.address)
            approve_tx = memao_token.functions.approve(AIRDROP_CONTRACT_ADDRESS, total_amount)
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
        except Exception as approve_error:
            print("Approve step failed!")
            print(f"Error: {str(approve_error)}")
            traceback.print_exc()
            return False

        # Step 2: Airdrop
        try:
            print(f"Starting airdrop step for recipients: {recipients} with amounts: {amounts}")
            nonce = w3.eth.get_transaction_count(dev_account.address)
            airdrop_tx = airdrop_contract.functions.airdrop(recipients, [int(amount) for amount in amounts])
            gas_estimate = airdrop_tx.estimate_gas({'from': dev_account.address})
            airdrop_tx_build = airdrop_tx.build_transaction({
                'from': dev_account.address,
                'nonce': nonce,
                'gas': gas_estimate + 10000,
                'maxFeePerGas': w3.to_wei('10', 'gwei'),
                'maxPriorityFeePerGas': w3.to_wei('2', 'gwei'),
            })
            signed_airdrop_tx = w3.eth.account.sign_transaction(airdrop_tx_build, private_key=DEV_PRIVATE_KEY)
            airdrop_tx_hash = w3.eth.send_raw_transaction(signed_airdrop_tx.raw_transaction)
            print(f"Airdrop transaction sent: {w3.to_hex(airdrop_tx_hash)}")
            w3.eth.wait_for_transaction_receipt(airdrop_tx_hash)
            print("Airdrop completed successfully.")
            return True
        except Exception as airdrop_error:
            print("Airdrop step failed!")
            print(f"Error: {str(airdrop_error)}")
            traceback.print_exc()
            return False

    except Exception as e:
        error_message = str(e)
        if 'already known' in error_message:
            print("Transaction already known, likely pending in mempool. Treating as success.")
            return True
        else:
            print(f"Blockchain transaction failed: {error_message}")
            traceback.print_exc()
            return False

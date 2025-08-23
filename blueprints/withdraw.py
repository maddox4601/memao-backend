import os,json
from web3 import Web3
from flask import current_app
from flask import Blueprint, request, jsonify
from extensions import db
from models import WalletUser, WithdrawalHistory,UserPointsAccount,PointsHistory
from datetime import datetime, timezone
from decimal import Decimal
from utils.blockchain_batch_transfer import blockchain_batch_withdraw
from utils.blockchain_sign import sign_withdrawal  # 你需要实现签名逻辑
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_

withdraw_bp = Blueprint('withdraw', __name__, url_prefix='/api/withdraw')


# 读取环境变量
WEB3_PROVIDER = os.getenv('WEB3_PROVIDER')
WITHDRAW_CONTRACT_ADDRESS = os.getenv('WITHDRAW_CONTRACT_ADDRESS')

if not WEB3_PROVIDER:
    raise RuntimeError("Missing WEB3_PROVIDER environment variable")
if not WITHDRAW_CONTRACT_ADDRESS:
    raise RuntimeError("Missing WITHDRAW_CONTRACT_ADDRESS environment variable")

w3 = Web3(Web3.HTTPProvider(WEB3_PROVIDER))

# 当前文件目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# abis目录（相对上级目录）
ABIS_DIR = os.path.join(BASE_DIR, '..', 'abis')

# 读取Withdraw合约ABI
with open(os.path.join(ABIS_DIR, 'WithdrawWithSignature.json'), 'r') as f:
    full_json = json.load(f)
WithdrawContractABI = full_json['abi']


#version：v1 platform pay gas
@withdraw_bp.route('', methods=['POST'])
def withdraw_points():
    data = request.get_json()
    wallet_address = data.get('walletAddress')
    amount = data.get('amount')

    if not wallet_address or amount is None:
        return jsonify({'success': False, 'message': 'Missing wallet address or amount'}), 400

    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({'success': False, 'message': 'Wallet address not found'}), 404

    user_account = user.points_account
    if not user_account or user_account.total_points < amount:
        return jsonify({'success': False, 'message': 'Insufficient points'}), 400

    if amount < 100:
        return jsonify({'success': False, 'message': 'Minimum withdrawal amount is 100 points'}), 400

    # 扣除积分，记录提现申请
    user_account.total_points -= amount
    withdrawal = WithdrawalHistory(
        wallet_user_id=user.id,
        amount=amount,
        requested_at=datetime.now(timezone.utc),
        status='pending'
    )

    try:
        db.session.add(withdrawal)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Withdrawal request submitted'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Database error'}), 500


@withdraw_bp.route('/history', methods=['GET'])
def get_withdrawal_history():
    wallet_address = request.args.get('walletAddress')
    page = request.args.get('page', default=1, type=int)
    limit = request.args.get('limit', default=5, type=int)

    # 验证参数
    if not wallet_address:
        return jsonify({'success': False, 'message': 'Missing wallet address'}), 400

    if page < 1 or limit < 1:
        return jsonify({'success': False, 'message': 'Invalid pagination parameters'}), 400

    # 查询用户
    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({'success': False, 'message': 'Wallet address not found'}), 404

    # 计算分页偏移量
    offset = (page - 1) * limit

    # 查询总记录数
    total = WithdrawalHistory.query.filter_by(wallet_user_id=user.id).count()

    # 查询分页数据
    history_query = WithdrawalHistory.query.filter_by(wallet_user_id=user.id) \
        .order_by(WithdrawalHistory.requested_at.desc()) \
        .offset(offset) \
        .limit(limit)

    history = history_query.all()

    history_data = []
    for record in history:
        history_data.append({
            'id': record.id,
            'amount': str(record.amount),
            'requested_at': record.requested_at.astimezone(timezone.utc).isoformat(),
            'status': record.status
        })

    return jsonify({
        'success': True,
        'history': history_data,
        'total': total,  # 添加总记录数用于前端计算总页数
        'page': page,
        'limit': limit
    })

@withdraw_bp.route('/process', methods=['POST'])
def manual_process_withdrawals():
    try:
        process_withdrawals()
        return jsonify({'success': True, 'message': 'Withdrawals processed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Processing failed: {str(e)}'}), 500


BATCH_SIZE = 20
def process_withdrawals():
    # 拉取所有 pending，没限制也行，或者加 limit 防止一次太多
    pending_withdrawals = WithdrawalHistory.query.filter_by(status='pending').order_by(WithdrawalHistory.requested_at.asc()).limit(1000).all()

    if not pending_withdrawals:
        print("No pending withdrawals.")
        return

    total = len(pending_withdrawals)
    print(f"Total pending withdrawals fetched: {total}")

    for i in range(0, total, BATCH_SIZE):
        batch = pending_withdrawals[i:i+BATCH_SIZE]

        recipients = []
        amounts_wei = []
        withdrawal_ids = []

        for wd in batch:
            user = WalletUser.query.get(wd.wallet_user_id)
            if user:
                recipients.append(user.wallet_address)
                amounts_wei.append(int(Decimal(str(wd.amount)) * Decimal(10 ** 18)))
                withdrawal_ids.append(wd.id)

        print(f"Processing batch {i//BATCH_SIZE + 1} with {len(recipients)} withdrawals: {list(zip(recipients, amounts_wei))}")

        try:
            success = blockchain_batch_withdraw(recipients, amounts_wei)  # 调用区块链批量提现接口

            if success:
                print(f"Batch {i//BATCH_SIZE + 1} processed successfully, updating DB...")
                try:
                    for withdrawal_id in withdrawal_ids:
                        wd_record = WithdrawalHistory.query.get(withdrawal_id)
                        if wd_record:
                            wd_record.status = 'completed'
                    db.session.commit()
                except Exception as db_error:
                    print(f"Database update error in batch {i//BATCH_SIZE + 1}: {str(db_error)}")
                    db.session.rollback()
            else:
                print(f"Blockchain transfer failed in batch {i//BATCH_SIZE + 1}, will retry later.")
                # 失败不更新，下一次任务重试

        except Exception as e:
            print(f"Blockchain transaction error in batch {i//BATCH_SIZE + 1}: {str(e)}")
            db.session.rollback()


#version：v2 user pay gas

#/withdraw/apply — 创建提现申请（不扣积分）
@withdraw_bp.route('/apply', methods=['POST'])
def apply_withdraw():
    data = request.get_json()
    wallet_address = data.get('walletAddress')
    amount = Decimal(str(data.get('amount', '0')))

    if not wallet_address or amount <= 0:
        return jsonify({'success': False, 'message': 'Missing wallet address or invalid amount'}), 400

    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({'success': False, 'message': 'Wallet address not found'}), 404

    try:
        user_account = (
            UserPointsAccount.query
            .filter_by(wallet_user_id=user.id)
            .with_for_update()
            .first()
        )
        if not user_account or user_account.total_points < amount:
            return jsonify({'success': False, 'message': 'Insufficient points'}), 400

        if amount < 100:
            return jsonify({'success': False, 'message': 'Minimum withdrawal amount is 100 points'}), 400

        # 创建 pending 提现记录
        withdraw_record = WithdrawalHistory(
            wallet_user_id=user.id,
            amount=amount,
            status='pending',
            requested_at=datetime.now(timezone.utc)
        )
        db.session.add(withdraw_record)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Withdrawal request created',
            'withdrawal_id': withdraw_record.id
        })
    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"DB error in apply_withdraw: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500


# /withdraw/signature — 生成链上签名
@withdraw_bp.route('/signature', methods=['POST'])
def get_withdraw_signature():
    data = request.get_json()
    wallet_address = data.get('walletAddress')
    withdrawal_id = data.get('withdrawalId')

    if not wallet_address or not withdrawal_id:
        return jsonify({'success': False, 'message': 'Missing wallet address or withdrawalId'}), 400

    try:
        with db.session.begin_nested():
            user = (
                WalletUser.query
                .filter_by(wallet_address=wallet_address)
                .with_for_update()
                .first()
            )
            if not user:
                return jsonify({'success': False, 'message': 'Wallet address not found'}), 404

            user_account = (
                UserPointsAccount.query
                .filter_by(wallet_user_id=user.id)
                .with_for_update()
                .first()
            )
            if not user_account:
                return jsonify({'success': False, 'message': 'User points account not found'}), 404

            withdraw_record = (
                WithdrawalHistory.query
                .filter_by(id=withdrawal_id, wallet_user_id=user.id, status='pending')
                .with_for_update()
                .first()
            )
            if not withdraw_record:
                return jsonify({'success': False, 'message': 'No pending withdrawal found'}), 404

            amount = withdraw_record.amount

            if user_account.total_points < amount:
                return jsonify({'success': False, 'message': 'Insufficient points'}), 400

            # 获取链上 nonce 和数据库 nonce
            chain_nonce = sync_nonce_from_chain(wallet_address)
            db_nonce = user_account.withdraw_nonce

            # ========================
            # 自动同步逻辑
            # ========================
            if chain_nonce == 0 and db_nonce > 0:
                # 合约升级，重置本地 nonce
                current_app.logger.warning(
                    f"Contract reset detected for {wallet_address}, resetting db_nonce from {db_nonce} to 0"
                )
                user_account.withdraw_nonce = 0
                db.session.commit()
                db_nonce = 0

            elif db_nonce < chain_nonce:
                # 本地落后，强制追赶链上
                current_app.logger.warning(
                    f"Nonce mismatch: db={db_nonce}, chain={chain_nonce}, syncing to chain"
                )
                user_account.withdraw_nonce = chain_nonce
                db.session.commit()
                db_nonce = chain_nonce

            elif db_nonce > chain_nonce:
                # 数据库超前，不允许签名，报警
                current_app.logger.error(
                    f"DB nonce ahead of chain for {wallet_address}: db={db_nonce}, chain={chain_nonce}"
                )
                return jsonify({
                    'success': False,
                    'message': f"Nonce mismatch: db={db_nonce}, chain={chain_nonce}. Please contact support.",
                    'nonce': db_nonce,
                    'chain_nonce': chain_nonce,
                    'is_nonce_synced': False
                }), 400

            print("chain_nonce,db_nonce", chain_nonce, db_nonce)

            # 生成签名（不扣积分）
            signature = sign_withdrawal(wallet_address, amount, db_nonce)

            current_app.logger.info(
                f"Signature generated - Address: {wallet_address}, Amount: {amount}, Nonce: {db_nonce}"
            )

            return jsonify({
                'success': True,
                'signature': signature,
                'nonce': db_nonce,
                'chain_nonce': chain_nonce,
                'is_nonce_synced': db_nonce == chain_nonce
            })

    except Exception as e:
        db.session.rollback()
        try:
            user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
            if user:
                withdraw_record = (
                    WithdrawalHistory.query
                    .filter_by(id=withdrawal_id, wallet_user_id=user.id, status='pending')
                    .first()
                )
                if withdraw_record:
                    withdraw_record.status = 'failed'
                    withdraw_record.processed_at = datetime.now(timezone.utc)
                    withdraw_record.remarks = f"Signature generation failed. Error: {str(e)}"
                    db.session.commit()
        except Exception as rollback_exc:
            current_app.logger.error(f"Failed to auto-fail withdrawal record on signature error: {rollback_exc}")

        current_app.logger.error(f"Unexpected error in signature: {str(e)}")
        return jsonify({'success': False, 'message': 'Internal server error'}), 500



# /withdraw/report — 上报链上执行结果
@withdraw_bp.route('/report', methods=['POST'])
def report_withdraw_result():
    data = request.get_json()
    wallet_address = data.get('walletAddress')
    withdrawal_id = data.get('withdrawalId')
    result = data.get('result')  # 'success' or 'failure'
    onchain_nonce = data.get('onchainNonce')
    tx_hash = data.get('txHash')
    remarks = data.get('remarks')

    if not wallet_address or not result or withdrawal_id is None or onchain_nonce is None:
        return jsonify({'success': False, 'message': 'Missing parameters'}), 400

    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({'success': False, 'message': 'Wallet address not found'}), 404

    try:
        user_account = (
            UserPointsAccount.query
            .filter_by(wallet_user_id=user.id)
            .with_for_update()
            .first()
        )
        if not user_account:
            return jsonify({'success': False, 'message': 'User points account not found'}), 404

        withdraw_record = (
            WithdrawalHistory.query
            .filter_by(id=withdrawal_id, wallet_user_id=user.id)
            .with_for_update()
            .first()
        )
        if not withdraw_record:
            return jsonify({'success': False, 'message': 'Withdrawal record not found'}), 404

        # 幂等：如果已经终态，直接返回
        if withdraw_record.status in ('completed', 'failed'):
            return jsonify({'success': True, 'message': f'Already {withdraw_record.status}', 'latest_nonce': user_account.withdraw_nonce})

        if result == 'success':
            amount = withdraw_record.amount

            if user_account.total_points < amount:
                return jsonify({'success': False, 'message': 'Insufficient points at confirm time'}), 400

            # 成功才扣分
            user_account.total_points -= amount
            points_history = PointsHistory(
                wallet_user_id=user.id,
                change_type="withdrawal_points",
                change_amount=-amount,
                created_at=datetime.now(timezone.utc),
                description=f"Deducted for MEMAO withdrawal -{amount}"
            )
            db.session.add(points_history)

            user_account.withdraw_nonce = onchain_nonce + 1

            withdraw_record.status = 'completed'
            withdraw_record.tx_hash = tx_hash
            withdraw_record.processed_at = datetime.now(timezone.utc)
            if remarks:
                withdraw_record.remarks = remarks

        elif result == 'failure':
            # 失败：不返还积分，只更新状态和 nonce
            user_account.withdraw_nonce = onchain_nonce
            withdraw_record.status = 'failed'
            withdraw_record.processed_at = datetime.now(timezone.utc)
            if remarks:
                withdraw_record.remarks = remarks
        else:
            return jsonify({'success': False, 'message': 'Invalid result value'}), 400

        db.session.commit()
        return jsonify({'success': True, 'message': 'Report recorded', 'latest_nonce': user_account.withdraw_nonce})

    except SQLAlchemyError as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to report withdraw result for {wallet_address}: {e}")
        return jsonify({'success': False, 'message': 'Database error'}), 500


def sync_nonce_from_chain(wallet_address: str) -> int:
    """
    增强版nonce同步方法
    返回：链上最新nonce
    异常：可能抛出区块链连接或数据库错误
    """
    try:
        # 获取链上nonce
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(WITHDRAW_CONTRACT_ADDRESS),
            abi=WithdrawContractABI
        )
        #数据库中存的非校验地址需要转成校验地址
        wallet_address = Web3.to_checksum_address(wallet_address)
        onchain_nonce = contract.functions.nonces(wallet_address).call()


        # 获取并更新数据库记录（已在外部事务中锁定）
        user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
        if not user:
            raise ValueError(f"User {wallet_address} not found")

        # 保证数据库nonce >= 链上nonce
        if user.points_account.withdraw_nonce < onchain_nonce:
            user.points_account.withdraw_nonce = onchain_nonce
            db.session.flush()  # 立即生效但不提交（由外部事务控制）

        current_app.logger.debug(
            f"Nonce synced - Address: {wallet_address}, "
            f"DB: {user.points_account.withdraw_nonce} -> Chain: {onchain_nonce}"
        )

        return onchain_nonce

    except Exception as e:
        current_app.logger.error(
            f"Nonce sync error for {wallet_address}: {str(e)}"
        )
        raise  # 抛出给上层处理

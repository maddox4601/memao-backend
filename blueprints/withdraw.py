import json
from flask import Blueprint, request, jsonify
from models import db, WalletUser, WithdrawalHistory
from datetime import datetime, timezone
from utils.blockchain_batch_transfer import blockchain_batch_transfer

withdraw_bp = Blueprint('withdraw', __name__, url_prefix='/api/withdraw')

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

    if not wallet_address:
        return jsonify({'success': False, 'message': 'Missing wallet address'}), 400

    # 查询用户
    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if not user:
        return jsonify({'success': False, 'message': 'Wallet address not found'}), 404

    # 查询提现记录
    history = WithdrawalHistory.query.filter_by(wallet_user_id=user.id).order_by(WithdrawalHistory.requested_at.desc()).all()
    print(user.id)

    history_data = []
    for record in history:
        history_data.append({
            'id': record.id,
            'amount': str(record.amount),  # 如果是 Decimal 建议转 string，防止前端解析问题
            'requested_at': record.requested_at.strftime('%Y-%m-%d %H:%M:%S'),
            'status': record.status
        })

    return jsonify({'success': True, 'history': history_data})

@withdraw_bp.route('/process', methods=['POST'])
def manual_process_withdrawals():
    try:
        process_withdrawals()
        return jsonify({'success': True, 'message': 'Withdrawals processed successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Processing failed: {str(e)}'}), 500


def process_withdrawals():
    pending_withdrawals = WithdrawalHistory.query.filter_by(status='pending').order_by(WithdrawalHistory.requested_at.asc()).all()

    if not pending_withdrawals:
        print("No pending withdrawals.")
        return

    recipients = []
    amounts_wei = []
    withdrawal_ids = []

    for wd in pending_withdrawals:
        user = WalletUser.query.get(wd.wallet_user_id)
        if user:
            recipients.append(user.wallet_address)
            amounts_wei.append(wd.amount * 10**18)
            withdrawal_ids.append(wd.id)

    print(f"Processing withdrawals on chain: {list(zip(recipients, amounts_wei))}")

    try:
        success = blockchain_batch_transfer(recipients, amounts_wei)

        if success:
            print("Withdrawals processed successfully, updating DB records...")
            WithdrawalHistory.query.filter(WithdrawalHistory.id.in_(withdrawal_ids)).update({'status': 'completed'}, synchronize_session=False)
            db.session.commit()
        else:
            print("Blockchain transfer failed, keeping records pending for next retry.")
            # 失败时保留 pending 状态，下一轮任务会继续处理

    except Exception as e:
        print(f"Blockchain transaction error: {str(e)}")
        # 保持 pending，等待下次重试，不做任何 DB 更新

import json
from flask import Blueprint, request, jsonify
from models import db, WalletUser, WithdrawalHistory
from datetime import datetime, timezone
from decimal import Decimal
from utils.blockchain_batch_transfer import blockchain_batch_withdraw

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
            'requested_at': record.requested_at.astimezone(timezone.utc).isoformat(),
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

from flask import Blueprint, jsonify, request
from datetime import datetime, timedelta, date
from sqlalchemy.exc import SQLAlchemyError
from models import WalletUser, CheckinHistory, UserPointsAccount
from extensions import db  # 你的SQLAlchemy实例

checkin_bp = Blueprint('checkin', __name__, url_prefix='/api/checkin')

def get_milestone_reward(days: int) -> int:
    milestone = (days // 100) * 100
    if milestone >= 100:
        return milestone
    return 0

@checkin_bp.route('/status', methods=['GET'])
def get_checkin_status():
    wallet_address = request.args.get('wallet_address', '').strip()
    if not wallet_address or len(wallet_address) != 42:
        return jsonify({'error': 'Invalid wallet address'}), 400

    today = date.today()

    is_signed_today = CheckinHistory.query.join(WalletUser).filter(
        WalletUser.wallet_address == wallet_address,
        CheckinHistory.checkin_date == today
    ).first() is not None

    points_account = UserPointsAccount.query.join(WalletUser).filter(
        WalletUser.wallet_address == wallet_address
    ).first()

    return jsonify({
        'isSignedToday': is_signed_today,
        'consecutiveDays': points_account.consecutive_days if points_account else 0,
        'points': points_account.total_points if points_account else 0,
        'milestone': points_account.milestone_reached if points_account else 0
    })

@checkin_bp.route('/weekly', methods=['GET'])
def get_weekly_status():
    wallet_address = request.args.get('wallet_address', '').strip()
    if not wallet_address:
        return jsonify({'error': 'Wallet address required'}), 400

    today = date.today()
    start_of_week = today - timedelta(days=today.weekday())

    records = CheckinHistory.query.join(WalletUser).filter(
        WalletUser.wallet_address == wallet_address,
        CheckinHistory.checkin_date >= start_of_week,
        CheckinHistory.checkin_date <= today
    ).all()

    week_status = [0] * 7
    for record in records:
        day_index = (record.checkin_date - start_of_week).days
        if 0 <= day_index < 7:
            week_status[day_index] = 1

    week_dates = [(start_of_week + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]

    return jsonify({'week': week_status, 'dates': week_dates})

@checkin_bp.route('', methods=['POST'])
def checkin():
    data = request.get_json() or {}
    wallet_address = data.get('wallet_address', '').strip()

    if not wallet_address or len(wallet_address) != 42:
        return jsonify({'success': False, 'message': 'Invalid wallet address'}), 400

    today = date.today()

    try:
        with db.session.begin_nested():
            wallet_user = WalletUser.query.filter_by(wallet_address=wallet_address).with_for_update().first()
            if not wallet_user:
                wallet_user = WalletUser(wallet_address=wallet_address)
                db.session.add(wallet_user)
                db.session.flush()

            points_account = UserPointsAccount.query.filter_by(wallet_user_id=wallet_user.id).with_for_update().first()
            if not points_account:
                points_account = UserPointsAccount(
                    wallet_user_id=wallet_user.id,
                    total_points=0,
                    consecutive_days=0,
                    milestone_reached=0
                )
                db.session.add(points_account)
                db.session.flush()

            already_checked_in = CheckinHistory.query.filter_by(
                wallet_user_id=wallet_user.id,
                checkin_date=today
            ).first()

            if already_checked_in:
                return jsonify({'success': False, 'message': 'Already checked in today'}), 400

            points_earned = 1
            reward_type = 'daily'
            milestone_reward = 0

            if points_account.last_checkin_date:
                days_diff = (today - points_account.last_checkin_date).days
                if days_diff == 1:
                    points_account.consecutive_days += 1

                    if points_account.consecutive_days % 7 == 0:
                        points_earned += 5
                        reward_type = 'weekly'

                    new_milestone = get_milestone_reward(points_account.consecutive_days)
                    if new_milestone > points_account.milestone_reached:
                        milestone_reward = new_milestone
                        points_earned += new_milestone
                        reward_type = 'milestone'
                        points_account.milestone_reached = new_milestone
                elif days_diff > 1:
                    points_account.consecutive_days = 1
            else:
                points_account.consecutive_days = 1

            points_account.total_points += points_earned
            points_account.last_checkin_date = today

            db.session.add(CheckinHistory(
                wallet_user_id=wallet_user.id,
                checkin_date=today,
                points_earned=points_earned,
                reward_type=reward_type
            ))
        db.session.commit()

        return jsonify({
            'success': True,
            'points': points_account.total_points,
            'consecutiveDays': points_account.consecutive_days,
            'dailyReward': 1,
            'weeklyReward': 5 if reward_type == 'weekly' else 0,
            'milestoneReward': milestone_reward
        })

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500

@checkin_bp.route('/monthly', methods=['GET'])
def get_monthly_checkin_status():
    wallet_address = request.args.get('wallet_address', '').strip()
    month = request.args.get('month', '').strip()  # 格式 'YYYY-MM'

    if not wallet_address or len(wallet_address) != 42:
        return jsonify({'error': 'Invalid wallet address'}), 400

    if not month:
        return jsonify({'error': 'Month parameter required'}), 400

    try:
        year, mon = map(int, month.split('-'))
        start_date = date(year, mon, 1)
    except Exception:
        return jsonify({'error': 'Invalid month format, expected YYYY-MM'}), 400

    if mon == 12:
        end_date = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(year, mon + 1, 1) - timedelta(days=1)

    records = CheckinHistory.query.join(WalletUser).filter(
        WalletUser.wallet_address == wallet_address,
        CheckinHistory.checkin_date >= start_date,
        CheckinHistory.checkin_date <= end_date
    ).all()

    dates = [r.checkin_date.strftime('%Y-%m-%d') for r in records]

    return jsonify({'dates': dates})

from flask import Blueprint, jsonify, request
from extensions import db
from models import WalletUser, UserPointsAccount, PointsHistory

activity_bp = Blueprint('activity', __name__, url_prefix='/activity')


@activity_bp.route('/total', methods=['GET'])
def get_total_points():
    wallet_address = request.args.get('wallet_address')

    if not wallet_address:
        return jsonify({'error': 'Missing wallet_address'}), 400

    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()

    if not user or not user.points_account:
        return jsonify({'total_points': 0})

    return jsonify({
        'total_points': user.points_account.total_points,
        'consecutive_days': user.points_account.consecutive_days,
        'last_checkin_date': user.points_account.last_checkin_date.isoformat() if user.points_account.last_checkin_date else None
    })


@activity_bp.route('/history', methods=['GET'])
def get_points_history():
    wallet_address = request.args.get('wallet_address')

    if not wallet_address:
        return jsonify({'error': 'Missing wallet_address'}), 400

    user = WalletUser.query.filter_by(wallet_address=wallet_address).first()

    if not user:
        return jsonify({'history': []})

    history = PointsHistory.query.filter_by(wallet_user_id=user.id).order_by(PointsHistory.created_at.desc()).limit(50).all()

    return jsonify([
        {
            'change_type': record.change_type,
            'change_amount': record.change_amount,
            'description': record.description,
            'created_at': record.created_at.isoformat()
        }
        for record in history
    ])

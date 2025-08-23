from flask import Blueprint, request, jsonify, session
from extensions import db
from models import SocialAccount
from utils.twitter_client import twitter_client

socialauth_bp = Blueprint('auth', __name__, url_prefix='/auth')



@socialauth_bp.route('/twitter/login', methods=['GET'])
def twitter_login():
    redirect_url = twitter_client.get_authorize_url()
    return jsonify({"auth_url": redirect_url})


@socialauth_bp.route('/twitter/callback', methods=['GET'])
def twitter_callback():
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    # 从 Twitter 拿到用户信息
    user_info = twitter_client.get_user_info(oauth_token, oauth_verifier)
    twitter_id = user_info["id_str"]
    handle = user_info["screen_name"]

    wallet_user_id = session.get("wallet_user_id")  # 假设前端登录后存的
    if not wallet_user_id:
        return jsonify({"error": "wallet user not found"}), 400

    # 查是否已有绑定
    account = SocialAccount.query.filter_by(
        provider="twitter", social_id=twitter_id
    ).first()

    if account and account.wallet_user_id != wallet_user_id:
        return jsonify({"error": "this twitter account already linked"}), 400

    if not account:
        account = SocialAccount(
            wallet_user_id=wallet_user_id,
            provider="twitter",
            social_id=twitter_id,
            handle=handle,
            verified=True,
        )
        db.session.add(account)
    else:
        account.handle = handle
        account.verified = True

    db.session.commit()

    return jsonify({"message": "twitter linked successfully", "handle": handle})


@socialauth_bp.route('/twitter/status', methods=['GET'])
def twitter_status():
    wallet_user_id = session.get("wallet_user_id")
    if not wallet_user_id:
        return jsonify({"error": "wallet user not found"}), 400

    account = SocialAccount.query.filter_by(
        wallet_user_id=wallet_user_id, provider="twitter"
    ).first()

    if not account or not account.verified:
        return jsonify({"verified": False})

    return jsonify({
        "verified": True,
        "handle": account.handle
    })

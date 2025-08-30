from flask import Blueprint, request, jsonify, session,redirect
from extensions import db
from models import SocialAccount
from utils.twitter_client import twitter_client

from eth_account.messages import encode_defunct
from web3 import Web3

socialauth_bp = Blueprint('socialauth', __name__, url_prefix='/api/socialauth')

# -----------------------------
# Step 1: Twitter 授权
# -----------------------------
@socialauth_bp.route('/twitter/login', methods=['GET'])
def twitter_login():
    """
    返回 Twitter 授权 URL
    """
    # 获取 request token 并保存 secret 到 session
    auth_url, request_token_secret = twitter_client.get_authorize_url_with_secret()
    session['request_token_secret'] = request_token_secret
    return jsonify({"auth_url": auth_url})


# -----------------------------
# Step 2: Twitter 回调
# -----------------------------
@socialauth_bp.route('/twitter/callback', methods=['GET'])
def twitter_callback():
    """
    Twitter 授权回调
    返回 Twitter 用户信息 (twitter_id, handle)
    """
    oauth_token = request.args.get('oauth_token')
    oauth_verifier = request.args.get('oauth_verifier')

    if not oauth_token or not oauth_verifier:
        return jsonify({"error": "Missing oauth parameters"}), 400

    # 从 session 获取 request token secret
    request_token_secret = session.get('request_token_secret')
    if not request_token_secret:
        return jsonify({"error": "Missing request token secret"}), 400

    # 从 Twitter 拿到用户信息
    user_info = twitter_client.get_user_info(oauth_token, oauth_verifier, request_token_secret)
    twitter_id = user_info["id_str"]
    handle = user_info["screen_name"]

    # 返回给前端，用于生成钱包签名
    return jsonify({
        "status": "ok",
        "twitter_id": twitter_id,
        "handle": handle
    })

    #中间页模式
    # frontend_url = f"https://www.memao.org/twittercallbackpage?handle={handle}&twitter_id={twitter_id}"
    # return redirect(frontend_url)


# -----------------------------
# Step 3: 钱包签名绑定
# -----------------------------
def verify_signature(wallet_address, twitter_id, signature):
    """
    验证用户钱包签名
    """
    message = f"Bind wallet {wallet_address} to twitter {twitter_id}"
    msg = encode_defunct(text=message)
    recovered_address = Web3().eth.account.recover_message(msg, signature=signature)
    return recovered_address.lower() == wallet_address.lower()


@socialauth_bp.route('/twitter/bind_wallet', methods=['POST'])
def bind_wallet():
    """
    前端发送 wallet_address + twitter_id + signature
    后端验证签名并存储绑定关系
    """
    try:
        data = request.json
        wallet_address = data.get("wallet_address")
        twitter_id = data.get("twitter_id")
        signature = data.get("signature")
        handle = data.get("handle", "")  # 可选，前端可以传 handle

        # 验证必需参数
        if not wallet_address or not twitter_id or not signature:
            return jsonify({
                "status": "error",
                "data": None,
                "message": "Missing required parameters: wallet_address, twitter_id, and signature are required"
            }), 400

        # 验证签名
        if not verify_signature(wallet_address, twitter_id, signature):
            return jsonify({
                "status": "error",
                "data": None,
                "message": "Signature verification failed"
            }), 401

        # 查是否已有绑定
        account = SocialAccount.query.filter_by(provider="twitter", social_id=twitter_id).first()

        # 检查是否已绑定到其他钱包
        if account and account.wallet_address.lower() != wallet_address.lower():
            return jsonify({
                "status": "error",
                "data": {
                    "existing_wallet": account.wallet_address,
                    "twitter_id": twitter_id
                },
                "message": "This Twitter account is already linked to another wallet"
            }), 409  # 409 Conflict

        # 处理绑定逻辑
        if not account:
            # 新建绑定
            account = SocialAccount(
                wallet_address=wallet_address,
                provider="twitter",
                social_id=twitter_id,
                handle=handle,
                verified=True
            )
            db.session.add(account)
            action = "created"
        else:
            # 更新绑定信息
            account.wallet_address = wallet_address
            account.handle = handle or account.handle
            account.verified = True
            action = "updated"

        db.session.commit()

        # 成功响应
        return jsonify({
            "status": "success",
            "data": {
                "handle": account.handle,
                "twitter_id": account.social_id,
                "wallet_address": account.wallet_address,
                "provider": account.provider,
                "verified": account.verified,
                "action": action
            },
            "message": "Wallet successfully linked to Twitter"
        })

    except Exception as e:
        # 数据库操作异常回滚
        db.session.rollback()

        # 记录错误日志
        print(f"Error in bind_wallet: {str(e)}")

        return jsonify({
            "status": "error",
            "data": None,
            "message": "Internal server error occurred while processing your request"
        }), 500


# -----------------------------
# Step 4: 查询绑定状态
# -----------------------------
@socialauth_bp.route('/twitter/status', methods=['GET'])
def twitter_status():
    """
    前端传 wallet_address 查询绑定状态
    """
    wallet_address = request.args.get("wallet_address")
    if not wallet_address:
        return jsonify({"error": "wallet address not provided"}), 400

    account = SocialAccount.query.filter_by(wallet_address=wallet_address, provider="twitter").first()

    if not account or not account.verified:
        return jsonify({"verified": False})

    return jsonify({
        "verified": True,
        "handle": account.handle
    })

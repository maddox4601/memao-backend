# app/auth/routes.py
from flask import Blueprint, request, jsonify
from models import User, UserAccount, WalletUser
from extensions import db
from datetime import datetime, timezone

login_bp = Blueprint("login", __name__, url_prefix="/api/login")


# app/auth/routes.py
def serialize_user(user):
    """序列化用户数据，基于实际模型字段"""
    return {
        "user_id": user.id,  # 现在返回的是 UUID 字符串
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "oauth_accounts": [
            {
                "provider": acc.provider,
                "provider_uid": acc.provider_uid
            }
            for acc in user.oauth_accounts
        ],
        "wallets": [
            {
                "address": wallet.wallet_address,
                "nickname": wallet.nickname,
                "registered_at": wallet.registered_at.isoformat() if wallet.registered_at else None,
                "daily_weight": wallet.daily_weight
            }
            for wallet in user.wallets
        ]
    }


# --------- 获取用户信息 ----------
@login_bp.route("/user/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """根据用户ID获取完整的用户信息"""
    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "user not found"}), 404

    return jsonify({"user": serialize_user(user)})


# --------- OAuth 登录 ----------
@login_bp.route("/oauth-login", methods=["POST"])
def oauth_login():
    data = request.json
    provider = data.get("provider")
    provider_uid = data.get("provider_uid")

    if not provider or not provider_uid:
        return jsonify({"msg": "invalid parameters"}), 400

    # 查询已有账户
    account = UserAccount.query.filter_by(provider=provider, provider_uid=provider_uid).first()
    if account:
        user = account.user
        return jsonify({
            "msg": "login success",
            "user": serialize_user(user)
        })
    else:
        # 新建用户和账号 - 使用模型的默认值
        user = User()  # created_at 有默认值，不需要手动设置
        db.session.add(user)
        db.session.flush()

        new_account = UserAccount(
            user_id=user.id,
            provider=provider,
            provider_uid=provider_uid
            # UserAccount 没有 created_at 字段
        )
        db.session.add(new_account)
        db.session.commit()

        return jsonify({
            "msg": "new user created",
            "user": serialize_user(user)
        })


# --------- Wallet 登录 / 绑定 ----------
@login_bp.route("/wallet-login", methods=["POST"])
def wallet_login():
    data = request.json
    wallet_address = data.get("wallet_address")
    user_id = data.get("user_id")  # 可选，表示当前登录用户要绑定 Wallet

    if not wallet_address:
        return jsonify({"msg": "wallet_address required"}), 400

    wallet_user = WalletUser.query.filter_by(wallet_address=wallet_address).first()

    # Wallet 已存在
    if wallet_user:
        # 已绑定 user_id
        if wallet_user.user_id:
            # 如果传入 user_id 且不同，提示冲突
            if user_id and wallet_user.user_id != user_id:
                return jsonify({
                    "msg": "wallet bound to another user",
                    "wallet_user_id": wallet_user.id,
                    "bound_user_id": wallet_user.user_id
                }), 409

            user = User.query.get(wallet_user.user_id)
            return jsonify({
                "msg": "login success",
                "user": serialize_user(user)
            })
        else:
            # Wallet 未绑定，绑定到当前 user_id 或新建用户
            if user_id:
                wallet_user.user_id = user_id
                user = User.query.get(user_id)
            else:
                user = User()  # 使用默认值
                db.session.add(user)
                db.session.flush()
                wallet_user.user_id = user.id

            db.session.commit()
            return jsonify({
                "msg": "wallet bound",
                "user": serialize_user(user)
            })

    # Wallet 不存在
    else:
        if user_id:
            user = User.query.get(user_id)
            wallet_user = WalletUser(
                wallet_address=wallet_address,
                user_id=user_id
                # registered_at 有默认值
            )
        else:
            user = User()  # 使用默认值
            db.session.add(user)
            db.session.flush()
            wallet_user = WalletUser(
                wallet_address=wallet_address,
                user_id=user.id
                # registered_at 有默认值
            )

        db.session.add(wallet_user)
        db.session.commit()
        return jsonify({
            "msg": "wallet created and bound",
            "user": serialize_user(user)
        })


# --------- 查询 Wallet 冲突 ----------
@login_bp.route("/wallet-conflict/<wallet_address>", methods=["GET"])
def wallet_conflict(wallet_address):
    wallet_user = WalletUser.query.filter_by(wallet_address=wallet_address).first()
    if wallet_user and wallet_user.user_id:
        return jsonify({
            "wallet_user_id": wallet_user.id,
            "bound_user_id": wallet_user.user_id,
            "conflict": True
        })
    return jsonify({"conflict": False})


# --------- 绑定 OAuth 到现有用户 ----------
@login_bp.route("/bind-oauth", methods=["POST"])
def bind_oauth():
    """将 OAuth 账号绑定到现有用户"""
    data = request.json
    user_id = data.get("user_id")
    provider = data.get("provider")
    provider_uid = data.get("provider_uid")

    if not all([user_id, provider, provider_uid]):
        return jsonify({"msg": "missing parameters"}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"msg": "user not found"}), 404

    # 检查是否已绑定
    existing_account = UserAccount.query.filter_by(
        provider=provider,
        provider_uid=provider_uid
    ).first()

    if existing_account:
        return jsonify({"msg": "oauth account already bound to another user"}), 409

    # 创建新的 OAuth 绑定
    new_account = UserAccount(
        user_id=user_id,
        provider=provider,
        provider_uid=provider_uid
    )
    db.session.add(new_account)
    db.session.commit()

    # 返回更新后的用户信息
    updated_user = User.query.get(user_id)
    return jsonify({
        "msg": "oauth account bound successfully",
        "user": serialize_user(updated_user)
    })
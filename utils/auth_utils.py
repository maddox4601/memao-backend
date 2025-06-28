# auth_utils.py
import jwt
from flask import request, jsonify, current_app
from functools import wraps

def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None

        # 从请求头获取 Authorization: Bearer <token>
        auth_header = request.headers.get('Authorization', None)
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        else:
            return jsonify({'success': False, 'message': '缺少授权令牌'}), 401

        try:
            payload = jwt.decode(token, current_app.config['JWT_SECRET'], algorithms=['HS256'])
            # 如果需要可以把用户信息放入上下文
            # from flask import g
            # g.current_user_id = payload.get('user_id')
        except jwt.ExpiredSignatureError:
            return jsonify({'success': False, 'message': '授权令牌已过期'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'success': False, 'message': '无效的授权令牌'}), 401

        return f(*args, **kwargs)
    return decorated_function

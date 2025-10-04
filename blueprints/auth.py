from flask import Blueprint, request, jsonify, session, send_file,current_app
from models import AdminUser
from extensions import db
import jwt
import datetime
from captcha.image import ImageCaptcha

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

# JWT 密钥（实际项目中请用更安全的方式保管）
JWT_EXP_DELTA_SECONDS = 3600  # token 有效时间，单位：秒

# 注册
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

    if AdminUser.query.filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400

    try:
        user = AdminUser(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return jsonify({'success': True, 'message': '注册成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'注册失败: {str(e)}'}), 500

# 获取图形验证码
@auth_bp.route('/captcha', methods=['GET'])
def get_captcha():
    image = ImageCaptcha()
    captcha_text = ''.join([chr(i) for i in range(65, 91)])[:4]  # 简单字符
    import random
    captcha_code = ''.join(random.choices(captcha_text, k=4))
    session['captcha_code'] = captcha_code.lower()

    data = image.generate(captcha_code)
    return send_file(data, mimetype='image/png')

# 登录
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    username = data.get('username')
    password = data.get('password')
    captcha = data.get('captcha', '').lower()
    session_captcha = session.get('captcha_code', '').lower()

    if captcha != session_captcha:
        return jsonify({'success': False, 'message': '验证码错误'}), 400

    user = AdminUser.query.filter_by(username=username).first()
    if user and user.check_password(password):
        payload = {
            'user_id': user.id,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        token = jwt.encode(payload, current_app.config['JWT_SECRET'], algorithm='HS256')
        return jsonify({'success': True, 'token': token})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

from flask import Blueprint, request, jsonify
from models import Message
from datetime import datetime, timezone
from utils.email import send_reply_email
import re
from extensions import db  # 你的 SQLAlchemy 实例

contact_bp = Blueprint('contact', __name__, url_prefix='/api/contact')

email_pattern = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')

@contact_bp.route('', methods=['POST'])
def submit_contact():
    data = request.get_json() or {}

    name = data.get('name', '').strip()
    email = data.get('email', '').strip()
    message_text = data.get('message', '').strip()

    if not all([name, email, message_text]):
        return jsonify({'success': False, 'message': '所有字段均为必填'}), 400

    if not email_pattern.match(email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400

    try:
        new_msg = Message(username=name, email=email, message=message_text)
        db.session.add(new_msg)
        db.session.commit()
        return jsonify({'success': True, 'message': '留言提交成功,我们会尽快联系您！'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'数据库错误: {str(e)}'}), 500

@contact_bp.route('/contacts_list', methods=['GET'])
def get_contact_messages():
    try:
        messages = Message.query.order_by(Message.created_at.desc()).all()
        data = [{
            'id': msg.id,
            'username': msg.username,
            'email': msg.email,
            'message': msg.message,
            'replied': msg.replied,
            'replay_content': msg.replay_content,  # 你这里字段叫 replay_content，建议数据库字段改成 reply_content
            'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else None,
            'replied_at': msg.replied_at.strftime('%Y-%m-%d %H:%M:%S') if msg.replied_at else None
        } for msg in messages]
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取留言列表失败: {str(e)}'}), 500

@contact_bp.route('/<int:contact_id>/reply', methods=['POST'])
def reply_contact(contact_id):
    data = request.get_json() or {}
    reply_content = data.get('reply', '').strip()

    if not reply_content:
        return jsonify({'success': False, 'message': '回复内容不能为空'}), 400

    try:
        message = Message.query.get(contact_id)
        if not message:
            return jsonify({'success': False, 'message': '留言不存在'}), 404

        subject = '关于您留言的回复'
        email_sent = send_reply_email(message.email, subject, reply_content)

        if email_sent:
            message.replied = True
            message.replay_content = reply_content
            message.replied_at = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({'success': True, 'message': '回复成功，邮件已发送'})
        else:
            # 邮件发送失败，数据库不更新
            return jsonify({'success': True, 'message': '回复成功，但邮件发送失败'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500

from flask import Flask,request,jsonify
from flask_cors import CORS
from models import Message,session,AirdropAddress,User
from datetime import datetime,timedelta,timezone
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.utils import formataddr
import smtplib
import re


app = Flask(__name__)
CORS(app)


@app.route('/api/contact',methods=['POST'])
def contact():
    data=request.get_json()

    name=data.get('name','').strip()
    email = data.get('email', '').strip()
    message = data.get('message', '').strip()

    #简单校验
    if not name or not email or not message:
        return jsonify({'success':False,'message':'所有字段均为必填'}),400

    # 邮箱格式校验
    email_pattern = r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    if not re.match(email_pattern, email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400

    try:
        new_msg = Message(username=name, email=email, message=message)
        session.add(new_msg)
        session.commit()
        return jsonify({'success': True, 'message': '留言提交成功,我们会尽快联系您！'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': f'数据库错误: {str(e)}'}), 500
    finally:
        session.close()



@app.route('/api/contacts', methods=['GET'])
def get_messages():
    try:
        messages = session.query(Message).order_by(Message.created_at.desc()).all()
        data = []
        for msg in messages:
            data.append({
                'id': msg.id,
                'username': msg.username,
                'email': msg.email,
                'message': msg.message,
                'replied': msg.replied,
                'replay_content': msg.replay_content,
                'created_at': msg.created_at.strftime('%Y-%m-%d %H:%M:%S') if msg.created_at else None,
                'replied_at': msg.replied_at.strftime('%Y-%m-%d %H:%M:%S') if msg.replied_at else None
            })
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取留言列表失败: {str(e)}'}), 500



# Gmail SMTP 配置
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
GMAIL_USERNAME = 'memaoteam@gmail.com'
GMAIL_PASSWORD = 'nfdh fytg wmkc esbn'  # 注意使用"应用专用密码"，不是 Gmail 登录密码


def send_reply_email(to_email, subject, content):
    try:
        msg = MIMEText(content, 'plain', 'utf-8')
        msg['From'] = formataddr(("MEMAO官方客服", GMAIL_USERNAME))
        msg['To'] = to_email
        msg['Subject'] = subject

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(GMAIL_USERNAME, GMAIL_PASSWORD)
        server.sendmail(GMAIL_USERNAME, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

@app.route('/api/contacts/<int:contact_id>/reply', methods=['POST'])
def reply_message(contact_id):
    data = request.get_json()
    reply_content = data.get('reply', '').strip()

    if not reply_content:
        return jsonify({'success': False, 'message': '回复内容不能为空'}), 400

    try:
        message = session.query(Message).filter_by(id=contact_id).first()
        if not message:
            return jsonify({'success': False, 'message': '留言不存在'}), 404

        # 发送邮件通知（先发送邮件）
        subject = '关于您留言的回复'
        email_sent = send_reply_email(message.email, subject, reply_content)

        if email_sent:
            # 邮件发送成功再更新数据库
            message.replied = True
            message.replay_content = reply_content
            message.replied_at = datetime.now(timezone.utc)
            session.commit()
            return jsonify({'success': True, 'message': '回复成功，邮件已发送'})
        else:
            # 邮件失败，不保存数据库
            session.rollback()
            return jsonify({'success': True, 'message': '回复成功，但邮件发送失败'}), 200

    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': f'操作失败: {str(e)}'}), 500



@app.route('/api/collect_address', methods=['POST'])
def collect_address():
    data = request.get_json()
    address = data.get('address', '').strip()
    comment = data.get('comment', '').strip()

    # 简单地址格式校验（可根据实际项目调整）
    if not address or not re.match(r'^0x[a-fA-F0-9]{40}$', address):
        return jsonify({'success': False, 'message': '钱包地址无效'}), 400

    # 检查是否重复提交
    existing = session.query(AirdropAddress).filter_by(address=address).first()
    if existing:
        return jsonify({'success': False, 'message': '该地址已参加过空投活动'}), 200

    try:
        new_entry = AirdropAddress(
            address=address,
            comment=comment,
            submitted_at=datetime.now(timezone.utc)
        )
        session.add(new_entry)
        session.commit()
        return jsonify({'success': True, 'message': '地址提交成功'}), 200
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'message': f'提交失败: {str(e)}'}), 500


@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if not username or not password:
        return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400

    # 用 session.query 代替 User.query
    if session.query(User).filter_by(username=username).first():
        return jsonify({'success': False, 'message': '用户名已存在'}), 400

    user = User(username=username)
    user.set_password(password)
    session.add(user)
    session.commit()
    return jsonify({'success': True, 'message': '注册成功'})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # 用 session.query 代替 User.query
    user = session.query(User).filter_by(username=username).first()
    if user and user.check_password(password):
        token = 'fake-jwt-token-for-demo'  # 你后续可以替换成真正的 JWT
        return jsonify({'success': True, 'token': token})
    else:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

if __name__=='__main__':
    app.run(debug=True)
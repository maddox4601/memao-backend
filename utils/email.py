import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

# Gmail SMTP 配置
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
GMAIL_USERNAME = 'memaoteam@gmail.com'
GMAIL_PASSWORD = 'nfdh fytg wmkc esbn'

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
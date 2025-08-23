from datetime import datetime, timezone
from extensions import db

class Message(db.Model):
    __tablename__ = 'messages'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100))
    message = db.Column(db.String(1000))
    replied = db.Column(db.Boolean, default=False)
    replay_content = db.Column(db.String(1000))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    replied_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='normal')
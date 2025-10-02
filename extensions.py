# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import os
from redis import Redis
from rq import Queue
from dotenv import load_dotenv

db = SQLAlchemy()

load_dotenv()

# REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
print(f"REDIS_URL: {os.getenv('REDIS_URL')}")
REDIS_URL = os.getenv("REDIS_URL")
redis_conn = Redis.from_url(REDIS_URL)
tx_queue = Queue("tx_jobs", connection=redis_conn)

socketio = SocketIO()  # 不传 app
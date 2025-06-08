import pymysql
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from urllib.parse import quote_plus
from werkzeug.security import generate_password_hash, check_password_hash

# MySQL 配置项
DB_NAME = 'memao_portal'
DB_USER = 'root'
DB_PASSWORD = 'Maddox1988@'
DB_HOST = 'localhost'
DB_PORT = 3306
CHARSET = 'utf8mb4'

# 对密码进行 URL 编码，避免特殊字符导致连接错误
DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD)

def ensure_database_exists():
    print("开始检查数据库是否存在...")
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database='mysql',  # 连接到系统数据库
        charset=CHARSET
    )
    cursor = conn.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME} CHARACTER SET {CHARSET} COLLATE {CHARSET}_unicode_ci;")
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ 数据库 {DB_NAME} 已确认存在或创建成功")

# 先执行数据库检查和创建
ensure_database_exists()

# 创建 SQLAlchemy 引擎，连接到目标数据库
DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD_ENCODED}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={CHARSET}'
engine = create_engine(DATABASE_URI, echo=True)  # echo=True 会输出 SQL 方便调试

Base = declarative_base()

# 定义数据表模型

class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    username = Column(String(100))
    email = Column(String(100))
    message = Column(String(1000))
    replied = Column(Boolean, default=False)
    replay_content = Column(String(1000))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    replied_at = Column(DateTime)

class AirdropAddress(Base):
    __tablename__ = 'airdrop_addresses'
    id = Column(Integer, primary_key=True)
    address = Column(String(255), nullable=False, unique=True)
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    comment = Column(String(100))

class TokenTransfer(Base):
    __tablename__ = 'token_transfers'
    id = Column(Integer, primary_key=True)
    from_address = Column(String(255), nullable=False)
    to_address = Column(String(255), nullable=False)
    token_symbol = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    tx_hash = Column(String(255), nullable=False, unique=True)
    transferred_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String(20), default='pending')


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# 创建所有表结构
Base.metadata.create_all(engine)
print("✅ 所有数据表已创建或确认存在")

# 创建会话工厂和会话实例
Session = sessionmaker(bind=engine)
session = Session()

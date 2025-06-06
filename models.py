import pymysql
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime,Float
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from urllib.parse import quote_plus

# MySql配置项

DB_NAME = 'memao_portal'
DB_USER = 'root'
DB_PASSWORD = 'Maddox1988@'
DB_HOST = 'localhost'
DB_PORT = 3306
CHARSET = 'utf8mb4'
DB_PASSWORD_ENCODED = quote_plus(DB_PASSWORD)


# 检查并创建数据库
def ensure_database_exists():
    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database='mysql',
        charset=CHARSET
    )
    cursor = conn.cursor()
    cursor.execute("CREATE DATABASE IF NOT EXISTS your_database_name CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ 数据库检查完成")

#执行数据库检查
ensure_database_exists()

#创建SQLAlchemy引擎并链接到目标数据库
DATABASE_URI = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset={CHARSET}'
engine=create_engine(DATABASE_URI)

Base= declarative_base()


#用户留言表
class Message(Base):
    __tablename__ = 'messages'
    id = Column(Integer, primary_key=True)
    username = Column(String(100),)
    email = Column(String(100))
    message = Column(String(1000))
    replied=Column(Boolean,default=False)
    replay_content = Column(String(1000))
    created_at = Column(DateTime, default=lambda:datetime.now(timezone.utc))
    replied_at=Column(DateTime)


#空投地址收集表
class AirdropAddress(Base):
    __tablename__ = 'airdrop_addresses'
    id = Column(Integer, primary_key=True)
    address =Column(String(255), nullable=False, unique=True)
    submitted_at = Column(DateTime, default=lambda:datetime.now(timezone.utc))
    comment = Column(String(100))


#Token转账记录表
class TokenTransfer(Base):
    __tablename__ = 'token_transfers'

    id = Column(Integer, primary_key=True)
    from_address = Column(String(255), nullable=False)
    to_address = Column(String(255), nullable=False)
    token_symbol = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    tx_hash = Column(String(255), nullable=False, unique=True)
    transferred_at = Column(DateTime, default=lambda:datetime.now(timezone.utc))
    status = Column(String(20), default='pending')

#创建所有表结构
Base.metadata.crete_all(engine)

#会话工厂
Session=sessionmaker(bind=engine)
session=Session()

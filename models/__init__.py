# 1. 显式导入所有模型类（供__all__和直接引用使用）
from extensions import db

from .adminuser_models import AdminUser
from .user_models import User,UserAccount
from .wallet_models import WalletUser, CheckinHistory, UserPointsAccount, WithdrawalHistory, PointsHistory
from .airdrop_models import AirdropAddress, AirdropConfig, TokenTransfer
from .mining_models import MiningHistory
from .message_models import Message
from .vip_subscriptions import VIPSubscription
from .invite_models import InviteRecord
from .socialaccount_models import SocialAccount
from .paypal import PayPalOrder,PaymentStatusEnum,DeployStatusEnum
from .transaction_jobs import TransactionJob,JobStatusEnum
from .eth import EthOrder

# 2. 定义__all__（控制from models import *的行为）
__all__ = [
    'AdminUser',
    'User',
    'UserAccount',
    'WalletUser',
    'CheckinHistory',
    'UserPointsAccount',
    'WithdrawalHistory',
    'PointsHistory',
    'AirdropAddress',
    'AirdropConfig',
    'TokenTransfer',
    'MiningHistory',
    'Message',
    'VIPSubscription',
    'InviteRecord',
    'SocialAccount',
    'PayPalOrder',
    'PaymentStatusEnum',
    'DeployStatusEnum',
    'TransactionJob',
    'JobStatusEnum',
    'EthOrder'
]

# 3. 显式注册函数（确保Flask-Migrate能发现模型）
def register_models():
    """强制导入所有模型模块（触发SQLAlchemy注册）"""
    from . import adminuser_models
    from . import user_models
    from . import user_models
    from . import wallet_models
    from . import airdrop_models
    from . import mining_models
    from . import message_models
    from . import vip_subscriptions
    from . import invite_models
    from . import socialaccount_models
    from . import paypal
    from . import transaction_jobs
    from . import eth
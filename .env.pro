# ======================
# 数据库配置
# ======================
DB_HOST=mysql
DB_PORT=3306
DB_USER=memao_prod_user
DB_PASSWORD=Maddox1988@
DB_ROOT_PASSWORD=Maddox1988@
DB_NAME=memao_portal
DB_URI=mysql+pymysql://${DB_USER}:Maddox1988%40@${DB_HOST}:${DB_PORT}/${DB_NAME}


# ======================
# Flask 安全配置
# ======================
SECRET_KEY=prod_flask_secret_7f3c91d69c46b5b6b7e1e2ef23e9db59b7344eede9ed83e40f65b0fbc4e2b1b2
JWT_SECRET=prod_jwt_secret_92b1c1a74a6c9eec0c8a86f73227b7a5a34e7fddbf3d2a0c47e9a9b829fbd9e1
SESSION_TYPE=filesystem
SESSION_PERMANENT=False

# ======================
# 区块链配置
# ======================
WEB3_PROVIDER=https://mainnet.infura.io/v3/4a1828c6924c46ea86d80ca94c77c9de
COMMUNITY_PRIVATE_KEY=0x83fb9d9f89b89976653eaa1d07ea89df7fe08a29d185edbdd8042c6a1c1e1180
DEV_PRIVATE_KEY=0x1f8a627841544f8e55cf16e51c955777d6fade3c833fa442998b5cddb7628d0d
AIRDROP_CONTRACT_ADDRESS=0x64C2eAdA53c436f13cB1FcDEE48CA07b10Cbd38f
MEMAO_TOKEN_ADDRESS=0x9f50182B2735DB017F00c9898d1127A1D97b7cCE
BATCH_WITHDRAW_CONTRACT_ADDRESS=0x92949217C893eeC9143e4536e30508572bBb22AB
WITHDRAW_CONTRACT_ADDRESS=0x693e17Ca40E2F36ACBbA40064daeB0b7494B494c

# ======================
# Redis 缓存
# ======================
REDIS_URL=redis://:maddox1988@redis:6379/0

# ======================
# Twitter 认证
# ======================
TWITTER_CONSUMER_KEY=lHRa4wc8cRNj37rnMiGF5Lgq3
TWITTER_CONSUMER_SECRET=jEI2zIVWJlszFHkWyJYKGD4jx92t5kBCI1XJioiLbjNWgsRxXb
TWITTER_CALLBACK_URL=https://www.memao.org/api/socialauth/twitter/callback

# ======================
# PayPal
# ======================
PAYPAL_API=https://api-m.sandbox.paypal.com
PAYPAL_CLIENT_ID=AaE9wijDuyTmhVdwFnQQ830HUAMDfcyxqPZXsQezNW-lafAPo6C916Ue9lm_IjjV8b8AeKhV6_JrhsYp
PAYPAL_SECRET=EEPeuden31mF_yjVus8HU679D1z0raHf78cP2MpNogtJWtxQUvOzbbj9I84ckXWrdcI5nYfOFU-I3vQV

TOKEN_PRICE=1
TOKEN_CURRENCY=USD

FACTORY_ADDRESS=0xc66a513963381ea918251E15Fa78E2aD9eB30321
DEV_WALLET_ADDRESS=0xbDe89394393C7427e4840F468AeB3162282b86f4

MAIN_SERVER_URL=https://www.memao.org

# ======================
# Google OAuth
# ======================
GOOGLE_REDIRECT_URI=https://www.memao.org/api/socialauth/google/callback
GOOGLE_AUTH_URL=https://accounts.google.com/o/oauth2/v2/auth
GOOGLE_TOKEN_URL=https://oauth2.googleapis.com/token
GOOGLE_USERINFO_URL=https://www.googleapis.com/oauth2/v3/userinfo

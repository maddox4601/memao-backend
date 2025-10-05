# utils/google_client.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

# 从环境变量读取 Google API 配置
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# 从环境变量读取 OAuth2 端点
GOOGLE_AUTH_URL = os.getenv("GOOGLE_AUTH_URL")
GOOGLE_TOKEN_URL = os.getenv("GOOGLE_TOKEN_URL")
GOOGLE_USERINFO_URL = os.getenv("GOOGLE_USERINFO_URL")


class GoogleOAuthClient:
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorize_url(self):
        """
        获取 Google 授权 URL
        """
        scope = "openid email profile"
        auth_url = (
            f"{GOOGLE_AUTH_URL}"
            f"?client_id={self.client_id}"
            f"&redirect_uri={self.redirect_uri}"
            f"&response_type=code"
            f"&scope={scope}"
            f"&access_type=offline"
            f"&prompt=select_account"
        )
        return auth_url

    def exchange_code_for_token(self, code):
        """
        用授权码换取 access_token
        """
        token_data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        response = requests.post(GOOGLE_TOKEN_URL, data=token_data)
        response.raise_for_status()
        return response.json()

    def get_user_info(self, access_token):
        """
        用 access_token 获取 Google 用户信息
        """
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
        response.raise_for_status()
        return response.json()


# 全局客户端实例
google_client = GoogleOAuthClient(
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI
)
# utils/twitter_client.py
import os
from requests_oauthlib import OAuth1Session
from dotenv import load_dotenv

# 读取 .env
load_dotenv()

# 从环境变量读取 Twitter API 配置
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_CALLBACK_URL = os.getenv("TWITTER_CALLBACK_URL")  # e.g. "https://yourdomain.com/auth/twitter/callback"

# Twitter OAuth1.0a endpoints
REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
AUTHORIZATION_URL = "https://api.twitter.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
USER_INFO_URL = "https://api.twitter.com/1.1/account/verify_credentials.json"


class TwitterOAuthClient:
    def __init__(self, consumer_key, consumer_secret, callback_url):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_url = callback_url

    def get_authorize_url_with_secret(self):
        """
        获取 Twitter 授权 URL，同时返回 request_token_secret
        """
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            callback_uri=self.callback_url
        )
        fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)
        resource_owner_key = fetch_response.get("oauth_token")
        resource_owner_secret = fetch_response.get("oauth_token_secret")
        auth_url = f"{AUTHORIZATION_URL}?oauth_token={resource_owner_key}"
        return auth_url, resource_owner_secret

    def get_user_info(self, oauth_token, oauth_verifier, oauth_token_secret):
        """
        回调时获取 Twitter 用户信息
        需要 request_token_secret
        """
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=oauth_token,
            resource_owner_secret=oauth_token_secret,
            verifier=oauth_verifier
        )

        # 拉取 access token
        oauth_tokens = oauth.fetch_access_token(ACCESS_TOKEN_URL)

        access_token = oauth_tokens["oauth_token"]
        access_token_secret = oauth_tokens["oauth_token_secret"]

        # 用 access_token 拉取用户信息
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        response = oauth.get(USER_INFO_URL, params={"skip_status": True})
        response.raise_for_status()
        user_info = response.json()
        return {
            "id_str": user_info["id_str"],
            "screen_name": user_info["screen_name"]
        }


# 全局客户端实例
twitter_client = TwitterOAuthClient(
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    TWITTER_CALLBACK_URL
)

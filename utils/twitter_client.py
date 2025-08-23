import os
import requests
from requests_oauthlib import OAuth1Session

# 你需要在 Twitter Developer Portal 创建 App，拿到下面这些配置
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_CALLBACK_URL = os.getenv("TWITTER_CALLBACK_URL")  # e.g. "https://yourdomain.com/auth/twitter/callback"

# Twitter OAuth1.0a 相关 endpoint
REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
AUTHORIZATION_URL = "https://api.twitter.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://api.twitter.com/oauth/access_token"
USER_INFO_URL = "https://api.twitter.com/1.1/account/verify_credentials.json"


class TwitterOAuthClient:
    def __init__(self, consumer_key, consumer_secret, callback_url):
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.callback_url = callback_url

    def get_authorize_url(self):
        """获取 Twitter 授权跳转链接"""
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            callback_uri=self.callback_url,
        )
        fetch_response = oauth.fetch_request_token(REQUEST_TOKEN_URL)

        resource_owner_key = fetch_response.get("oauth_token")
        # resource_owner_secret = fetch_response.get("oauth_token_secret")  # 一般存 session 备用

        return f"{AUTHORIZATION_URL}?oauth_token={resource_owner_key}"

    def get_user_info(self, oauth_token, oauth_verifier):
        """通过 callback 拿到用户 access_token 和 profile"""
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
        )

        oauth_tokens = oauth.fetch_access_token(
            ACCESS_TOKEN_URL,
            verifier=oauth_verifier,
        )

        access_token = oauth_tokens["oauth_token"]
        access_token_secret = oauth_tokens["oauth_token_secret"]

        # 再用 access_token 拉用户信息
        oauth = OAuth1Session(
            self.consumer_key,
            client_secret=self.consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )

        response = oauth.get(USER_INFO_URL, params={"skip_status": True})
        response.raise_for_status()
        return response.json()


# 初始化一个全局客户端
twitter_client = TwitterOAuthClient(
    TWITTER_CONSUMER_KEY,
    TWITTER_CONSUMER_SECRET,
    TWITTER_CALLBACK_URL,
)

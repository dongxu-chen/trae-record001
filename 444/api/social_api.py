import os
from typing import List, Optional, Dict
from datetime import datetime

try:
    import tweepy
    HAS_TWEEP = True
except ImportError:
    HAS_TWEEP = False

from utils.helpers import to_utc_datetime, format_utc_iso


class SocialMediaAPI:
    def __init__(
        self,
        platform: str = "twitter",
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        access_token: Optional[str] = None,
        access_token_secret: Optional[str] = None,
        bearer_token: Optional[str] = None,
    ):
        self.platform = platform
        self.api_key = api_key or os.getenv("TWITTER_API_KEY", "")
        self.api_secret = api_secret or os.getenv("TWITTER_API_SECRET", "")
        self.access_token = access_token or os.getenv("TWITTER_ACCESS_TOKEN", "")
        self.access_token_secret = access_token_secret or os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "")
        self.bearer_token = bearer_token or os.getenv("TWITTER_BEARER_TOKEN", "")
        self._client = None
        self._api = None

    def authenticate(self) -> bool:
        if not HAS_TWEEP:
            return False

        try:
            if self.bearer_token:
                self._client = tweepy.Client(bearer_token=self.bearer_token)
                self._client.get_user(username="twitter")
                return True

            if self.api_key and self.api_secret:
                auth = tweepy.OAuth1UserHandler(
                    self.api_key,
                    self.api_secret,
                    self.access_token,
                    self.access_token_secret,
                )
                self._api = tweepy.API(auth, wait_on_rate_limit=True)
                self._api.verify_credentials()
                return True
        except Exception:
            pass
        return False

    def get_user_info(self, username: str) -> Optional[dict]:
        if self._client:
            try:
                user = self._client.get_user(username=username, user_fields=[
                    "created_at", "public_metrics", "verified", "profile_image_url",
                    "description", "protected",
                ])
                if user.data:
                    return self._twitter_user_to_dict(user.data)
            except Exception:
                pass

        if self._api:
            try:
                user = self._api.get_user(screen_name=username)
                return self._twitter_user_to_dict_legacy(user)
            except Exception:
                pass

        return None

    def get_followers(self, username: str, max_count: int = 100) -> List[dict]:
        if self._client:
            try:
                user_resp = self._client.get_user(username=username)
                if not user_resp.data:
                    return []
                user_id = user_resp.data.id

                followers = []
                paginator = tweepy.Paginator(
                    self._client.get_users_followers,
                    id=user_id,
                    max_results=min(max_count, 1000),
                    user_fields=[
                        "created_at", "public_metrics", "verified",
                        "profile_image_url", "description", "protected",
                    ],
                    limit=max_count // 100 + 1,
                )
                for response in paginator:
                    if response.data:
                        for user in response.data:
                            followers.append(self._twitter_user_to_dict(user))
                            if len(followers) >= max_count:
                                return followers
                return followers
            except Exception:
                pass

        if self._api:
            try:
                followers = []
                for user in tweepy.Cursor(self._api.get_followers, screen_name=username, count=200).items(max_count):
                    followers.append(self._twitter_user_to_dict_legacy(user))
                return followers
            except Exception:
                pass

        return []

    def _twitter_user_to_dict(self, user) -> dict:
        metrics = getattr(user, "public_metrics", {}) or {}
        created_at = getattr(user, "created_at", None)
        created_at_utc = to_utc_datetime(created_at) if created_at else None
        return {
            "user_id": str(user.id),
            "username": user.username,
            "display_name": user.name,
            "bio": getattr(user, "description", "") or "",
            "avatar_url": getattr(user, "profile_image_url", "") or "",
            "registration_date": format_utc_iso(created_at_utc),
            "followers_count": metrics.get("followers_count", 0),
            "following_count": metrics.get("following_count", 0),
            "posts_count": metrics.get("tweet_count", 0),
            "likes_count": metrics.get("like_count", 0) if "like_count" in metrics else 0,
            "is_verified": getattr(user, "verified", False) or False,
            "is_protected": getattr(user, "protected", False) or False,
            "has_profile_image": bool(getattr(user, "profile_image_url", "")),
            "bio_length": len(getattr(user, "description", "") or ""),
        }

    def _twitter_user_to_dict_legacy(self, user) -> dict:
        created_at = getattr(user, "created_at", None)
        created_at_utc = to_utc_datetime(created_at) if created_at else None
        return {
            "user_id": str(user.id),
            "username": user.screen_name,
            "display_name": user.name,
            "bio": getattr(user, "description", "") or "",
            "avatar_url": getattr(user, "profile_image_url_https", "") or "",
            "registration_date": format_utc_iso(created_at_utc),
            "followers_count": getattr(user, "followers_count", 0),
            "following_count": getattr(user, "friends_count", 0),
            "posts_count": getattr(user, "statuses_count", 0),
            "likes_count": getattr(user, "favourites_count", 0),
            "is_verified": getattr(user, "verified", False) or False,
            "is_protected": getattr(user, "protected", False) or False,
            "has_profile_image": bool(getattr(user, "profile_image_url_https", "") and not getattr(user, "default_profile_image", True)),
            "bio_length": len(getattr(user, "description", "") or ""),
        }

    def is_authenticated(self) -> bool:
        return self._client is not None or self._api is not None
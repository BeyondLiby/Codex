"""X/Twitter 数据源适配层。

本文件故意把第三方 API 的差异集中到一处：外部入口统一返回 SocialPost，
后面的监控、历史抓取和候选账户发现逻辑就不用关心供应商细节。
"""

import csv
import json
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.config import CONFIG
from app.ingestion.models import SearchSpec, SocialPost, parse_datetime


MENTION_RE = re.compile(r"@([A-Za-z0-9_]{1,30})")


class ApiClientError(RuntimeError):
    """第三方 API 调用失败时抛出的统一异常。"""


class BasePostClient(ABC):
    """所有数据源客户端的统一接口。"""

    source_name = "base"

    @abstractmethod
    def fetch_latest(self, spec: Optional[SearchSpec], limit: int = 50) -> List[SocialPost]:
        """获取符合条件的最新帖子。"""

    @abstractmethod
    def fetch_history(
        self,
        spec: SearchSpec,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> List[SocialPost]:
        """获取指定历史区间内的帖子。"""


class MagicalExportClient(BasePostClient):
    """读取 Magical/表格工具导出的 JSONL、JSON 或 CSV 文件，优先用于本地功能测试。"""

    source_name = "magical_export"

    def __init__(self, export_path: str):
        self.export_path = Path(export_path)

    def fetch_latest(self, spec: Optional[SearchSpec], limit: int = 50) -> List[SocialPost]:
        posts = self._load_posts()
        return _filter_posts(posts, spec)[:limit]

    def fetch_history(
        self,
        spec: SearchSpec,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> List[SocialPost]:
        posts = [
            post
            for post in self._load_posts()
            if post.created_at and start <= post.created_at <= end
        ]
        return _filter_posts(posts, spec)[:limit]

    def _load_posts(self) -> List[SocialPost]:
        if not self.export_path.exists():
            raise FileNotFoundError(f"Magical export file not found: {self.export_path}")

        rows: Iterable[Dict[str, Any]]
        suffix = self.export_path.suffix.lower()
        if suffix == ".jsonl":
            rows = _read_jsonl(self.export_path)
        elif suffix == ".json":
            data = json.loads(self.export_path.read_text(encoding="utf-8"))
            rows = data if isinstance(data, list) else data.get("posts", [])
        elif suffix == ".csv":
            with self.export_path.open("r", encoding="utf-8-sig", newline="") as fp:
                rows = list(csv.DictReader(fp))
        else:
            raise ValueError("Magical export must be .jsonl, .json, or .csv")

        return [_normalize_post(row, self.source_name) for row in rows]


class TwitterApiIOClient(BasePostClient):
    """TwitterAPI.io 适配器。

    该供应商支持高级搜索、用户时间线和 Webhook；这里先实现最稳定的搜索型接口，
    实时监控用短周期轮询验证功能，后续可在同一类里补 webhook 注册/回调。
    """

    source_name = "twitterapi_io"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.api_key = api_key or CONFIG.api.api_key
        self.base_url = (base_url or CONFIG.api.base_url or "https://api.twitterapi.io").rstrip("/")
        self.timeout_seconds = timeout_seconds or CONFIG.api.timeout_seconds

    def fetch_latest(self, spec: Optional[SearchSpec], limit: int = 50) -> List[SocialPost]:
        return self._advanced_search((spec or SearchSpec()).to_twitter_query(), query_type="Latest", limit=limit)

    def fetch_history(
        self,
        spec: SearchSpec,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> List[SocialPost]:
        return self._advanced_search(spec.to_twitter_query(start, end), query_type="Latest", limit=limit)

    def _advanced_search(self, query: str, query_type: str, limit: int) -> List[SocialPost]:
        if not query:
            return []

        payload = self._request_json(
            "/twitter/tweet/advanced_search",
            {
                "query": query,
                "queryType": query_type,
                "max_results": min(limit, 100),
            },
            {"X-API-Key": self.api_key},
        )
        items = _extract_items(payload, ["tweets", "data", "results"])
        return [_normalize_post(item, self.source_name) for item in items[:limit]]

    def _request_json(self, path: str, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}?{urlencode({k: v for k, v in params.items() if v is not None})}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ApiClientError(f"{self.source_name} HTTP {exc.code}: {detail}") from exc
        except OSError as exc:
            raise ApiClientError(f"{self.source_name} request failed: {exc}") from exc


class DesearchClient(BasePostClient):
    """Desearch Twitter API 适配器占位实现。

    Desearch 端点可能随账号套餐变化，这里把 path 做成配置项；如果实际返回字段不同，
    只需要调整 _extract_items 或 _normalize_post，不影响上层流程。
    """

    source_name = "desearch"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        search_path: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.api_key = api_key or CONFIG.api.api_key
        self.base_url = (base_url or CONFIG.api.base_url or "https://api.desearch.ai").rstrip("/")
        self.search_path = search_path or CONFIG.api.desearch_search_path
        self.timeout_seconds = timeout_seconds or CONFIG.api.timeout_seconds

    def fetch_latest(self, spec: Optional[SearchSpec], limit: int = 50) -> List[SocialPost]:
        return self._search((spec or SearchSpec()).to_twitter_query(), limit)

    def fetch_history(
        self,
        spec: SearchSpec,
        start: datetime,
        end: datetime,
        limit: int = 200,
    ) -> List[SocialPost]:
        return self._search(spec.to_twitter_query(start, end), limit)

    def _search(self, query: str, limit: int) -> List[SocialPost]:
        if not query:
            return []

        payload = self._request_json(
            self.search_path,
            {"query": query, "limit": limit},
            {"Authorization": f"Bearer {self.api_key}"},
        )
        items = _extract_items(payload, ["tweets", "posts", "data", "results"])
        return [_normalize_post(item, self.source_name) for item in items[:limit]]

    def _request_json(self, path: str, params: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        url = f"{self.base_url}{path}?{urlencode({k: v for k, v in params.items() if v is not None})}"
        request = Request(url, headers=headers)
        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ApiClientError(f"{self.source_name} HTTP {exc.code}: {detail}") from exc
        except OSError as exc:
            raise ApiClientError(f"{self.source_name} request failed: {exc}") from exc


def make_post_client(provider: Optional[str] = None) -> BasePostClient:
    """按配置创建数据源客户端。"""
    selected = (provider or CONFIG.api.provider).lower()
    if selected in {"magical", "magical_export", "export"}:
        return MagicalExportClient(CONFIG.api.magical_export_path)
    if selected in {"twitterapi", "twitterapi_io", "twitterapi.io"}:
        return TwitterApiIOClient()
    if selected in {"desearch", "desearch_ai"}:
        return DesearchClient()
    raise ValueError(f"Unsupported X_PROVIDER: {selected}")


def _read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                yield json.loads(line)


def _extract_items(payload: Dict[str, Any], candidate_keys: List[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    for key in candidate_keys:
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _extract_items(value, candidate_keys)
            if nested:
                return nested
    return []


def _filter_posts(posts: List[SocialPost], spec: Optional[SearchSpec]) -> List[SocialPost]:
    if spec is None:
        return sorted(posts, key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    keywords = [keyword.lower() for keyword in spec.keywords if keyword]
    users = {user.strip().lstrip("@").lower() for user in spec.users if user}

    filtered = []
    for post in posts:
        text = post.text.lower()
        author = post.author_username.lower()
        keyword_ok = not keywords or any(keyword in text for keyword in keywords)
        user_ok = not users or author in users
        if keyword_ok and user_ok:
            filtered.append(post)

    return sorted(filtered, key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)


def _normalize_post(row: Dict[str, Any], source: str) -> SocialPost:
    text = _first(row, ["text", "full_text", "content", "tweetText", "body"], "")
    author = _extract_author(row)
    created_at = parse_datetime(_first(row, ["created_at", "createdAt", "time", "timestamp", "date"]))
    media_urls = _extract_media_urls(row)

    return SocialPost(
        id=str(_first(row, ["id", "tweet_id", "tweetId", "post_id", "url"], "")),
        text=str(text or ""),
        author_username=author,
        created_at=created_at,
        url=_first(row, ["url", "tweet_url", "tweetUrl"]),
        media_urls=media_urls,
        mentioned_users=sorted(set(MENTION_RE.findall(str(text or "")))),
        reposted_user=_extract_nested_username(row, ["retweeted_tweet", "retweetedTweet", "repost"]),
        quoted_user=_extract_nested_username(row, ["quoted_tweet", "quotedTweet", "quote"]),
        metrics=_extract_metrics(row),
        raw=row,
        source=source,
    )


def _first(row: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return default


def _extract_author(row: Dict[str, Any]) -> str:
    direct = _first(row, ["author_username", "username", "userName", "screen_name", "author"], "")
    if isinstance(direct, str) and direct:
        return direct.strip().lstrip("@")
    if isinstance(direct, dict):
        return str(_first(direct, ["username", "userName", "screen_name"], "")).strip().lstrip("@")

    for key in ["user", "author", "authorDetails"]:
        value = row.get(key)
        if isinstance(value, dict):
            return str(_first(value, ["username", "userName", "screen_name"], "")).strip().lstrip("@")
    return ""


def _extract_media_urls(row: Dict[str, Any]) -> List[str]:
    values: List[str] = []
    for key in ["media_urls", "mediaUrls", "images", "photos"]:
        raw = row.get(key)
        if isinstance(raw, str):
            values.extend([item.strip() for item in raw.split(",") if item.strip()])
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, str):
                    values.append(item)
                elif isinstance(item, dict):
                    url = _first(item, ["url", "media_url_https", "mediaUrl", "preview_image_url"])
                    if url:
                        values.append(str(url))

    entities = row.get("extendedEntities") or row.get("extended_entities") or row.get("entities") or {}
    media = entities.get("media") if isinstance(entities, dict) else None
    if isinstance(media, list):
        for item in media:
            if isinstance(item, dict):
                url = _first(item, ["media_url_https", "media_url", "url"])
                if url:
                    values.append(str(url))

    return sorted(set(values))


def _extract_nested_username(row: Dict[str, Any], keys: List[str]) -> Optional[str]:
    for key in keys:
        value = row.get(key)
        if isinstance(value, dict):
            username = _extract_author(value)
            if username:
                return username
    return None


def _extract_metrics(row: Dict[str, Any]) -> Dict[str, Any]:
    metrics = row.get("metrics") or row.get("public_metrics") or {}
    if isinstance(metrics, dict):
        return metrics
    return {
        "like_count": _first(row, ["like_count", "likes", "favorite_count"]),
        "repost_count": _first(row, ["repost_count", "retweet_count", "retweets"]),
        "reply_count": _first(row, ["reply_count", "replies"]),
    }

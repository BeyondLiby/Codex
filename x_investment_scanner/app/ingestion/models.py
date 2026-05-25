"""社交平台帖子在项目内部使用的统一数据结构。"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def parse_datetime(value: Any) -> Optional[datetime]:
    """把 API 中常见的时间格式统一转换成带时区的 datetime。"""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@dataclass
class SearchSpec:
    """监控/历史抓取共用的查询条件。"""

    keywords: List[str] = field(default_factory=list)
    users: List[str] = field(default_factory=list)
    include_reposts: bool = True
    include_replies: bool = False
    language: Optional[str] = None

    def to_twitter_query(self, start: Optional[datetime] = None, end: Optional[datetime] = None) -> str:
        """生成多数 Twitter/X 第三方 API 都能理解的查询语句。"""
        parts: List[str] = []

        if self.keywords:
            keyword_query = " OR ".join(_quote_query_value(keyword) for keyword in self.keywords)
            parts.append(f"({keyword_query})")

        if self.users:
            user_query = " OR ".join(f"from:{_clean_username(user)}" for user in self.users)
            parts.append(f"({user_query})")

        if not self.include_replies:
            parts.append("-filter:replies")
        if not self.include_reposts:
            parts.append("-filter:retweets")
        if self.language:
            parts.append(f"lang:{self.language}")
        if start:
            parts.append(f"since:{start.date().isoformat()}")
        if end:
            parts.append(f"until:{end.date().isoformat()}")

        return " ".join(parts).strip()


@dataclass
class SocialPost:
    """内部标准帖子结构，后续过滤、存储、候选账户发现都只依赖它。"""

    id: str
    text: str
    author_username: str
    created_at: Optional[datetime] = None
    url: Optional[str] = None
    media_urls: List[str] = field(default_factory=list)
    mentioned_users: List[str] = field(default_factory=list)
    reposted_user: Optional[str] = None
    quoted_user: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    raw: Dict[str, Any] = field(default_factory=dict)
    source: str = "unknown"

    def to_storage_dict(self) -> Dict[str, Any]:
        """转换成可 JSON 序列化的落盘格式。"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat() if self.created_at else None
        return data


def _quote_query_value(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        return cleaned
    if cleaned.startswith("$") or cleaned.startswith("#") or ":" in cleaned:
        return cleaned
    return f'"{cleaned}"' if " " in cleaned else cleaned


def _clean_username(username: str) -> str:
    return username.strip().lstrip("@")

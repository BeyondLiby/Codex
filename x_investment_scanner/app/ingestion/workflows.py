"""监控、历史抓取和潜在关注账户发现的核心流程。"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from app.config import CONFIG
from app.ingestion.api_clients import BasePostClient
from app.ingestion.models import SearchSpec, SocialPost
from app.ingestion.storage import JsonlPostStore


def default_search_spec() -> SearchSpec:
    """从配置生成默认监控条件。"""
    return SearchSpec(
        keywords=CONFIG.filter.keywords + CONFIG.filter.cashtags,
        users=CONFIG.scan_policy.tracked_users,
        include_reposts=True,
        include_replies=False,
    )


def monitor_latest_once(
    client: BasePostClient,
    spec: Optional[SearchSpec] = None,
    store: Optional[JsonlPostStore] = None,
    limit: int = 50,
) -> Dict[str, object]:
    """执行一次近实时监控拉取，适合用 cron/while loop 反复调用。"""
    selected_spec = spec or default_search_spec()
    posts = client.fetch_latest(selected_spec, limit=limit)
    output_path = (store or JsonlPostStore()).save_posts(posts, "realtime")
    return {"count": len(posts), "path": str(output_path), "posts": posts}


def fetch_history_range(
    client: BasePostClient,
    start: datetime,
    end: datetime,
    spec: Optional[SearchSpec] = None,
    store: Optional[JsonlPostStore] = None,
    limit: int = 200,
) -> Dict[str, object]:
    """按时间区间抓取历史帖子并落盘。"""
    selected_spec = spec or default_search_spec()
    posts = client.fetch_history(selected_spec, start=start, end=end, limit=limit)
    output_path = (store or JsonlPostStore()).save_posts(posts, "history")
    return {"count": len(posts), "path": str(output_path), "posts": posts}


def discover_candidate_accounts(
    posts: Iterable[SocialPost],
    current_users: Iterable[str],
    top_n: int = 20,
) -> List[Dict[str, object]]:
    """根据 @、repost、quote 等互动信号发现潜在关注账户。"""
    current = {user.strip().lstrip("@").lower() for user in current_users}
    scores: Counter = Counter()
    reasons = defaultdict(list)

    for post in posts:
        for username in post.mentioned_users:
            _add_signal(username, "mentioned", 1, current, scores, reasons)
        if post.reposted_user:
            _add_signal(post.reposted_user, "reposted", 3, current, scores, reasons)
        if post.quoted_user:
            _add_signal(post.quoted_user, "quoted", 2, current, scores, reasons)

    ranked = []
    for username, score in scores.most_common(top_n):
        ranked.append(
            {
                "username": username,
                "score": score,
                "signals": dict(Counter(reasons[username])),
            }
        )
    return ranked


def _add_signal(
    username: str,
    signal: str,
    weight: int,
    current_users: set,
    scores: Counter,
    reasons: defaultdict,
) -> None:
    normalized = username.strip().lstrip("@")
    if not normalized or normalized.lower() in current_users:
        return
    scores[normalized] += weight
    reasons[normalized].append(signal)

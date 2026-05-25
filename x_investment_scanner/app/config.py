"""统一配置中心：所有可变参数尽量集中在本文件。

说明：
1. 所有扫描频率、关键词、账号层级、模型参数、告警阈值都在这里。
2. 生产环境建议通过环境变量注入敏感信息（API KEY、数据库连接）。
"""

from dataclasses import dataclass, field
from typing import Dict, List
import os


@dataclass
class DatabaseConfig:
    """数据库配置。"""

    url: str = os.getenv("DB_URL", "postgresql+psycopg2://postgres:postgres@localhost:5432/x_scanner")


@dataclass
class ApiConfig:
    """数据源 API 配置。"""

    provider: str = os.getenv("X_PROVIDER", "magical_export")  # magical_export / twitterapi_io / desearch
    base_url: str = os.getenv("X_API_BASE_URL", "")
    api_key: str = os.getenv("X_API_KEY", "PLEASE_SET_X_API_KEY")
    timeout_seconds: int = int(os.getenv("X_API_TIMEOUT", "20"))
    magical_export_path: str = os.getenv("X_MAGICAL_EXPORT_PATH", "data/sample_exports/magical_posts.jsonl")
    desearch_search_path: str = os.getenv("DESEARCH_SEARCH_PATH", "/twitter/search")


@dataclass
class StorageConfig:
    """抓取结果落盘配置。"""

    raw_posts_dir: str = os.getenv("RAW_POSTS_DIR", "data/raw_posts")
    candidate_accounts_path: str = os.getenv("CANDIDATE_ACCOUNTS_PATH", "data/candidate_accounts.json")


@dataclass
class OpenAIConfig:
    """LLM 相关配置。"""

    api_key: str = os.getenv("OPENAI_API_KEY", "PLEASE_SET_OPENAI_API_KEY")
    classify_model: str = os.getenv("OPENAI_CLASSIFY_MODEL", "gpt-5-mini")
    extract_model: str = os.getenv("OPENAI_EXTRACT_MODEL", "gpt-5")
    judge_model: str = os.getenv("OPENAI_JUDGE_MODEL", "gpt-5")
    digest_model: str = os.getenv("OPENAI_DIGEST_MODEL", "gpt-5")


@dataclass
class ScanPolicyConfig:
    """账号分层与扫描策略。"""

    # tier -> minutes
    tier_scan_interval_minutes: Dict[str, int] = field(
        default_factory=lambda: {"S": 5, "A": 20, "B": 720, "Candidate": 10080}
    )
    # tier -> max posts each pull
    tier_post_limit: Dict[str, int] = field(
        default_factory=lambda: {"S": 20, "A": 30, "B": 50, "Candidate": 100}
    )
    tracked_users: List[str] = field(default_factory=lambda: ["macro_focus", "alpha_researcher"])
    realtime_poll_seconds: int = int(os.getenv("REALTIME_POLL_SECONDS", "60"))


@dataclass
class FilterConfig:
    """规则过滤参数。"""

    keywords: List[str] = field(
        default_factory=lambda: [
            "AI infrastructure",
            "optical networking",
            "semiconductor",
            "M&A",
            "takeout",
            "short squeeze",
            "ATM offering",
            "dilution",
            "guidance raise",
            "options flow",
            "10Y yield",
            "duration",
        ]
    )
    cashtags: List[str] = field(
        default_factory=lambda: ["$SIVE", "$CPSH", "$LITE", "$COHR", "$NVDA", "$TLT"]
    )
    drop_keywords: List[str] = field(
        default_factory=lambda: ["to the moon", "gm", "good night", "meme"]
    )


@dataclass
class AlertConfig:
    """告警阈值参数。"""

    min_quality_accounts_1h: int = 3
    trigger_keywords: List[str] = field(
        default_factory=lambda: ["offering", "ATM", "dilution", "merger", "acquisition", "guidance"]
    )
    notify_channels: List[str] = field(default_factory=lambda: ["telegram"])


@dataclass
class AppConfig:
    """应用总配置。"""

    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    scan_policy: ScanPolicyConfig = field(default_factory=ScanPolicyConfig)
    filter: FilterConfig = field(default_factory=FilterConfig)
    alert: AlertConfig = field(default_factory=AlertConfig)


CONFIG = AppConfig()

"""帖子抓取结果的轻量 JSONL 存储。"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from app.config import CONFIG
from app.ingestion.models import SocialPost


class JsonlPostStore:
    """按数据集和日期保存帖子，适合 MVP 测试与后续导入数据库。"""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir or CONFIG.storage.raw_posts_dir)

    def save_posts(self, posts: Iterable[SocialPost], dataset: str) -> Path:
        """写入 JSONL，并按 post id 做简单去重。"""
        post_list = list(posts)
        day = datetime.now(timezone.utc).date().isoformat()
        target_dir = self.base_dir / dataset
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{day}.jsonl"

        known_ids = self._read_known_ids(target_path)
        with target_path.open("a", encoding="utf-8") as fp:
            for post in post_list:
                if post.id in known_ids:
                    continue
                fp.write(json.dumps(post.to_storage_dict(), ensure_ascii=False) + "\n")
                known_ids.add(post.id)

        return target_path

    @staticmethod
    def _read_known_ids(path: Path) -> set:
        if not path.exists():
            return set()
        ids = set()
        with path.open("r", encoding="utf-8") as fp:
            for line in fp:
                try:
                    item = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if item.get("id"):
                    ids.add(str(item["id"]))
        return ids


def load_posts_from_jsonl(path: str) -> List[dict]:
    """给测试和候选账户分析使用的 JSONL 读取函数。"""
    rows: List[dict] = []
    with Path(path).open("r", encoding="utf-8") as fp:
        for line in fp:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows

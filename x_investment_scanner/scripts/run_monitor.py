"""测试实时监控：拉取最新帖子并保存为 JSONL。"""

import argparse
import time

from app.config import CONFIG
from app.ingestion.api_clients import make_post_client
from app.ingestion.models import SearchSpec
from app.ingestion.workflows import monitor_latest_once


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default=None, help="magical_export / twitterapi_io / desearch")
    parser.add_argument("--keyword", action="append", default=[], help="可重复传入多个关键词")
    parser.add_argument("--user", action="append", default=[], help="可重复传入多个用户名")
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--loop", action="store_true", help="持续轮询，模拟实时监控流")
    parser.add_argument("--interval", type=int, default=CONFIG.scan_policy.realtime_poll_seconds)
    args = parser.parse_args()

    client = make_post_client(args.provider)
    spec = SearchSpec(keywords=args.keyword, users=args.user) if args.keyword or args.user else None

    while True:
        result = monitor_latest_once(client, spec=spec, limit=args.limit)
        print({"count": result["count"], "path": result["path"]})
        if not args.loop:
            break
        time.sleep(args.interval)


if __name__ == "__main__":
    main()

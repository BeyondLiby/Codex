"""测试历史抓取：按时间区间拉取帖子并保存为 JSONL。"""

import argparse

from app.ingestion.api_clients import make_post_client
from app.ingestion.models import SearchSpec, parse_datetime
from app.ingestion.workflows import fetch_history_range


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", default=None, help="magical_export / twitterapi_io / desearch")
    parser.add_argument("--start", required=True, help="开始时间，例如 2026-05-20T00:00:00+00:00")
    parser.add_argument("--end", required=True, help="结束时间，例如 2026-05-25T00:00:00+00:00")
    parser.add_argument("--keyword", action="append", default=[], help="可重复传入多个关键词")
    parser.add_argument("--user", action="append", default=[], help="可重复传入多个用户名")
    parser.add_argument("--limit", type=int, default=200)
    args = parser.parse_args()

    start = parse_datetime(args.start)
    end = parse_datetime(args.end)
    if not start or not end:
        raise ValueError("--start and --end must be valid ISO datetime strings")

    spec = SearchSpec(keywords=args.keyword, users=args.user) if args.keyword or args.user else None
    result = fetch_history_range(make_post_client(args.provider), start=start, end=end, spec=spec, limit=args.limit)
    print({"count": result["count"], "path": result["path"]})


if __name__ == "__main__":
    main()

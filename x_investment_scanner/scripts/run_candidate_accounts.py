"""测试潜在相关账户发现。"""

import argparse
import json
from pathlib import Path

from app.config import CONFIG
from app.ingestion.api_clients import MagicalExportClient
from app.ingestion.workflows import discover_candidate_accounts


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", default=CONFIG.api.magical_export_path, help="Magical/JSONL/CSV 导出文件")
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()

    client = MagicalExportClient(args.source)
    posts = client.fetch_latest(spec=None, limit=1000)
    candidates = discover_candidate_accounts(posts, CONFIG.scan_policy.tracked_users, top_n=args.top_n)

    output_path = Path(CONFIG.storage.candidate_accounts_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(candidates, ensure_ascii=False, indent=2), encoding="utf-8")
    print({"count": len(candidates), "path": str(output_path), "candidates": candidates})


if __name__ == "__main__":
    main()

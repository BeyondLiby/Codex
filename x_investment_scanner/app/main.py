"""命令行入口。"""

from app.ingestion.scanner import run_scan_cycle


if __name__ == "__main__":
    # 示例账号输入，实际项目建议从数据库读取。
    accounts = [
        {
            "username": "alpha_researcher",
            "mock_posts": [
                {"id": "1", "text": "$SIVE possible acquisition optionality, watch offering risk."},
                {"id": "2", "text": "good night everyone"},
            ],
        }
    ]

    results = run_scan_cycle(accounts)
    print(results)

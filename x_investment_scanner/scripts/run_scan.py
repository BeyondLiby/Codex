from app.ingestion.scanner import run_scan_cycle

accounts = [
    {
        "username": "macro_focus",
        "mock_posts": [
            {"id": "101", "text": "10Y yield and duration positioning changes, $TLT watch guidance"}
        ],
    }
]

print(run_scan_cycle(accounts))

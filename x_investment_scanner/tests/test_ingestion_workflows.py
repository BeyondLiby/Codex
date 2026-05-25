import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from app.ingestion.api_clients import MagicalExportClient
from app.ingestion.models import SearchSpec
from app.ingestion.storage import JsonlPostStore
from app.ingestion.workflows import (
    discover_candidate_accounts,
    fetch_history_range,
    monitor_latest_once,
)


class IngestionWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.export_path = Path(self.temp_dir.name) / "magical_posts.jsonl"
        rows = [
            {
                "id": "p1",
                "text": "$NVDA AI infrastructure check from @semicap_daily",
                "author_username": "macro_focus",
                "created_at": "2026-05-24T10:00:00+00:00",
                "media_urls": ["https://example.com/chart.png"],
            },
            {
                "id": "p2",
                "text": "ATM offering risk via @dilution_tracker",
                "author_username": "alpha_researcher",
                "created_at": "2026-05-20T10:00:00+00:00",
                "retweeted_tweet": {"author_username": "dilution_tracker"},
            },
            {
                "id": "p3",
                "text": "good night",
                "author_username": "macro_focus",
                "created_at": "2026-05-19T10:00:00+00:00",
            },
        ]
        with self.export_path.open("w", encoding="utf-8") as fp:
            for row in rows:
                fp.write(json.dumps(row) + "\n")

        self.client = MagicalExportClient(str(self.export_path))
        self.store = JsonlPostStore(str(Path(self.temp_dir.name) / "raw_posts"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_monitor_latest_once_saves_normalized_posts(self):
        spec = SearchSpec(keywords=["AI infrastructure"], users=["macro_focus"])
        result = monitor_latest_once(self.client, spec=spec, store=self.store, limit=10)

        self.assertEqual(result["count"], 1)
        output = Path(result["path"])
        self.assertTrue(output.exists())
        saved = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(saved[0]["id"], "p1")
        self.assertEqual(saved[0]["media_urls"], ["https://example.com/chart.png"])

    def test_history_fetch_filters_by_date_range(self):
        spec = SearchSpec(keywords=["offering"])
        result = fetch_history_range(
            self.client,
            start=datetime(2026, 5, 20, tzinfo=timezone.utc),
            end=datetime(2026, 5, 21, tzinfo=timezone.utc),
            spec=spec,
            store=self.store,
            limit=10,
        )

        self.assertEqual(result["count"], 1)
        self.assertEqual(result["posts"][0].id, "p2")

    def test_candidate_accounts_are_ranked_from_mentions_and_reposts(self):
        posts = self.client.fetch_latest(spec=None, limit=10)
        candidates = discover_candidate_accounts(posts, current_users=["macro_focus", "alpha_researcher"])

        self.assertEqual(candidates[0]["username"], "dilution_tracker")
        self.assertEqual(candidates[0]["score"], 4)


if __name__ == "__main__":
    unittest.main()

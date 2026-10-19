import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
import render

SERVICES = {"title": "VictorHub", "services": [
    {"name": "Website", "description": "Public site", "url": "https://example.com"},
    {"name": "API", "description": "Health", "url": "https://example.com/api"},
]}


def results(website_ok, api_ok, checked_at):
    return {"checks": [
        {"service": "Website", "ok": website_ok, "status_code": 200,
         "checked_at": checked_at},
        {"service": "API", "ok": api_ok, "status_code": 500, "error": "HTTP 500",
         "checked_at": checked_at},
    ]}


class StatusTests(unittest.TestCase):
    def test_all_up(self):
        now = dt.datetime(2026, 10, 19, 12, 0, tzinfo=dt.timezone.utc)
        data = results(True, True, "2026-10-19T11:59:00+00:00")
        evaluated, overall = render.evaluate(SERVICES, data, 30, now)
        self.assertEqual(overall, "operational")
        self.assertTrue(all(item["status"] == "up" for item in evaluated))

    def test_down_wins(self):
        now = dt.datetime(2026, 10, 19, 12, 0, tzinfo=dt.timezone.utc)
        data = results(True, False, "2026-10-19T11:59:00+00:00")
        evaluated, overall = render.evaluate(SERVICES, data, 30, now)
        self.assertEqual(overall, "outage")
        self.assertEqual(evaluated[1]["status"], "down")

    def test_stale_is_unknown(self):
        now = dt.datetime(2026, 10, 19, 12, 0, tzinfo=dt.timezone.utc)
        data = results(True, True, "2026-10-19T08:00:00+00:00")
        evaluated, overall = render.evaluate(SERVICES, data, 30, now)
        self.assertEqual(overall, "degraded")
        self.assertTrue(all(item["status"] == "unknown" for item in evaluated))

    def test_missing_check_is_unknown(self):
        evaluated, overall = render.evaluate(SERVICES, {"checks": []}, 30)
        self.assertEqual(overall, "degraded")
        self.assertEqual({item["status"] for item in evaluated}, {"unknown"})

    def test_render_escapes_html(self):
        services = json.loads(json.dumps(SERVICES))
        services["title"] = "<script>"
        html_text = render.render(services, [], "degraded")
        self.assertNotIn("<script>", html_text)
        self.assertIn("&lt;script&gt;", html_text)

    def test_cli_writes_page(self):
        with tempfile.TemporaryDirectory() as tmp:
            services_path = Path(tmp) / "services.json"
            results_path = Path(tmp) / "results.json"
            out = Path(tmp) / "index.html"
            services_path.write_text(json.dumps(SERVICES))
            now = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
            results_path.write_text(json.dumps(results(True, True, now)))
            code = render.main([str(services_path), "--results", str(results_path),
                                "--out", str(out)])
            self.assertEqual(code, 0)
            self.assertIn("VictorHub", out.read_text())


if __name__ == "__main__":
    unittest.main()

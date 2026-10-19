#!/usr/bin/env python3
"""Render a static status page from services and check results."""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import sys
from pathlib import Path

CSS = """
:root { --bg:#0f172a; --panel:#1e293b; --text:#e2e8f0; --up:#22c55e;
        --down:#ef4444; --unknown:#eab308; }
* { box-sizing:border-box; }
body { margin:0; padding:2rem; background:var(--bg); color:var(--text);
       font-family:system-ui, sans-serif; }
main { max-width:760px; margin:0 auto; }
.banner { padding:1rem 1.25rem; border-radius:0.75rem; background:var(--panel);
          margin-bottom:2rem; font-weight:600; }
ul { list-style:none; padding:0; }
li { display:flex; justify-content:space-between; align-items:center;
     background:var(--panel); border-radius:0.75rem; padding:1rem 1.25rem;
     margin-bottom:0.75rem; }
.dot { width:0.75rem; height:0.75rem; border-radius:50%; display:inline-block;
       margin-right:0.5rem; }
.up { color:var(--up); } .down { color:var(--down); } .unknown { color:var(--unknown); }
.dot.up { background:var(--up); } .dot.down { background:var(--down); }
.dot.unknown { background:var(--unknown); }
small { color:#94a3b8; }
"""


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate(services, results, max_age_minutes: int, now: dt.datetime | None = None):
    now = now or dt.datetime.now(dt.timezone.utc)
    by_name = {item["service"]: item for item in results.get("checks", [])}
    evaluated = []
    for service in services["services"]:
        check = by_name.get(service["name"])
        status = "unknown"
        detail = "no recent check"
        if check:
            try:
                checked = dt.datetime.fromisoformat(check["checked_at"])
            except (KeyError, ValueError):
                checked = None
            age = (now - checked).total_seconds() / 60 if checked else None
            if age is not None and age > max_age_minutes:
                detail = f"stale check ({age:.0f} min old)"
            elif check.get("ok"):
                status, detail = "up", f"HTTP {check.get('status_code', '?')}"
            else:
                status, detail = "down", check.get("error", "check failed")
        evaluated.append({**service, "status": status, "detail": detail})
    overall = "operational"
    if any(item["status"] == "down" for item in evaluated):
        overall = "outage"
    elif any(item["status"] == "unknown" for item in evaluated):
        overall = "degraded"
    return evaluated, overall


def render(services, evaluated, overall) -> str:
    rows = []
    for service in evaluated:
        rows.append(
            f'<li><span><span class="dot {service["status"]}"></span>'
            f'<strong>{html.escape(service["name"])}</strong><br>'
            f'<small>{html.escape(service.get("description", ""))}</small></span>'
            f'<span class="{service["status"]}">{service["status"]} '
            f'<small>{html.escape(service["detail"])}</small></span></li>'
        )
    return (
        "<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        f"<title>{html.escape(services['title'])} status</title>\n"
        f"<style>{CSS}</style>\n</head>\n<body>\n<main>\n"
        f"<h1>{html.escape(services['title'])}</h1>\n"
        f'<div class="banner">{html.escape(overall)}</div>\n'
        f"<ul>{''.join(rows)}</ul>\n</main>\n</body>\n</html>\n"
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Status page renderer")
    parser.add_argument("services", type=Path)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("index.html"))
    parser.add_argument("--max-age", type=int, default=30)
    args = parser.parse_args(argv)

    try:
        services = load(args.services)
        results = load(args.results)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    evaluated, overall = evaluate(services, results, args.max_age)
    args.out.write_text(render(services, evaluated, overall), encoding="utf-8")
    print(f"wrote {args.out} ({overall})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

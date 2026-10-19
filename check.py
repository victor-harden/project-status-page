#!/usr/bin/env python3
"""Run HTTP checks and record results for the status page."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


def check_service(service: dict, timeout: float = 5.0) -> dict:
    url = service["url"]
    expected = int(service.get("expect", 200))
    checked_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            code = response.status
            return {"service": service["name"], "ok": code == expected,
                    "status_code": code, "checked_at": checked_at}
    except urllib.error.HTTPError as exc:
        return {"service": service["name"], "ok": exc.code == expected,
                "status_code": exc.code, "checked_at": checked_at}
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        return {"service": service["name"], "ok": False, "error": str(exc),
                "checked_at": checked_at}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="HTTP checks")
    parser.add_argument("services", type=Path)
    parser.add_argument("--out", type=Path, default=Path("results.json"))
    parser.add_argument("--timeout", type=float, default=5.0)
    args = parser.parse_args(argv)

    try:
        services = json.loads(args.services.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read services: {exc}", file=sys.stderr)
        return 2
    checks = [check_service(service, args.timeout) for service in services["services"]]
    payload = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
               "checks": checks}
    args.out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    failing = [c["service"] for c in checks if not c["ok"]]
    print(f"checked {len(checks)} services; failing: {failing or 'none'}")
    return 0 if not failing else 1


if __name__ == "__main__":
    raise SystemExit(main())

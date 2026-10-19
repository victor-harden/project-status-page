# project-status-page

A status page generator that stays honest: services are declared in JSON, check
results are recorded separately, and the generated page marks anything without a
recent success as degraded instead of silently green.

## Features

- `services.json`: name, description, URL and expected status.
- `check.py`: runs HTTP checks and writes `results.json` with timestamps.
- `render.py`: builds a static `index.html` with per-service status and overall
  banner.
- Stale results (older than `--max-age`) are shown as "unknown", never as "up".
- Tests cover rendering, staleness and exit codes.

## Installation

```bash
git clone https://github.com/victor-harden/project-status-page.git
cd project-status-page
```

## Usage

```bash
python3 check.py services.example.json --out results.json
python3 render.py services.example.json --results results.json --out index.html
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).

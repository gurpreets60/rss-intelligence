# RSS Intelligence CLI

Local-first RSS intelligence tool that fetches feeds, filters/deduplicates stories, clusters related items, and summarizes clusters via a local Ollama model (default: phi3). Output is deterministic and cached so repeated runs only show new content.

## Features
- Typer-based CLI with `news fetch`, `news summarize`, and `news watch` commands.
- Configurable filters: recency windows, keywords, domains, tags, max item caps.
- Canonicalization + dedupe to drop tracking parameters and fuzzy-duplicate titles.
- Lightweight text clustering plus spec-compliant Ollama summaries with local fallback.
- Persistent cache (`.news_cache/state.json`) to track seen links and clusters.
- Plain-text render by default with optional `--color`.

## Install
```bash
python -m venv .venv
. .venv/bin/activate
pip install -e .[dev]
```

## Usage
Create a `feeds.yaml` (sample provided) and run:
```bash
news --help
news fetch --config feeds.yaml --since 24h --include "ai" --color
news summarize --config feeds.yaml --since 3d --threshold 0.6 --max-items 40
news watch --config feeds.yaml --interval 30m --notify
```

## Testing
All tests are offline and mock network/LLM calls:
```bash
. .venv/bin/activate
pytest -q
```

## System Notes
- Developed and tested on Linux (Arch); other Unix-like systems should work as long as Python 3.11+ is available.
- Requires a local Ollama installation with the `phi3` model for summaries (`ollama serve` / `ollama run phi3`).
- Notifications in `news watch --notify` rely on `notify-send` (libnotify/Xorg); without it the CLI falls back to plaintext messages.

.venv/bin/activate && pytest

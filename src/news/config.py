from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError


class OllamaSettings(BaseModel):
    enabled: bool = True
    base_url: str = "http://127.0.0.1:11434"
    model: str = "phi3"
    timeout_s: int = 30


class Settings(BaseModel):
    user_agent: str = "news-cli/0.1"
    timeout_s: int = 10
    max_items_per_feed: int = 40
    cache_dir: str = ".news_cache"
    default_since: str = "48h"
    top_n_fetch: int = 5
    ollama: OllamaSettings = Field(default_factory=OllamaSettings)

    def cache_path(self, base_path: Path | None = None) -> Path:
        root = Path(base_path or ".")
        cache = root / self.cache_dir
        cache.mkdir(parents=True, exist_ok=True)
        return cache


class FeedConfig(BaseModel):
    name: str
    url: str
    tags: list[str] = Field(default_factory=list)


class AppConfig(BaseModel):
    settings: Settings = Field(default_factory=Settings)
    feeds: list[FeedConfig]

    def ensure_cache_dir(self, base_path: Path | None = None) -> Path:
        return self.settings.cache_path(base_path)


@dataclass(slots=True)
class ConfigLoadResult:
    config: AppConfig
    path: Path


def load_config(path: str | Path = "feeds.yaml") -> ConfigLoadResult:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config file not found: {cfg_path}")
    data = yaml.safe_load(cfg_path.read_text()) or {}
    try:
        config = AppConfig.model_validate(data)
    except ValidationError as exc:
        raise ValueError(f"Invalid config file {cfg_path}: {exc}") from exc
    return ConfigLoadResult(config=config, path=cfg_path)


def parse_since_window(value: str | None, *, now: datetime | None = None) -> datetime | None:
    if not value:
        return None
    now = now or datetime.now(tz=timezone.utc)
    delta = parse_duration(value)
    return now - delta


def parse_duration(value: str) -> timedelta:
    amount, unit = _split_duration(value.strip())
    return _duration_to_timedelta(amount, unit)


def _split_duration(raw: str) -> tuple[int, str]:
    if len(raw) < 2:
        msg = "Duration format must be like '24h' or '3d'."
        raise ValueError(msg)
    digits = ""
    for ch in raw:
        if ch.isdigit():
            digits += ch
        else:
            if not digits:
                raise ValueError("Duration missing numeric value.")
            unit = raw[len(digits) :].strip().lower()
            if not unit:
                raise ValueError("Missing time unit in duration.")
            return int(digits), unit
    raise ValueError("Missing time unit in duration.")


def _duration_to_timedelta(amount: int, unit: str) -> timedelta:
    match unit:
        case "s" | "sec" | "secs":
            return timedelta(seconds=amount)
        case "m" | "min" | "mins":
            return timedelta(minutes=amount)
        case "h" | "hr" | "hrs" | "hour" | "hours":
            return timedelta(hours=amount)
        case "d" | "day" | "days":
            return timedelta(days=amount)
        case "w" | "week" | "weeks":
            return timedelta(weeks=amount)
        case _:
            raise ValueError(f"Unsupported duration unit: {unit}")


def build_since_from_cli(since: str | None, settings: Settings) -> datetime | None:
    return parse_since_window(since or settings.default_since)

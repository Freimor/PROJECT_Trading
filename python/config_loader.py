"""Load YAML config from trading_wiki."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml


def wiki_root() -> Path:
    env = os.environ.get("WIKI_CONFIG_PATH")
    if env:
        return Path(env)
    # Docker: /data/trading_wiki; local dev: repo/trading_wiki
    for candidate in (
        Path("/data/trading_wiki"),
        Path(__file__).resolve().parents[1] / "trading_wiki",
        Path(__file__).resolve().parents[2] / "trading_wiki",
    ):
        if (candidate / "config" / "guardrails.yaml").exists():
            return candidate
    return Path(__file__).resolve().parents[2] / "trading_wiki"


def load_config(name: str) -> dict[str, Any]:
    path = wiki_root() / "config" / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return data


def load_prompt_body(filename: str) -> str:
    path = wiki_root() / "prompts" / filename
    if not path.exists():
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8")

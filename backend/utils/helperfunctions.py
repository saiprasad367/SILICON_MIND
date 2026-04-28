"""
helperfunctions.py - Shared utilities for the backend.
"""
import re
import os
import json
import hashlib
from datetime import datetime
from typing import Any, Dict


def slugify(text: str) -> str:
    """Convert text to filesystem-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "_", text)
    return text.strip("_-")


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely cast to float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def timestamp_str() -> str:
    return datetime.utcnow().strftime("%Y%m%d_%H%M%S")


def file_hash(path: str) -> str:
    """Return MD5 hash of file contents."""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
    except Exception:
        pass
    return h.hexdigest()


def flatten_dict(d: Dict, sep: str = "_", prefix: str = "") -> Dict:
    """Flatten nested dict."""
    items = {}
    for k, v in d.items():
        key = f"{prefix}{sep}{k}" if prefix else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, sep, key))
        else:
            items[key] = v
    return items


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def json_safe(obj: Any) -> Any:
    """Make object JSON-serialisable."""
    if isinstance(obj, dict):
        return {k: json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [json_safe(i) for i in obj]
    if isinstance(obj, (int, float, str, bool, type(None))):
        return obj
    return str(obj)

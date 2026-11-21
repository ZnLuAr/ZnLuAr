"""Validated WakaTime snapshot and its rendering-friendly view for the hero carousel."""

from hero.scene import GEN_DIR, load_json

WAKATIME_PATH = GEN_DIR / "wakatime.json"
MAX_LANGUAGES = 6
MAX_EDITORS = 3
MAX_OPERATING_SYSTEMS = 3
EXCLUDED_LANGUAGE_NAMES = {"Other"}
RANGE_DAYS = {"last_7_days": 7, "last_30_days": 30}
RANGE_LABELS = {"last_7_days": "LAST 7 DAYS", "last_30_days": "LAST 30 DAYS"}
SNAPSHOT_KEYS = {
    "placeholder",
    "fetched_at",
    "range",
    "total",
    "daily_average",
    "languages",
    "editors",
    "operating_systems",
}


def _validate_entry(entry, kind):
    if set(entry) != {"name", "percent", "text"}:
        raise ValueError(f"WakaTime {kind} entries must only carry name, percent and text")
    if not isinstance(entry["name"], str) or not entry["name"].strip():
        raise ValueError(f"WakaTime {kind} names must be non-empty strings")
    percent = entry["percent"]
    if not isinstance(percent, (int, float)) or not 0 < percent <= 100:
        raise ValueError(f"WakaTime {kind} percentages must be within (0, 100]")
    if not isinstance(entry["text"], str) or not entry["text"].strip():
        raise ValueError(f"WakaTime {kind} durations must be non-empty strings")


def _validate_duration(duration, kind):
    if set(duration) != {"seconds", "text"}:
        raise ValueError(f"WakaTime {kind} must only carry seconds and text")
    if not isinstance(duration["seconds"], (int, float)) or duration["seconds"] <= 0:
        raise ValueError(f"WakaTime {kind} seconds must be positive")
    if not isinstance(duration["text"], str) or not duration["text"].strip():
        raise ValueError(f"WakaTime {kind} text must be a non-empty string")


def validate_wakatime(snapshot):
    if set(snapshot) != SNAPSHOT_KEYS:
        raise ValueError("WakaTime snapshot fields do not match the declared schema")
    if not isinstance(snapshot["placeholder"], bool):
        raise ValueError("WakaTime placeholder flag must be a boolean")
    if snapshot["range"] not in RANGE_DAYS:
        raise ValueError(f"Unsupported WakaTime range: {snapshot['range']}")
    if not isinstance(snapshot["fetched_at"], str) or "T" not in snapshot["fetched_at"]:
        raise ValueError("WakaTime fetched_at must be an ISO timestamp")
    _validate_duration(snapshot["total"], "total")
    _validate_duration(snapshot["daily_average"], "daily average")
    for key, limit in (
        ("languages", MAX_LANGUAGES),
        ("editors", MAX_EDITORS),
        ("operating_systems", MAX_OPERATING_SYSTEMS),
    ):
        entries = snapshot[key]
        if not isinstance(entries, list) or not 1 <= len(entries) <= limit:
            raise ValueError(f"WakaTime {key} must contain between 1 and {limit} entries")
        for entry in entries:
            _validate_entry(entry, key)
    return snapshot


def load_wakatime():
    """Return the validated snapshot, or None before any data has been captured."""
    if not WAKATIME_PATH.is_file():
        return None
    return validate_wakatime(load_json(WAKATIME_PATH))


def wakatime_view(snapshot):
    """Project the snapshot into the bounded values the SVG renderer draws."""
    validate_wakatime(snapshot)
    return {
        "range_label": RANGE_LABELS[snapshot["range"]],
        "updated_label": snapshot["fetched_at"][:10],
        "total": snapshot["total"]["text"],
        "daily_average": snapshot["daily_average"]["text"],
        "languages": [(entry["name"], entry["percent"]) for entry in snapshot["languages"]],
        "editors": [(entry["name"], entry["percent"]) for entry in snapshot["editors"]],
        "operating_systems": [
            (entry["name"], entry["percent"]) for entry in snapshot["operating_systems"]
        ],
    }

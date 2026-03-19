"""
Agent configuration loader
===========================
Reads behaviour thresholds from data/config.json at import time.
To change agent behaviour, edit data/config.json — no code changes needed.
"""

import json
from pathlib import Path

_CONFIG_FILE = Path("data/config.json")

_DEFAULTS = {
    "chaser_frequency_days": 2,
    "advance_warning_days": 2,
    "escalation_threshold_days": 3,
    "re_escalation_gap_days": 3,
}


def _load_config() -> dict:
    """Load config from file, falling back to defaults for missing keys."""
    if _CONFIG_FILE.exists():
        with open(_CONFIG_FILE, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        return {**_DEFAULTS, **user_config}
    return dict(_DEFAULTS)


_config = _load_config()

CHASER_FREQUENCY_DAYS: int = _config["chaser_frequency_days"]
ADVANCE_WARNING_DAYS: int = _config["advance_warning_days"]
ESCALATION_THRESHOLD_DAYS: int = _config["escalation_threshold_days"]
RE_ESCALATION_GAP_DAYS: int = _config["re_escalation_gap_days"]

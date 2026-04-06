"""
Simulated date management
=========================
REFERENCE_DATE is loaded from settings (which reads .env) at import time.

The ``advance_reference_date()`` function increments by one day and persists
the new value back to ``.env`` so that subsequent runs pick it up.
"""

import datetime as dt
import re
from pathlib import Path

from project_manager_agent.core.config import settings

_ENV_FILE = Path(".env")


def _update_env_reference_date(date: dt.date) -> None:
    """Write the new REFERENCE_DATE back into .env so it persists."""
    env_text = _ENV_FILE.read_text(encoding="utf-8") if _ENV_FILE.exists() else ""
    new_line = f"REFERENCE_DATE={date.isoformat()}"

    if re.search(r"^REFERENCE_DATE=", env_text, re.MULTILINE):
        env_text = re.sub(
            r"^REFERENCE_DATE=.*$", new_line, env_text, flags=re.MULTILINE
        )
    else:
        env_text = env_text.rstrip("\n") + f"\n{new_line}\n"

    _ENV_FILE.write_text(env_text, encoding="utf-8")


def advance_reference_date() -> None:
    """Increment the reference date by one day and persist to .env."""
    next_date = REFERENCE_DATE + dt.timedelta(days=1)
    _update_env_reference_date(next_date)
    print(f"Reference date advanced to {next_date}")


# Loaded once at import time from .env via pydantic-settings.
# To reset or jump to a specific date, edit REFERENCE_DATE in .env:
#   REFERENCE_DATE=2026-03-19
REFERENCE_DATE: dt.date = settings.reference_date

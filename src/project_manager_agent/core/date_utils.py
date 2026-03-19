import json
import datetime as dt
from pathlib import Path

_DATE_FILE = Path("data/date.json")


def load_reference_date() -> dt.date:
    """
    Load the reference date from data/date.json.

    Defaults to today if the file does not exist, and creates it so that
    subsequent runs can advance from there.
    """
    if _DATE_FILE.exists():
        with open(_DATE_FILE, "r", encoding="utf-8") as f:
            return dt.date.fromisoformat(json.load(f)["reference_date"])
    date = dt.date.today()
    _save_reference_date(date)
    return date


def _save_reference_date(date: dt.date) -> None:
    """Persist a date to data/date.json."""
    with open(_DATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"reference_date": date.isoformat()}, f)


def advance_reference_date() -> None:
    """Increment the reference date by one day and save it."""
    next_date = REFERENCE_DATE + dt.timedelta(days=1)
    _save_reference_date(next_date)
    print(f"Reference date advanced to {next_date}")


# Loaded once at import time.
# To reset or jump to a specific date, edit data/date.json directly:
#   {"reference_date": "2026-03-19"}
REFERENCE_DATE: dt.date = load_reference_date()

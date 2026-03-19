'''
Reset Script
============
Clears all runtime data to allow a clean test run:
  - Empties data/inbox/messages.jsonl
  - Empties data/outbox/messages.jsonl
  - Deletes all journal files in data/journal/
  - Deletes tasks.json, project.json, raid.json, actions.json
    so the next run re-seeds from scratch
  - Optionally deletes all reports in data/reports/ (--reports flag)
  - Resets data/date.json to START_DATE
'''
import json
import argparse
from pathlib import Path

DATA = Path('data')

INBOX_FILE   = DATA / 'inbox'  / 'messages.jsonl'
OUTBOX_FILE  = DATA / 'outbox' / 'messages.jsonl'
JOURNAL_DIR  = DATA / 'journal'
REPORTS_DIR  = DATA / 'reports'
TASKS_FILE   = DATA / 'tasks.json'
PROJECT_FILE = DATA / 'project.json'
RAID_FILE    = DATA / 'raid.json'
ACTIONS_FILE = DATA / 'actions.json'
DATE_FILE    = DATA / 'date.json'

START_DATE = '2026-03-19'


def reset(start_date: str = START_DATE, clear_reports: bool = False) -> None:
    cleared = []

    for path in (INBOX_FILE, OUTBOX_FILE, TASKS_FILE, PROJECT_FILE, RAID_FILE, ACTIONS_FILE):
        if path.exists():
            path.unlink()
            cleared.append(str(path))

    for journal in JOURNAL_DIR.glob('*.md'):
        journal.unlink()
        cleared.append(str(journal))

    if clear_reports:
        for report in REPORTS_DIR.glob('*.md'):
            report.unlink()
            cleared.append(str(report))

    with open(DATE_FILE, 'w', encoding='utf-8') as f:
        json.dump({'reference_date': start_date}, f)
    cleared.append(f'{DATE_FILE} → {start_date}')

    print('Cleared:')
    for item in cleared:
        print(f'  {item}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reset project manager runtime data.')
    parser.add_argument(
        '--date',
        default=START_DATE,
        help=f'Start date to reset to (YYYY-MM-DD). Defaults to {START_DATE}.',
    )
    parser.add_argument(
        '--reports',
        action='store_true',
        help='Also delete all generated reports in data/reports/.',
    )
    args = parser.parse_args()
    reset(args.date, clear_reports=args.reports)

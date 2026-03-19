'''
Demo Data Setup
===============
Populates data/ with a realistic mid-project scenario for testing and demos.

Scenario: "Customer Portal Modernisation"
  - Phase 1 (Discovery) is complete with milestone achieved.
  - Phase 2 (Design & Build) is in progress — one task blocked, milestone slipping.
  - Phase 3 (Testing & Launch) is not yet started.
  - RAG is AMBER due to milestone slip caused by a blocked database task.
  - RAID log contains risks, an open issue, two assumptions (one validated,
    one overdue for validation), and two decisions.
  - One action is overdue, two are open.
  - Inbox contains two messages awaiting processing.
  - Date is set to 2026-03-20 (mid-project).

Run from the project root:
    python create_demo_data.py
'''
import json
from pathlib import Path

DATA = Path('data')

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(content, f, indent=4)


def _write_jsonl(path: Path, lines: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        for line in lines:
            f.write(json.dumps(line) + '\n')


# ---------------------------------------------------------------------------
# Project plan
# ---------------------------------------------------------------------------

PROJECT = {
    'name': 'Customer Portal Modernisation',
    'description': (
        'Replace the legacy customer portal with a modern, responsive web '
        'application backed by a new API layer and migrated database.'
    ),
    'objectives': [
        'Deliver a responsive customer portal that reduces support call volume by 20%.',
        'Migrate all customer data to the new database with zero data loss.',
        'Achieve go-live by end of April 2026 with full security sign-off.',
    ],
    'sponsor': 'Alice (CTO)',
    'project_manager': 'Project Manager Agent',
    'planned_start': '2026-03-01',
    'planned_end':   '2026-04-30',
    'actual_start':  '2026-03-01',
    'forecast_end':  '2026-05-07',   # slipped one week
    'rag_status': 'amber',
    'rag_reason': (
        'Build milestone has slipped by one week due to DBA sign-off delay on '
        'the database schema, blocking the migration task. Frontend and API '
        'development remain on track. Recovery is feasible if the DBA review '
        'is completed by 2026-03-24.'
    ),
    'phases': [
        {
            'phase_id': 1,
            'name': 'Discovery',
            'description': 'Stakeholder interviews, requirements capture, and UX research.',
            'planned_start': '2026-03-01',
            'planned_end':   '2026-03-10',
        },
        {
            'phase_id': 2,
            'name': 'Design & Build',
            'description': 'Technical architecture, API development, frontend build, and DB migration.',
            'planned_start': '2026-03-11',
            'planned_end':   '2026-04-11',
        },
        {
            'phase_id': 3,
            'name': 'Testing & Launch',
            'description': 'UAT, security review, performance testing, and go-live.',
            'planned_start': '2026-04-14',
            'planned_end':   '2026-04-30',
        },
    ],
    'milestones': [
        {
            'milestone_id': 1,
            'name': 'Discovery Complete',
            'description': 'All requirements captured, wireframes approved, architecture agreed.',
            'planned_date': '2026-03-10',
            'forecast_date': '2026-03-10',
            'actual_date': '2026-03-10',
            'status': 'achieved',
            'linked_task_ids': [1, 2, 3, 4],
        },
        {
            'milestone_id': 2,
            'name': 'Build Complete',
            'description': 'API, frontend, and database migration all complete and integrated.',
            'planned_date': '2026-04-11',
            'forecast_date': '2026-04-18',   # slipped one week
            'actual_date': None,
            'status': 'pending',
            'linked_task_ids': [5, 6, 7, 8],
        },
        {
            'milestone_id': 3,
            'name': 'Go-Live',
            'description': 'New portal live in production, legacy system decommissioned.',
            'planned_date': '2026-04-30',
            'forecast_date': '2026-05-07',   # propagated slip
            'actual_date': None,
            'status': 'pending',
            'linked_task_ids': [9, 10, 11],
        },
    ],
}

# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

TASKS = [
    # Phase 1 — Discovery (all complete)
    {
        'task_id': 1,
        'description': 'Conduct stakeholder interviews',
        'owner_name': 'Mary',
        'owner_email': 'mary@test.com',
        'due_date': '2026-03-05',
        'status': 'complete',
        'phase_id': 1,
        'depends_on': [],
        'blocked_reason': None,
        'external_dependency': None,
    },
    {
        'task_id': 2,
        'description': 'Write business requirements document',
        'owner_name': 'Mary',
        'owner_email': 'mary@test.com',
        'due_date': '2026-03-07',
        'status': 'complete',
        'phase_id': 1,
        'depends_on': [1],
        'blocked_reason': None,
        'external_dependency': None,
    },
    {
        'task_id': 3,
        'description': 'Produce UX wireframes',
        'owner_name': 'Sarah',
        'owner_email': 'sarah@test.com',
        'due_date': '2026-03-08',
        'status': 'complete',
        'phase_id': 1,
        'depends_on': [1],
        'blocked_reason': None,
        'external_dependency': None,
    },
    {
        'task_id': 4,
        'description': 'Design technical architecture',
        'owner_name': 'Chris',
        'owner_email': 'chris@test.com',
        'due_date': '2026-03-10',
        'status': 'complete',
        'phase_id': 1,
        'depends_on': [2],
        'blocked_reason': None,
        'external_dependency': None,
    },

    # Phase 2 — Design & Build (in progress / blocked)
    {
        'task_id': 5,
        'description': 'Develop REST API layer',
        'owner_name': 'Chris',
        'owner_email': 'chris@test.com',
        'due_date': '2026-03-28',
        'status': 'in_progress',
        'phase_id': 2,
        'depends_on': [4],
        'blocked_reason': None,
        'external_dependency': None,
    },
    {
        'task_id': 6,
        'description': 'Build frontend application',
        'owner_name': 'Sarah',
        'owner_email': 'sarah@test.com',
        'due_date': '2026-04-04',
        'status': 'in_progress',
        'phase_id': 2,
        'depends_on': [3, 4],
        'blocked_reason': None,
        'external_dependency': None,
    },
    {
        'task_id': 7,
        'description': 'Migrate database to new schema',
        'owner_name': 'Chris',
        'owner_email': 'chris@test.com',
        'due_date': '2026-04-04',
        'status': 'blocked',
        'phase_id': 2,
        'depends_on': [5],
        'blocked_reason': 'Awaiting DBA sign-off on schema changes. Raised with Bob (DBA) on 2026-03-15 — no response yet.',
        'external_dependency': 'DBA team schema review and approval',
    },
    {
        'task_id': 8,
        'description': 'Integration testing',
        'owner_name': 'Bob',
        'owner_email': 'bob@test.com',
        'due_date': '2026-04-11',
        'status': 'not_started',
        'phase_id': 2,
        'depends_on': [5, 6, 7],
        'blocked_reason': None,
        'external_dependency': None,
    },

    # Phase 3 — Testing & Launch (not started)
    {
        'task_id': 9,
        'description': 'User acceptance testing',
        'owner_name': 'Mary',
        'owner_email': 'mary@test.com',
        'due_date': '2026-04-22',
        'status': 'not_started',
        'phase_id': 3,
        'depends_on': [8],
        'blocked_reason': None,
        'external_dependency': None,
    },
    {
        'task_id': 10,
        'description': 'Security penetration test and sign-off',
        'owner_name': 'Bob',
        'owner_email': 'bob@test.com',
        'due_date': '2026-04-22',
        'status': 'not_started',
        'phase_id': 3,
        'depends_on': [8],
        'blocked_reason': None,
        'external_dependency': 'External security firm — engagement letter signed, slot booked for w/c 2026-04-14.',
    },
    {
        'task_id': 11,
        'description': 'Go-live deployment and cutover',
        'owner_name': 'Chris',
        'owner_email': 'chris@test.com',
        'due_date': '2026-04-30',
        'status': 'not_started',
        'phase_id': 3,
        'depends_on': [9, 10],
        'blocked_reason': None,
        'external_dependency': None,
    },
]

# ---------------------------------------------------------------------------
# RAID log
# ---------------------------------------------------------------------------

RAID = [
    {
        'raid_id': 1,
        'type': 'risk',
        'title': 'DBA resource unavailability causes further migration delay',
        'description': (
            'The DBA team is under-resourced and has not yet reviewed the schema '
            'change request submitted on 2026-03-15. Further delay would push the '
            'database migration past its window and cascade to integration testing.'
        ),
        'owner': 'Bob',
        'raised_date': '2026-03-15',
        'status': 'open',
        'linked_task_ids': [7, 8],
        'probability': 'high',
        'impact': 'high',
        'mitigation': (
            'Escalate to DBA team lead by 2026-03-21. Identify a secondary DBA '
            'who can deputise if primary reviewer remains unavailable.'
        ),
        'review_date': '2026-03-21',
        # non-risk fields null
        'validation_method': None, 'validation_date': None, 'validated_by': None,
        'severity': None, 'resolution': None, 'resolved_date': None,
        'rationale': None, 'decided_by': None, 'decision_date': None,
        'alternatives_considered': None,
    },
    {
        'raid_id': 2,
        'type': 'risk',
        'title': 'Breaking changes to third-party payment API',
        'description': (
            'The payment provider has announced an API v3 deprecation with a '
            '90-day notice. If our integration targets v2, we may need emergency '
            'rework before go-live.'
        ),
        'owner': 'Chris',
        'raised_date': '2026-03-12',
        'status': 'open',
        'linked_task_ids': [5, 11],
        'probability': 'medium',
        'impact': 'high',
        'mitigation': (
            'Chris to confirm which API version is targeted and document a '
            'versioning strategy by 2026-03-28.'
        ),
        'review_date': '2026-03-28',
        'validation_method': None, 'validation_date': None, 'validated_by': None,
        'severity': None, 'resolution': None, 'resolved_date': None,
        'rationale': None, 'decided_by': None, 'decision_date': None,
        'alternatives_considered': None,
    },
    {
        'raid_id': 3,
        'type': 'assumption',
        'title': 'Cloud infrastructure will be provisioned before build phase ends',
        'description': (
            'We are assuming that the cloud hosting environment (staging and '
            'production) will be provisioned by the internal infrastructure team '
            'in time for integration testing to start on 2026-04-14.'
        ),
        'owner': 'Mary',
        'raised_date': '2026-03-01',
        'status': 'open',
        'linked_task_ids': [8, 9, 10, 11],
        'probability': None, 'impact': None, 'mitigation': None, 'review_date': None,
        'validation_method': 'Confirm provisioning timeline with infra team lead.',
        'validation_date': '2026-03-20',    # today — overdue for validation
        'validated_by': None,               # NOT yet validated
        'severity': None, 'resolution': None, 'resolved_date': None,
        'rationale': None, 'decided_by': None, 'decision_date': None,
        'alternatives_considered': None,
    },
    {
        'raid_id': 4,
        'type': 'assumption',
        'title': 'Users will be available for UAT during w/c 2026-04-14',
        'description': (
            'We are assuming that at least 10 representative users can participate '
            'in UAT sessions during the week of 2026-04-14.'
        ),
        'owner': 'Mary',
        'raised_date': '2026-03-01',
        'status': 'open',
        'linked_task_ids': [9],
        'probability': None, 'impact': None, 'mitigation': None, 'review_date': None,
        'validation_method': 'Mary to confirm UAT participant list with business leads.',
        'validation_date': '2026-03-25',
        'validated_by': None,
        'severity': None, 'resolution': None, 'resolved_date': None,
        'rationale': None, 'decided_by': None, 'decision_date': None,
        'alternatives_considered': None,
    },
    {
        'raid_id': 5,
        'type': 'issue',
        'title': 'DBA schema sign-off delayed — blocking database migration',
        'description': (
            'The schema change request submitted to the DBA team on 2026-03-15 '
            'has not been reviewed. Task 7 (database migration) cannot begin '
            'until sign-off is received, and the delay is now five days.'
        ),
        'owner': 'Bob',
        'raised_date': '2026-03-20',
        'status': 'open',
        'linked_task_ids': [7],
        'probability': None, 'impact': None, 'mitigation': None, 'review_date': None,
        'validation_method': None, 'validation_date': None, 'validated_by': None,
        'severity': 'high',
        'resolution': None,
        'resolved_date': None,
        'rationale': None, 'decided_by': None, 'decision_date': None,
        'alternatives_considered': None,
    },
    {
        'raid_id': 6,
        'type': 'decision',
        'title': 'Use React for the frontend application',
        'description': (
            'Agreed to use React (with TypeScript) as the frontend framework '
            'rather than Vue or Angular.'
        ),
        'owner': 'Chris',
        'raised_date': '2026-03-05',
        'status': 'closed',
        'linked_task_ids': [6],
        'probability': None, 'impact': None, 'mitigation': None, 'review_date': None,
        'validation_method': None, 'validation_date': None, 'validated_by': None,
        'severity': None, 'resolution': None, 'resolved_date': None,
        'rationale': (
            'Team has strongest existing React skills. Large component ecosystem '
            'reduces build time. Vue and Angular both considered but rejected due '
            'to lower team familiarity.'
        ),
        'decided_by': 'Chris',
        'decision_date': '2026-03-05',
        'alternatives_considered': 'Vue 3 (good ecosystem, less team familiarity); Angular (rejected — overkill for this scale).',
    },
    {
        'raid_id': 7,
        'type': 'decision',
        'title': 'Defer mobile native app to a follow-on project',
        'description': (
            'A native mobile app was in scope in the original brief. Agreed '
            'to descope it from this project and treat it as a follow-on initiative.'
        ),
        'owner': 'Alice',
        'raised_date': '2026-03-15',
        'status': 'closed',
        'linked_task_ids': [],
        'probability': None, 'impact': None, 'mitigation': None, 'review_date': None,
        'validation_method': None, 'validation_date': None, 'validated_by': None,
        'severity': None, 'resolution': None, 'resolved_date': None,
        'rationale': (
            'The responsive web portal will be accessible on mobile browsers, '
            'covering the primary use cases. A native app adds 6+ weeks and '
            'would push go-live past the business deadline.'
        ),
        'decided_by': 'Alice',
        'decision_date': '2026-03-15',
        'alternatives_considered': 'Keep mobile app in scope (rejected — timeline impact unacceptable).',
    },
]

# ---------------------------------------------------------------------------
# Actions
# ---------------------------------------------------------------------------

ACTIONS = [
    {
        'action_id': 1,
        'description': (
            'Escalate DBA schema sign-off to DBA team lead — request review '
            'be completed by 2026-03-24.'
        ),
        'owner_name': 'Bob',
        'owner_email': 'bob@test.com',
        'due_date': '2026-03-15',           # overdue
        'status': 'open',
        'source_raid_id': 1,
        'source_task_id': 7,
    },
    {
        'action_id': 2,
        'description': (
            'Confirm cloud infrastructure provisioning timeline with the '
            'infrastructure team lead and update the project plan.'
        ),
        'owner_name': 'Mary',
        'owner_email': 'mary@test.com',
        'due_date': '2026-03-22',
        'status': 'open',
        'source_raid_id': 3,
        'source_task_id': None,
    },
    {
        'action_id': 3,
        'description': (
            'Document the API versioning strategy and confirm whether the '
            'payment integration targets v2 or v3 of the provider API.'
        ),
        'owner_name': 'Chris',
        'owner_email': 'chris@test.com',
        'due_date': '2026-03-28',
        'status': 'open',
        'source_raid_id': 2,
        'source_task_id': None,
    },
]

# ---------------------------------------------------------------------------
# Inbox messages (awaiting processing by the agent)
# ---------------------------------------------------------------------------

INBOX_MESSAGES = [
    {
        'timestamp': '2026-03-20T08:14:00',
        'sender_name': 'Chris',
        'sender_email': 'chris@test.com',
        'message': (
            'Just a heads-up — the database schema is still with the DBA team. '
            'I chased again yesterday but no response. This is now blocking my '
            'migration work. Can we get this escalated? API development is going '
            'well and I expect to have a working build by next Friday.'
        ),
    },
    {
        'timestamp': '2026-03-20T09:02:00',
        'sender_name': 'Sarah',
        'sender_email': 'sarah@test.com',
        'message': (
            'Frontend is on track. I expect to complete the main views by '
            '2026-04-04 as planned. No blockers at the moment.'
        ),
    },
]

# ---------------------------------------------------------------------------
# Outbox (one reminder already sent — simulates prior agent run)
# ---------------------------------------------------------------------------

OUTBOX_MESSAGES = [
    {
        'timestamp': '2026-03-18T09:00:00',
        'owner_name': 'Bob',
        'owner_email': 'bob@test.com',
        'message': (
            'Hi Bob, this is a reminder that Action 1 is overdue: please escalate '
            'the DBA schema sign-off to the DBA team lead. This is blocking the '
            'database migration task (Task 7). Please provide an update by end of day.'
        ),
    },
]

# ---------------------------------------------------------------------------
# Reference date
# ---------------------------------------------------------------------------

DATE = {'reference_date': '2026-03-20'}

# ---------------------------------------------------------------------------
# Write all files
# ---------------------------------------------------------------------------

def create() -> None:
    _write(DATA / 'project.json',              PROJECT)
    _write(DATA / 'tasks.json',                TASKS)
    _write(DATA / 'raid.json',                 RAID)
    _write(DATA / 'actions.json',              ACTIONS)
    _write(DATA / 'date.json',                 DATE)
    _write_jsonl(DATA / 'inbox'  / 'messages.jsonl', INBOX_MESSAGES)
    _write_jsonl(DATA / 'outbox' / 'messages.jsonl', OUTBOX_MESSAGES)

    (DATA / 'journal').mkdir(parents=True, exist_ok=True)
    (DATA / 'reports').mkdir(parents=True, exist_ok=True)

    print('Demo data created:')
    print(f'  Project:  {PROJECT["name"]}')
    print(f'  Date:     {DATE["reference_date"]}')
    print(f'  RAG:      {PROJECT["rag_status"].upper()}')
    print(f'  Tasks:    {len(TASKS)} ({sum(1 for t in TASKS if t["status"] == "complete")} complete, '
          f'{sum(1 for t in TASKS if t["status"] == "in_progress")} in progress, '
          f'{sum(1 for t in TASKS if t["status"] == "blocked")} blocked)')
    print(f'  RAID:     {len(RAID)} items '
          f'({sum(1 for r in RAID if r["type"] == "risk")} risks, '
          f'{sum(1 for r in RAID if r["type"] == "assumption")} assumptions, '
          f'{sum(1 for r in RAID if r["type"] == "issue")} issues, '
          f'{sum(1 for r in RAID if r["type"] == "decision")} decisions)')
    print(f'  Actions:  {len(ACTIONS)} open '
          f'(1 overdue)')
    print(f'  Inbox:    {len(INBOX_MESSAGES)} unprocessed messages')


if __name__ == '__main__':
    create()

'''
Basic Project Manager
=====================
An AI agent that runs on a schedule. On each execution it follows a structured
daily loop:

  1. Opens today's journal and writes an opening entry.
  2. Reads the inbox and documents its thinking about any messages received.
  3. Fetches the task list and writes a plan for the day.
  4. Sends reminders for any tasks due today (informed by inbox context).
  5. Writes a closing entry summarising actions taken.

The agent is built with LangGraph. The graph has two nodes:
  - project-manager: the LLM that decides which tools to call.
  - tools:           executes the chosen tool and returns the result.

The graph loops between these two nodes until the LLM has no more
tool calls to make, at which point tools_condition routes to END.

Data directories:
  data/tasks.json              — task database
  data/inbox/messages.jsonl    — incoming messages from task owners
  data/outbox/messages.jsonl   — outgoing reminders sent by the agent
  data/journal/YYYY-MM-DD.md   — daily journal of the agent's thinking
'''
import json
import datetime as dt
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Annotated, Any, TypedDict

from dotenv import load_dotenv
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import Tool, StructuredTool
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import ToolNode, tools_condition


load_dotenv(override=True)

# Set this to any date to test agent behaviour on that day.
# Use REFERENCE_DATE for normal production runs.
REFERENCE_DATE: dt.date = dt.date(2026, 3, 24)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class Task:
    '''A single project task with its owner and due date.'''
    task_id: int
    description: str
    owner_name: str
    owner_email: str
    due_date: dt.date


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

class JsonSerialiser(json.JSONEncoder):
    '''Extends the default JSON encoder to handle dt.date objects.'''

    def default(self, o: Any) -> str:
        if isinstance(o, dt.date):
            return o.isoformat()
        return super().default(o)


class TasksRepo:
    '''Reads and writes tasks to a JSON file on disk.'''

    TASKS_PATH = Path('data/tasks.json')

    def initialise(self) -> None:
        '''Seed the database with sample tasks if it does not already exist.'''
        if not self.TASKS_PATH.exists():
            initial_tasks = [
                Task(1, 'Write business requirements', 'Mary', 'mary@test.com', dt.date(2026, 3, 18)),
                Task(2, 'Review business requirements', 'Bob', 'bob@test.com', dt.date(2026, 3, 25)),
                Task(3, 'Approve business requirements', 'Bob', 'bob@test.com', dt.date(2026, 3, 26)),
                Task(4, 'Create IT plan', 'Chris', 'chris@test.com', dt.date(2026, 3, 18)),
            ]
            with open(self.TASKS_PATH, 'w', encoding='utf-8') as f:
                json.dump([asdict(task) for task in initial_tasks], f, cls=JsonSerialiser, indent=4)

    def read(self) -> list[Task]:
        '''Load all tasks from the database, deserialising due_date strings to dt.date.'''
        with open(self.TASKS_PATH, 'r', encoding='utf-8') as f:
            tasks = json.load(f)
            for task in tasks:
                task['due_date'] = dt.date.fromisoformat(task['due_date'])
            return [Task(**task) for task in tasks]


class Mailbox:
    '''
    Manages the agent's inbox and outbox directories.

    Both use JSONL format (one JSON object per line), so messages accumulate
    across runs and can be processed or appended independently.

    Outbox (data/outbox/messages.jsonl):
        Written by the agent. Each entry is a reminder sent to a task owner.

    Inbox (data/inbox/messages.jsonl):
        Written by external systems (e.g. task owners replying with updates).
        Read by the agent to check for incoming updates before acting.
    '''

    INBOX_PATH = Path('data/inbox')
    OUTBOX_PATH = Path('data/outbox')
    INBOX_FILE = INBOX_PATH / 'messages.jsonl'
    OUTBOX_FILE = OUTBOX_PATH / 'messages.jsonl'

    def initialise(self) -> None:
        '''Create inbox and outbox directories if they do not already exist.'''
        self.INBOX_PATH.mkdir(parents=True, exist_ok=True)
        self.OUTBOX_PATH.mkdir(parents=True, exist_ok=True)

    def send(self, owner_name: str, owner_email: str, message: str) -> None:
        '''
        Append a message to the outbox.

        Args:
            owner_name:  Display name of the recipient.
            owner_email: Email address of the recipient.
            message:     Message body.
        '''
        entry = {
            'timestamp': dt.datetime.now().isoformat(),
            'owner_name': owner_name,
            'owner_email': owner_email,
            'message': message,
        }
        with open(self.OUTBOX_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + '\n')

    def read_inbox(self) -> list[dict]:
        '''
        Return all messages from the inbox as a list of dicts.

        Returns an empty list if the inbox file does not yet exist.
        Each dict contains the keys written by the sender, typically:
          - timestamp:    ISO 8601 string
          - sender_name:  Display name of the sender
          - sender_email: Email address of the sender
          - message:      Message body
        '''
        if not self.INBOX_FILE.exists():
            return []
        with open(self.INBOX_FILE, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]

    def read_outbox(self) -> list[dict]:
        '''
        Return all previously sent messages from the outbox as a list of dicts.

        Returns an empty list if no messages have been sent yet. Each dict contains:
          - timestamp:   ISO 8601 string of when the message was sent
          - owner_name:  Display name of the recipient
          - owner_email: Email address of the recipient
          - message:     Message body
        '''
        if not self.OUTBOX_FILE.exists():
            return []
        with open(self.OUTBOX_FILE, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]


class Journal:
    '''
    Maintains a daily markdown journal of the agent's thinking and actions.

    Each day gets its own file at data/journal/YYYY-MM-DD.md. Entries are
    appended throughout the agent's loop so the full reasoning trail is
    preserved in chronological order.

    Format:
        # Project Manager Journal — YYYY-MM-DD

        ## <Section Title>
        *HH:MM:SS*

        <Content>
    '''

    JOURNAL_PATH = Path('data/journal')

    def initialise(self) -> None:
        '''Create the journal directory if it does not already exist.'''
        self.JOURNAL_PATH.mkdir(parents=True, exist_ok=True)

    @property
    def today_file(self) -> Path:
        '''Path to today's journal file.'''
        return self.JOURNAL_PATH / f'{REFERENCE_DATE}.md'

    def read_last(self) -> str | None:
        '''
        Return the full content of the most recent journal file before today.

        Returns None if no previous journal exists. Useful for the agent to
        review what was noted and actioned on prior runs before deciding what
        to do today.
        '''
        past_journals = sorted(
            (f for f in self.JOURNAL_PATH.glob('*.md') if f.stem < str(REFERENCE_DATE)),
            reverse=True,
        )
        if not past_journals:
            return None
        with open(past_journals[0], 'r', encoding='utf-8') as f:
            return f.read()

    def write(self, section: str, content: str) -> None:
        '''
        Append a titled section to today's journal.

        Creates the journal file with a header if it does not yet exist.

        Args:
            section: Section heading (e.g. "Inbox Review", "Daily Plan").
            content: The agent's notes or reasoning for this section.
        '''
        if not self.today_file.exists():
            with open(self.today_file, 'w', encoding='utf-8') as f:
                f.write(f'# Project Manager Journal — {REFERENCE_DATE}\n\n')

        timestamp = dt.datetime.now().strftime('%H:%M:%S')
        with open(self.today_file, 'a', encoding='utf-8') as f:
            f.write(f'## {section}\n*{timestamp}*\n\n{content}\n\n')


# ---------------------------------------------------------------------------
# Tool functions
# ---------------------------------------------------------------------------

def read_last_journal() -> str:
    '''
    Read the most recent previous journal entry.

    Returns:
        The full markdown content of the last journal, or a message indicating
        none exists. Use this to understand what was actioned on prior runs.
    '''
    content = Journal().read_last()
    return content if content is not None else 'No previous journal found.'


def read_outbox() -> list[dict]:
    '''
    Read all previously sent outbox messages.

    Returns:
        List of message dicts with timestamp, owner_name, owner_email, and message.
        Use this to check when a reminder was last sent to each person before
        deciding whether to send another.
    '''
    return Mailbox().read_outbox()


def read_inbox() -> list[dict]:
    '''
    Read all messages from the inbox.

    Returns:
        List of message dicts, or an empty list if the inbox is empty.
        Each message may contain updates or replies from task owners.
    '''
    return Mailbox().read_inbox()


def send_message(owner_name: str, owner_email: str, message: str) -> str:
    '''
    Append a reminder to the outbox and print a confirmation.

    Args:
        owner_name:  Display name of the task owner.
        owner_email: Email address of the task owner.
        message:     Reminder message body.

    Returns:
        Confirmation string indicating the message was queued.
    '''
    Mailbox().send(owner_name, owner_email, message)
    print(f"Message queued for {owner_name} ({owner_email}): {message}")
    return f"Message queued for {owner_name}"


def write_journal_entry(section: str, content: str) -> str:
    '''
    Append an entry to today's journal.

    Args:
        section: Heading for this journal entry (e.g. "Inbox Review").
        content: The agent's notes, observations, or reasoning.

    Returns:
        Confirmation string.
    '''
    Journal().write(section, content)
    return f"Journal entry written: {section}"


# ---------------------------------------------------------------------------
# LangChain tool definitions
# The `description` field is included verbatim in the prompt sent to the LLM,
# so precise wording directly affects how reliably the model calls each tool.
# ---------------------------------------------------------------------------

fetch_last_journal_tool = Tool(
    name='fetch_last_journal',
    description=(
        'Read the most recent previous journal. Use this at the start of each run '
        'to understand what was noted and actioned before.'
    ),
    func=lambda _: read_last_journal()
)

fetch_outbox_tool = Tool(
    name='fetch_outbox_messages',
    description=(
        'Read all previously sent reminder messages. Use this before sending any new '
        'reminder to check when one was last sent to each person and avoid over-chasing.'
    ),
    func=lambda _: read_outbox()
)

fetch_tasks_tool = Tool(
    name='fetch_tasks_from_database',
    description='Fetch the current list of all project tasks.',
    func=lambda _: TasksRepo().read()
)

fetch_inbox_tool = Tool(
    name='fetch_inbox_messages',
    description='Read all messages received in the inbox from task owners.',
    func=lambda _: read_inbox()
)

class SendMessageInput(BaseModel):
    '''Input schema for the send_message_to_task_owner tool.'''
    owner_name: str
    owner_email: str
    message: str


class WriteJournalEntryInput(BaseModel):
    '''Input schema for the write_journal_entry tool.'''
    section: str
    content: str


communications_tool = StructuredTool(
    name='send_message_to_task_owner',
    description='Send a reminder message to a task owner.',
    func=send_message,
    args_schema=SendMessageInput,
)


write_journal_tool = StructuredTool(
    name='write_journal_entry',
    description=(
        'Append a titled entry to today\'s journal to document thinking, observations, '
        'or a summary of actions taken.'
    ),
    func=write_journal_entry,
    args_schema=WriteJournalEntryInput,
)

tools = [
    fetch_last_journal_tool,
    fetch_outbox_tool,
    fetch_inbox_tool,
    fetch_tasks_tool,
    write_journal_tool,
    communications_tool,
]


# ---------------------------------------------------------------------------
# Graph state
# `messages` uses add_messages so each node appends to the conversation
# history rather than overwriting it — required for the tool-call loop.
# ---------------------------------------------------------------------------

class State(TypedDict):
    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

project_manager_llm = ChatOpenAI(model='gpt-4o-mini')
project_manager_llm_with_tools = project_manager_llm.bind_tools(tools)

# Today's date is injected at startup so the LLM knows what "today" means
# without relying on its own (potentially stale) knowledge.
PM_SYSTEM_PROMPT = f'''You are a project manager running your daily check-in. Today is {REFERENCE_DATE}.

Follow these steps in order, using your tools at each stage:

1. CONTEXT REVIEW
   - Call fetch_last_journal to read what was noted and actioned on the previous run.
   - Call fetch_outbox_messages to see all reminders sent so far, noting the timestamp
     of the most recent message sent to each person.
   - Call write_journal_entry with section "Context Review", summarising the key points
     from the last journal and any recent outbox activity worth noting.

2. INBOX REVIEW
   - Call fetch_inbox_messages to read any incoming messages.
   - Call write_journal_entry with section "Inbox Review", documenting each message
     and your thoughts on what it means for the project.

3. TASK REVIEW & DAILY PLAN
   - Call fetch_tasks_from_database to get the full task list.
   - Call write_journal_entry with section "Task Review & Daily Plan", listing which
     tasks are due today, noting relevant inbox and outbox context, and stating your
     intended actions.

4. SEND REMINDERS
   - Before sending any reminder, check the outbox history for that person.
     Do not send a chaser if one was already sent within the last 2 days — note the
     reason for skipping in the journal instead.
   - For each task due today that still requires a reminder, call send_message_to_task_owner
     with a helpful, specific message.
   - Call write_journal_entry with section "Actions Taken", summarising every message
     sent or skipped and the reasoning behind each decision.
'''


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------

def project_manager_node(state: State) -> dict:
    '''
    Invoke the LLM with the current message history.

    The LLM follows the daily loop defined in the system prompt, calling tools
    at each phase. tools_condition routes back to the tools node while tool
    calls remain, then to END when the loop is complete.
    '''
    response = project_manager_llm_with_tools.invoke(state['messages'])
    return {'messages': [response]}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph():
    '''
    Assemble and compile the LangGraph state machine.

    Graph topology:
        START -> project-manager <-> tools
    The project-manager node runs first. If the LLM emits tool calls,
    tools_condition routes to the tools node, which executes them and
    loops back. When the LLM emits a plain response, tools_condition
    routes to END.

    Also writes a visualisation of the graph to project_manager_graph.png.
    '''
    graph_builder = StateGraph(State)

    graph_builder.add_node('project-manager', project_manager_node)
    graph_builder.add_node('tools', ToolNode(tools=tools))

    graph_builder.add_edge(START, 'project-manager')
    graph_builder.add_conditional_edges('project-manager', tools_condition, 'tools')
    graph_builder.add_edge('tools', 'project-manager')

    graph = graph_builder.compile()

    with open('project_manager_graph.png', 'wb') as f:
        f.write(graph.get_graph().draw_mermaid_png())

    return graph


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':

    Mailbox().initialise()
    Journal().initialise()

    task_repo = TasksRepo()
    task_repo.initialise()

    graph = build_graph()
    graph.invoke({
        'messages': [
            SystemMessage(PM_SYSTEM_PROMPT),
            HumanMessage('Please run your daily project management loop.'),
        ]
    })

"""
Project Manager Agent
=====================
An AI agent that runs on a schedule. On each execution it follows a structured
daily loop:

  1. Reviews context (last journal, outbox history).
  2. Reviews the project plan — phases, milestones, RAG status.
  3. Reviews the RAID log — open risks, issues, unvalidated assumptions, and
     overdue actions.
  4. Reads the inbox and updates task/RAID/action statuses accordingly.
  5. Reviews the task list, checks dependencies, and assesses milestone impact.
  6. Sends reminders for tasks due today and chases overdue actions.
  7. Updates project health (RAG status, milestone forecasts).
  8. Writes a closing journal entry.

The agent is built with LangGraph. The graph has two nodes:
  - project-manager: the LLM that decides which tools to call.
  - tools:           executes the chosen tool and returns the result.

Run from the project root:
    python -m project_manager_agent.agents.project_manager.agent
"""

from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from project_manager_agent.core.date_utils import REFERENCE_DATE, advance_reference_date
from project_manager_agent.core.db.engine import create_tables
from project_manager_agent.core.services import ProjectService
from .tools import tools
from .prompt import PM_SYSTEM_PROMPT

load_dotenv(override=True)


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------


class State(TypedDict):
    messages: Annotated[list, add_messages]


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------

project_manager_llm = ChatOpenAI(model="gpt-4o-mini")
project_manager_llm_with_tools = project_manager_llm.bind_tools(tools)


# ---------------------------------------------------------------------------
# Graph nodes
# ---------------------------------------------------------------------------


def project_manager_node(state: State) -> dict:
    """Invoke the LLM with the current message history."""
    response = project_manager_llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_graph():
    """Assemble and compile the LangGraph state machine."""
    graph_builder = StateGraph(State)

    graph_builder.add_node("project-manager", project_manager_node)
    graph_builder.add_node("tools", ToolNode(tools=tools))

    graph_builder.add_edge(START, "project-manager")
    graph_builder.add_conditional_edges("project-manager", tools_condition, "tools")
    graph_builder.add_edge("tools", "project-manager")

    graph = graph_builder.compile()

    with open("project_manager_graph.png", "wb") as f:
        f.write(graph.get_graph().draw_mermaid_png())

    return graph


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _already_ran_today() -> bool:
    """Check whether the daily loop has already completed for REFERENCE_DATE.

    Looks for an existing journal entry — journal entries are written
    throughout the daily loop, so their presence indicates a prior run.
    """
    svc = ProjectService()
    try:
        return svc.has_today_journal()
    finally:
        svc.close()


if __name__ == "__main__":
    DATA_DIR = Path(__file__).resolve().parents[4] / "data"
    JOURNAL_DIR = DATA_DIR / "journal"
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    create_tables()

    if _already_ran_today():
        print(
            f"⚠ Idempotency guard: daily loop already ran for {REFERENCE_DATE} "
            f"(journal entry exists). Skipping to prevent duplicate messages "
            f"and journal entries."
        )
    else:
        graph = build_graph()
        graph.invoke(
            {
                "messages": [
                    SystemMessage(PM_SYSTEM_PROMPT),
                    HumanMessage("Please run your daily project management loop."),
                ]
            }
        )

        advance_reference_date()

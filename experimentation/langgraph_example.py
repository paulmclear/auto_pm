import operator
from typing import Literal
from typing_extensions import Annotated, TypedDict

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langchain.messages import AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain.tools import tool
from langgraph.graph import END, START, StateGraph

load_dotenv()


# Step 1: Define tools and model
# Define tools
@tool
def multiply(a: int, b: int) -> int:
    """Multiply `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a * b


@tool
def add(a: int, b: int) -> int:
    """Adds `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a + b


@tool
def divide(a: int, b: int) -> float:
    """Divide `a` and `b`.

    Args:
        a: First int
        b: Second int
    """
    return a / b


# Augment the LLM with tools
MODEL = init_chat_model("gpt-4o-mini", temperature=0)

TOOLS = [add, multiply, divide]
TOOLS_BY_NAME = {tool.name: tool for tool in TOOLS}

MODEL_WITH_TOOLS = MODEL.bind_tools(TOOLS)


# Step 2: Define state
class MessagesState(TypedDict):
    messages: Annotated[list[AnyMessage], operator.add]
    llm_calls: int


# Step 3: Define model node
def llm_call(state: dict):
    """LLM decides whether to call a tool or not"""

    return {
        "messages": [
            MODEL_WITH_TOOLS.invoke(
                [
                    SystemMessage(
                        content="You are a helpful assistant tasked with performing arithmetic on a set of inputs."
                    )
                ]
                + state["messages"]
            )
        ],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# Step 4: Define tool node
def tool_node(state: dict):
    """Performs the tool call"""

    result = []
    for tool_call in state["messages"][-1].tool_calls:
        tool = TOOLS_BY_NAME[tool_call["name"]]
        observation = tool.invoke(tool_call["args"])
        result.append(ToolMessage(content=observation, tool_call_id=tool_call["id"]))
    return {"messages": result}


# Step 5: Define logic to determine whether to end
# Conditional edge function to route to the tool node or end based upon whether the LLM made a tool call
def should_continue(state: MessagesState) -> Literal["tool_node", END]:
    """Decide if we should continue the loop or stop based upon whether the LLM made a tool call"""

    messages = state["messages"]
    last_message = messages[-1]

    # If the LLM makes a tool call, then perform an action
    if last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return END


def build_agent():
    # Step 6: Build agent

    # Build workflow
    agent_builder = StateGraph(MessagesState)

    # Add nodes
    agent_builder.add_node("llm_call", llm_call)
    agent_builder.add_node("tool_node", tool_node)

    # Add edges to connect nodes
    agent_builder.add_edge(START, "llm_call")
    agent_builder.add_conditional_edges("llm_call", should_continue, ["tool_node", END])
    agent_builder.add_edge("tool_node", "llm_call")

    # Compile the agent
    return agent_builder.compile()


if __name__ == "__main__":
    agent = build_agent()

    # Show the agent
    with open("example.png", "wb") as f:
        f.write(agent.get_graph(xray=True).draw_mermaid_png())

    # Invoke
    messages = [HumanMessage(content="Add 3 and 4.")]

    # this will run all at once
    # messages = agent.invoke({"messages": messages})
    # for m in messages["messages"]:
    #     m.pretty_print()

    for chunk, metadata in agent.stream({"messages": messages}, stream_mode="messages"):
        if hasattr(chunk, "content") and chunk.content:
            print(chunk.content, end="", flush=True)
            print("\n", flush=True)

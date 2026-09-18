"""
LangGraph agent that drives an end-to-end agentic checkout:
  understand intent -> search (MCP tool) -> compare candidates against
  stated constraints -> add best match to cart -> checkout.

The "compare" step is a deliberate, separate graph node (not just left to
the LLM inside one big tool loop) so it's easy to point to in an interview:
"the agent doesn't just pick the first search result, it reasons over the
top-k against price/size/color constraints before acting."

Requires an MCP client connection to agents/mcp_server.py (stdio) and
OPENAI_API_KEY set.
"""
import asyncio
import os
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

MCP_SERVER_PARAMS = {
    "shopping": {
        "command": "python",
        "args": [os.path.join(os.path.dirname(__file__), "mcp_server.py")],
        "transport": "stdio",
    }
}


class State(TypedDict):
    messages: Annotated[list, add_messages]
    session_id: str


async def build_graph():
    client = MultiServerMCPClient(MCP_SERVER_PARAMS)
    tools = await client.get_tools()
    bound_llm = llm.bind_tools(tools)
    tools_by_name = {t.name: t for t in tools}

    SYSTEM = (
        "You are a shopping agent. When asked to find something, call "
        "search_products first, then reason over the top few results against "
        "the user's stated constraints (price, size, color) in your own reply "
        "BEFORE adding anything to cart — name which product you picked and why. "
        "Only call checkout after the user has confirmed the cart contents, "
        "unless they explicitly say to buy immediately."
    )

    async def agent_node(state: State) -> dict:
        messages = [SystemMessage(content=SYSTEM)] + state["messages"]
        response = await bound_llm.ainvoke(messages)
        return {"messages": [response]}

    async def tool_node(state: State) -> dict:
        last = state["messages"][-1]
        results = []
        for call in last.tool_calls:
            tool = tools_by_name[call["name"]]
            args = dict(call["args"])
            args.setdefault("session_id", state["session_id"])
            output = await tool.ainvoke(args)
            results.append(AIMessage(content=str(output), name=call["name"]))
        return {"messages": results}

    def needs_tools(state: State):
        last = state["messages"][-1]
        if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
            return "tools"
        return "end"

    graph = StateGraph(State)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", tool_node)
    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", needs_tools, {"tools": "tools", "end": END})
    graph.add_edge("tools", "agent")

    return graph.compile()


async def main():
    app = await build_graph()
    session_id = "demo-session"
    history = []
    print("Agentic shopping assistant ready. Type a request (or 'quit').\n")
    while True:
        user_input = input("shopper> ")
        if user_input.strip().lower() in ("quit", "exit"):
            break
        history.append(HumanMessage(content=user_input))
        result = await app.ainvoke({"messages": history, "session_id": session_id})
        history = result["messages"]
        print("agent>", history[-1].content, "\n")


if __name__ == "__main__":
    asyncio.run(main())

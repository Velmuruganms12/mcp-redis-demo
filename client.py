"""MCP Client - Stateful Support Ticket Demo using LangChain."""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain.agents import create_agent

MCP_SERVER_URL = "http://localhost:8000/mcp"
MCP_API_KEY = os.environ.get("MCP_API_KEY", "")


async def main():
    client = MultiServerMCPClient({
        "opencode-tools": {
            "transport": "http",
            "url": MCP_SERVER_URL,
            "headers": {"X-API-Key": MCP_API_KEY},
        }
    })
    tools = await client.get_tools()
    print(f"Loaded {len(tools)} tools from server:")
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    model = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    agent = create_agent(model, tools)

    questions = [
        "Create a high priority ticket: SSO login fails",
        "List all open tickets",
        "Update TKT-0001 status to in_progress",
        "Add a comment to TKT-0001: Investigating IdP config",
        "Get the full history for TKT-0001",
    ]
    for question in questions:
        print(f"\nUser: {question}")
        result = await agent.ainvoke({"messages": [("user", question)]})
        print(f"Agent: {result['messages'][-1].content}")


if __name__ == "__main__":
    asyncio.run(main())

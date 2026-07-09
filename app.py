"""Streamlit app for testing MCP Support Ticket System via LangChain."""

import asyncio
import os
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

MCP_SERVER_URL = st.sidebar.text_input("MCP Server URL", "http://localhost:8000/mcp")

st.set_page_config(page_title="MCP Ticket Agent", page_icon="🎫", layout="wide")
st.title("🎫 MCP Support Ticket Agent")
st.caption("Natural language ticket management via MCP tools")


async def connect_to_mcp(url):
    client = MultiServerMCPClient({"opencode-tools": {"transport": "http", "url": url}})
    tools = await client.get_tools()
    return client, tools


with st.sidebar:
    st.header("Connection")
    if st.button("Connect to MCP Server", type="primary"):
        with st.spinner("Connecting..."):
            try:
                client, tools = asyncio.run(connect_to_mcp(MCP_SERVER_URL))
                st.session_state["tools"] = tools
                st.session_state["mcp_client"] = client
                st.success(f"Connected! {len(tools)} tools loaded")
            except Exception as e:
                st.error(f"Connection failed: {e}")
    st.divider()
    st.header("Example Commands")
    st.code("""Create a high priority ticket: SSO login fails
List all open tickets
Update TKT-0001 to in_progress""", language=None)
    if st.button("Clear Chat History"):
        st.session_state["messages"] = []
        st.rerun()


async def run_agent(messages, tools):
    model = ChatGroq(model="llama-3.1-8b-instant", temperature=0)
    model_with_tools = model.bind_tools(tools)
    tool_map = {t.name: t for t in tools}
    system = SystemMessage(content="You are a support ticket agent. Use the provided tools directly.")
    msgs = [system] + messages
    response = await model_with_tools.ainvoke(msgs)
    if response.tool_calls:
        tool_call = response.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        if tool_name in tool_map:
            result = await tool_map[tool_name].ainvoke(tool_args)
            return result, tool_name
        return f"Unknown tool: {tool_name}", tool_name
    return response.content, None


if "messages" not in st.session_state:
    st.session_state["messages"] = []

for msg in st.session_state["messages"]:
    if isinstance(msg, HumanMessage):
        with st.chat_message("user"):
            st.write(msg.content)
    elif isinstance(msg, AIMessage):
        with st.chat_message("assistant"):
            st.write(msg.content)

if prompt := st.chat_input("Ask about tickets..."):
    st.session_state["messages"].append(HumanMessage(content=prompt))
    with st.chat_message("user"):
        st.write(prompt)
    if "tools" not in st.session_state:
        with st.chat_message("assistant"):
            st.write("Please connect to MCP server first.")
        st.stop()
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                result, tool_name = asyncio.run(run_agent([HumanMessage(content=prompt)], st.session_state["tools"]))
                st.write(result)
                st.session_state["messages"].append(AIMessage(content=result))
            except Exception as e:
                st.error(f"Error: {e}")

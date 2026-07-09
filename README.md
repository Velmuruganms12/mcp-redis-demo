# MCP Demo - Stateful Support Ticket System (Redis)

Enterprise support ticket system using FastMCP server with **Redis** for persistent state and multiple clients.

## Architecture

```
┌──────────────────┐     ┌──────────────────────┐
│  Streamlit App   │────►│  FastMCP Server       │
│  (app.py)        │     │  (port 8000)         │
└──────────────────┘     │  6 tools             │
                         └──────────┬───────────┘
┌──────────────────┐                │
│  LangChain Agent │────────────────┤
│  (client.py)     │                │
└──────────────────┘                │
                                    │
                         ┌──────────▼───────────┐
                         │  Redis (port 6379)    │
                         │  Persistent state     │
                         │  ticket:* keys        │
                         └──────────────────────┘
```

- **Server**: FastMCP running in Docker, streamable-http transport
- **Redis**: Stores all ticket data as JSON, survives server restarts
- **Streamlit App**: Web UI for testing ticket operations
- **LangChain Agent**: AI agent using Groq LLM for natural language ticket management

## Quick Start

```bash
docker compose up -d --build
pip install -r requirements.txt
streamlit run app.py
```

## Environment Variables

Create a `.env` file:

```
GROQ_API_KEY=gsk_your_groq_api_key_here
MCP_API_KEY=my-secret-api-key-123
```

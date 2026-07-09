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

## Project Structure

```
├── server/                 # MCP Server
│   ├── server.py          # FastMCP server with Redis
│   ├── Dockerfile         # Docker image
│   ├── docker-compose.yml # Runs server + Redis
│   └── server-requirements.txt
├── app.py                  # Streamlit web UI
├── client.py              # LangChain agent client
├── requirements.txt       # Client dependencies
└── README.md
```

## Quick Start

### Start Server

```bash
cd server
docker compose up -d --build
cd ..
```

### Setup Client

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

### Run Streamlit App

```bash
streamlit run app.py
```

## Environment Variables

Create a `.env` file:

```
GROQ_API_KEY=gsk_your_groq_api_key_here
MCP_API_KEY=my-secret-api-key-123
```

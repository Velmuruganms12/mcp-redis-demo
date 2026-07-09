"""MCP Server - Stateful Support Ticket System using FastMCP + Redis."""

import json
import os
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Coroutine
from mcp.server.fastmcp import FastMCP, Context
import redis

logging.getLogger("mcp").setLevel(logging.WARNING)

MCP_API_KEY = os.environ.get("MCP_API_KEY", "")
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))

mcp = FastMCP("opencode-tools", host="0.0.0.0", port=8000)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

TICKET_PREFIX = "ticket:"
COUNTER_KEY = "ticket_counter"
TICKETS_INDEX = "tickets:index"

VALID_STATUSES = ["open", "in_progress", "resolved", "closed"]
VALID_TRANSITIONS = {
    "open": ["in_progress", "closed"],
    "in_progress": ["resolved", "open"],
    "resolved": ["closed", "in_progress"],
    "closed": [],
}


async def _get_api_key(ctx: Context) -> str:
    request = ctx.request_context.request
    return request.headers.get("x-api-key", "")


def _verify_key(key: str):
    if not MCP_API_KEY or key != MCP_API_KEY:
        raise ValueError("Unauthorized: invalid or missing X-API-Key header")


def require_api_key(fn: Callable[..., Coroutine[Any, Any, str]]) -> Callable[..., Coroutine[Any, Any, str]]:
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        ctx = kwargs.get("ctx")
        if ctx is not None:
            key = await _get_api_key(ctx)
            _verify_key(key)
        return await fn(*args, **kwargs)
    return wrapper


def next_ticket_id():
    ticket_num = r.incr(COUNTER_KEY)
    return f"TKT-{ticket_num:04d}"


def now():
    return datetime.now(timezone.utc).isoformat()


def save_ticket(ticket_id: str, ticket: dict):
    r.set(f"{TICKET_PREFIX}{ticket_id}", json.dumps(ticket))
    r.sadd(TICKETS_INDEX, ticket_id)


def get_ticket_from_redis(ticket_id: str) -> dict | None:
    data = r.get(f"{TICKET_PREFIX}{ticket_id}")
    return json.loads(data) if data else None


def get_all_ticket_ids() -> list:
    return list(r.smembers(TICKETS_INDEX))


@mcp.tool()
@require_api_key
async def create_ticket(title: str, description: str, priority: str, requester: str, ctx: Context) -> str:
    """Create a new support ticket. Priority must be: low, medium, high, critical."""
    if priority not in ["low", "medium", "high", "critical"]:
        return json.dumps({"error": "Invalid priority. Must be one of: low, medium, high, critical"})
    ticket_id = next_ticket_id()
    ts = now()
    ticket = {
        "id": ticket_id, "title": title, "description": description,
        "priority": priority, "status": "open", "requester": requester,
        "assignee": None, "created_at": ts, "updated_at": ts,
        "comments": [], "history": [{"action": "created", "by": requester, "time": ts}],
    }
    save_ticket(ticket_id, ticket)
    return json.dumps({"message": f"Ticket {ticket_id} created", "ticket": ticket})


@mcp.tool()
@require_api_key
async def update_ticket(ticket_id: str, status: str = None, assignee: str = None, priority: str = None, ctx: Context = None) -> str:
    """Update a ticket's status, assignee, or priority."""
    ticket = get_ticket_from_redis(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})
    ts = now()
    changes = []
    if status:
        current = ticket["status"]
        if status not in VALID_STATUSES:
            return json.dumps({"error": f"Invalid status"})
        if status not in VALID_TRANSITIONS.get(current, []):
            return json.dumps({"error": f"Cannot transition from '{current}' to '{status}'"})
        ticket["status"] = status
        changes.append(f"status: {current} -> {status}")
    if assignee:
        ticket["assignee"] = assignee
        changes.append(f"assignee -> {assignee}")
    if priority:
        if priority not in ["low", "medium", "high", "critical"]:
            return json.dumps({"error": "Invalid priority"})
        ticket["priority"] = priority
        changes.append(f"priority -> {priority}")
    if changes:
        ticket["updated_at"] = ts
        ticket["history"].append({"action": f"updated: {', '.join(changes)}", "by": "system", "time": ts})
        save_ticket(ticket_id, ticket)
    return json.dumps({"message": f"Ticket {ticket_id} updated", "ticket": ticket})


@mcp.tool()
@require_api_key
async def get_ticket(ticket_id: str, ctx: Context) -> str:
    """Get full details of a support ticket by ID."""
    ticket = get_ticket_from_redis(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})
    return json.dumps({"ticket": ticket})


@mcp.tool()
@require_api_key
async def list_tickets(status_filter: str = None, ctx: Context = None) -> str:
    """List all tickets. Optionally filter by status."""
    ticket_ids = get_all_ticket_ids()
    results = []
    for tid in ticket_ids:
        t = get_ticket_from_redis(tid)
        if t:
            if status_filter and t["status"] != status_filter:
                continue
            results.append(t)
    return json.dumps({"count": len(results), "tickets": results})


@mcp.tool()
@require_api_key
async def add_comment(ticket_id: str, comment: str, author: str, ctx: Context) -> str:
    """Add a comment to an existing ticket."""
    ticket = get_ticket_from_redis(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})
    ts = now()
    entry = {"author": author, "text": comment, "time": ts}
    ticket["comments"].append(entry)
    ticket["updated_at"] = ts
    ticket["history"].append({"action": f"comment added by {author}", "by": author, "time": ts})
    save_ticket(ticket_id, ticket)
    return json.dumps({"message": "Comment added", "comment": entry})


@mcp.tool()
@require_api_key
async def get_ticket_history(ticket_id: str, ctx: Context) -> str:
    """Get the full audit trail for a ticket."""
    ticket = get_ticket_from_redis(ticket_id)
    if not ticket:
        return json.dumps({"error": f"Ticket {ticket_id} not found"})
    return json.dumps({"ticket_id": ticket_id, "history": ticket["history"], "comments": ticket["comments"]})


if __name__ == "__main__":
    mcp.run(transport="streamable-http")

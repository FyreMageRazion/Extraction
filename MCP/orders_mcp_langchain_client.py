#!/usr/bin/env python3
"""
orders_mcp_client.py

Async client that:
 - tries to use MultiServerMCPClient (langchain_mcp_adapters) if available
 - otherwise falls back to direct httpx-based calls to the /mcp endpoint
 - demonstrates discovery, list_recent_orders, get_order_status (SSE streaming), cancel_order

Usage:
    pip install httpx sseclient-py python-dotenv
    # optional if you want langchain adapter:
    pip install langchain-mcp-adapters langchain

    python orders_mcp_client.py --url http://127.0.0.1:8080/mcp
"""

import os
import asyncio
import json
import argparse
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
if not env_path:
    root_env = Path(__file__).resolve().parent / ".env"
    venv_env = Path(__file__).resolve().parent / ".venv" / ".env"
    if root_env.exists():
        env_path = str(root_env)
    elif venv_env.exists():
        env_path = str(venv_env)

if env_path:
    load_dotenv(env_path)

import asyncio

# optional imports
try:
    from langchain_mcp_adapters.client import MultiServerMCPClient
    LC_MCP_AVAILABLE = True
except Exception:
    LC_MCP_AVAILABLE = False

import httpx

# Simple SSE parser for lines of the form:
# event: <name>\n
# data: <json>\n\n
def parse_sse_bytes(chunk: bytes):
    text = chunk.decode(errors="replace")
    # split into events separated by double-newline
    for evt_text in text.split("\n\n"):
        if not evt_text.strip():
            continue
        evt = {}
        for line in evt_text.splitlines():
            if line.startswith("event:"):
                evt["event"] = line.partition(":")[2].strip()
            elif line.startswith("data:"):
                data = line.partition(":")[2].strip()
                # try parse json
                try:
                    evt["data"] = json.loads(data)
                except Exception:
                    evt["data"] = data
        yield evt

async def sse_stream_get_order_status(url: str, order_id: str):
    """
    Call /mcp with method=call_tool for get_order_status and stream SSE events.
    """
    async with httpx.AsyncClient(timeout=None) as client:
        payload = {"method": "call_tool", "params": {"tool": "get_order_status", "input": {"order_id": order_id}}}
        headers = {"Content-Type": "application/json"}
        # use stream to keep connection and read bytes progressively
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            print("SSE status code:", resp.status_code)
            if resp.status_code != 200:
                text = await resp.aread()
                print("SSE error body:", text.decode(errors="replace"))
                return
            async for chunk in resp.aiter_bytes():
                if not chunk:
                    continue
                for evt in parse_sse_bytes(chunk):
                    print("SSE EVENT:", evt)

async def http_list_recent_orders(url: str, customer_id: str, limit: int = 3):
    async with httpx.AsyncClient() as client:
        payload = {"method": "call_tool", "params": {"tool": "list_recent_orders", "input": {"customer_id": customer_id, "limit": limit}}}
        r = await client.post(url, json=payload)
        print("list_recent_orders status:", r.status_code)
        print("body:", r.text)
        if r.status_code == 200:
            try:
                print("parsed:", r.json())
            except Exception:
                pass

async def http_cancel_order(url: str, order_id: str, reason: str):
    async with httpx.AsyncClient() as client:
        payload = {"method": "call_tool", "params": {"tool": "cancel_order", "input": {"order_id": order_id, "reason": reason}}}
        r = await client.post(url, json=payload)
        print("cancel_order status:", r.status_code)
        print("body:", r.text)
        if r.status_code == 200:
            try:
                print("parsed:", r.json())
            except Exception:
                pass

async def try_langchain_mcp(url: str):
    """
    Try to use the MultiServerMCPClient to discover tools and create an agent.
    This is optional: will run only if LC adapter is installed.
    """
    if not LC_MCP_AVAILABLE:
        print("langchain_mcp_adapters not installed; skipping MultiServerMCPClient path.")
        return None

    servers = {
        "orders_http": {"url": url, "transport": "streamable_http"}
    }
    client = MultiServerMCPClient(servers)
    try:
        tools = await client.get_tools()
        print("Discovered tools count via MultiServerMCPClient:", len(tools))
        # print tool names (best-effort)
        for t in tools:
            try:
                print("-", getattr(t, "name", getattr(t, "tool_name", str(t))))
            except Exception:
                print("-", t)
        await client.close()
        return tools
    except Exception as exc:
        print("MultiServerMCPClient path failed with exception:", exc)
        try:
            await client.close()
        except Exception:
            pass
        return None

async def main(url: str):
    print("Client starting; MCP URL:", url)
    # 1) Try langchain adapter path (optional)
    tools = await try_langchain_mcp(url)

    from langchain.agents import create_agent
    model_name = "gpt-4o"
    agent = create_agent(
        model=model_name,
        tools=tools,
        system_prompt="You are an order management assistant with access to these tools:\n\n"
        "1. list_recent_orders - List orders for a customer (requires customer_id like 'cust_1')\n"
        "2. get_order_status - Get detailed status of an order (requires order_id like 'cust_1-ord-1')\n"
        "3. cancel_order - Cancel an order (requires order_id and reason)\n\n"
        "Important guidelines:\n"
        "- Customer IDs must be in format 'cust_1', 'cust_2', etc.\n"
        "- Order IDs must be in format '{customer_id}-ord-{number}' like 'cust_1-ord-1'\n"
        "- Always use exact ID formats - they are case sensitive.\n"
        "- If user asks about orders without an ID, ask for their customer ID.\n"
        "- For cancellations, always confirm and require a reason.\n\n"
        "Example interactions:\n"
        "User: Show me my orders\n"
        "Assistant: I'll help you check your orders. Could you please provide your customer ID? "
        "It should be in the format 'cust_1' or similar.\n\n"
        "User: Show orders for cust_1\n"
        "Assistant: I'll use the list_recent_orders tool to check the orders for customer cust_1.\n\n"
        "Remember to always process the tool responses to provide clear, user-friendly summaries."
    )

    # Test 1
    response = agent.invoke(
        {"messages": [{"role": "user", "content": "List recent orders of cust_1"}]}
    )
    print(response)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080/mcp", help="MCP HTTP URL")
    args = parser.parse_args()
    asyncio.run(main(args.url))

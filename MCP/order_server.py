#!/usr/bin/env python3
"""
order_server.py

MCP server exposing three tools:
 - get_order_status(order_id)  -> streams SSE events (ack, partial, result, done)
 - list_recent_orders(customer_id, limit) -> JSON response
 - cancel_order(order_id, reason) -> JSON response and DB mutation (audit)

Usage:
    pip install mcp-core
    python order_server.py --db orders.db --host 127.0.0.1 --port 8080

If orders.db doesn't exist, you can create it with the earlier script or
the server will still start but tools will return order_not_found for unknown IDs.
"""
import argparse
import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional, AsyncGenerator

from mcp.server.fastmcp import FastMCP

# Initialize MCP server with application name
mcp = FastMCP("Orders")

# Global connection for db access
db_conn = None

def init_db(db_path: str):
    """Initialize the database connection"""
    global db_conn
    db_conn = get_conn(db_path)
    ensure_audit_table(db_conn)
    return db_conn

# ----- MCP Tool Implementations -----

@mcp.tool()
async def get_order_status(order_id: str):
    """Get detailed status and event history for an order."""
    # Get the order and events
    order = fetch_order(db_conn, order_id)
    if not order:
        raise ValueError(f"Order not found: {order_id}")
    
    events = fetch_order_events(db_conn, order_id)
    
    return {
        "order": order,
        "events": events
    }

@mcp.tool()
async def list_recent_orders(customer_id: str, limit: int = 5):
    """
    List recent orders for a customer.
    Args:
        customer_id: ID of the customer to list orders for (e.g. cust_1)
        limit: Maximum number of orders to return (default: 5)
    Returns:
        Dictionary containing list of recent orders
    """
    try:
        orders = list_recent_orders_db(db_conn, customer_id, limit)
        return {"orders": orders}
    except Exception as e:
        raise ValueError(f"Failed to fetch orders: {str(e)}")

@mcp.tool()
async def cancel_order(order_id: str, reason: str):
    """
    Cancel an order (sets status=cancelled and logs an audit event).
    Args:
        order_id: ID of the order to cancel (e.g. cust_1-ord-1)
        reason: Reason for cancellation (required)
    Returns:
        Dictionary containing updated order status and cancellation timestamp
    """
    if not reason or not reason.strip():
        raise ValueError("A valid reason is required to cancel an order")
        
    try:
        result = cancel_order_db(db_conn, order_id, reason)
        if not result:
            raise ValueError(f"Order not found: {order_id}")
        return result
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Failed to cancel order: {str(e)}")



# ----- DB helpers -----
def get_conn(db_path: str):
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_audit_table(conn):
    cur = conn.cursor()
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS audit_log (
        id TEXT PRIMARY KEY,
        ts TEXT NOT NULL,
        action TEXT NOT NULL,
        details TEXT
    )
    """
    )
    conn.commit()


def fetch_order(conn, order_id: str) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,))
    row = cur.fetchone()
    return dict(row) if row else None


def fetch_order_events(conn, order_id: str) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        "SELECT event_id, order_id, ts, event_type, note FROM order_events WHERE order_id = ? ORDER BY ts ASC",
        (order_id,),
    )
    return [dict(r) for r in cur.fetchall()]


def list_recent_orders_db(conn, customer_id: str, limit: int = 5) -> List[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute(
        """
        SELECT order_id, customer_id, created_at, status, eta, total_amount
        FROM orders
        WHERE customer_id = ?
        ORDER BY created_at DESC
        LIMIT ?
    """,
        (customer_id, limit),
    )
    return [dict(r) for r in cur.fetchall()]


def cancel_order_db(conn, order_id: str, reason: str, actor: str = "mcp_server") -> Dict[str, Any]:
    cur = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    cur.execute("SELECT status FROM orders WHERE order_id = ?", (order_id,))
    row = cur.fetchone()
    if not row:
        raise ValueError("order_not_found")
    old_status = row["status"]
    if old_status == "CANCELLED":
        return {"order_id": order_id, "status": "CANCELLED", "cancelled_at": now, "note": "already_cancelled"}
    if old_status == "DELIVERED":
        return {"order_id": order_id, "status": old_status, "cancelled_at": None, "note": "cannot_cancel_delivered"}
    cur.execute("UPDATE orders SET status = ? WHERE order_id = ?", ("CANCELLED", order_id))
    event_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO order_events (event_id, order_id, ts, event_type, note) VALUES (?, ?, ?, ?, ?)",
        (event_id, order_id, now, "CANCELLED", f"Cancelled via MCP tool. Reason: {reason}"),
    )
    ensure_audit_table(conn)
    audit_id = str(uuid.uuid4())
    cur.execute(
        "INSERT INTO audit_log (id, ts, action, details) VALUES (?, ?, ?, ?)",
        (audit_id, now, "cancel_order", json.dumps({"order_id": order_id, "reason": reason, "actor": actor})),
    )
    conn.commit()
    return {"order_id": order_id, "status": "CANCELLED", "cancelled_at": now}





# ----- CLI -----
def main():
    parser = argparse.ArgumentParser(description="MCP order management tools server")
    parser.add_argument("--db", type=str, default="orders.db", help="Path to SQLite orders database")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on")
    args = parser.parse_args()

    # Connect to orders DB on startup
    try:
        db_conn = init_db(args.db)
        print(f"Connected to orders database: {args.db}")
    except Exception as e:
        print(f"Warning: Failed to connect to orders database: {e}")
        print("Server will still start but all tools will return order_not_found")
        db_conn = None

    # Run the MCP server with streamable HTTP transport
    mcp.run(
        transport="streamable-http",
        host=args.host,
        port=args.port
    )

if __name__ == "__main__":
    main()

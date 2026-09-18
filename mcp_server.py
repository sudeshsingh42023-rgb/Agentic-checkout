"""
MCP server exposing shopping tools: search_products, get_product_details,
add_to_cart, apply_coupon, checkout. This is the same shape as the shopping
MCP servers already emerging in the agentic-commerce ecosystem (e.g. UCP
Shopping) — the point is that ANY MCP-compatible agent (Claude, ChatGPT,
etc), not just the one in this repo, could drive a checkout through these
tools without custom integration work.

Run:
    python mcp_server.py

Then point an MCP client (Claude Desktop config, or the LangGraph agent in
agent.py) at this server over stdio.
"""
import sys, os
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "app"))

import requests
from mcp.server.fastmcp import FastMCP
from vector_search import search as semantic_search

STORE_API = "http://localhost:8001"

mcp = FastMCP("urumi-shopping-agent")


@mcp.tool()
def search_products(query: str, max_price: float | None = None, top_k: int = 5) -> str:
    """Semantically search the product catalog. Use natural language like
    'waterproof running jacket' — matches by meaning, not just keywords.
    Optionally cap results by max_price."""
    results = semantic_search(query, top_k=top_k, max_price=max_price)
    if not results:
        return "No matching products found."
    return "\n".join(
        f"[{p['id']}] {p['name']} — {p['description']} — ₹{p['price']} — "
        f"size {p['size']} — stock {p['stock']} (relevance {p['relevance']})"
        for p in results
    )


@mcp.tool()
def get_product_details(product_id: int) -> str:
    """Get full details for a single product by id."""
    r = requests.get(f"{STORE_API}/products/{product_id}")
    if r.status_code == 404:
        return f"Product {product_id} not found."
    p = r.json()
    return (f"{p['name']} — {p['description']} — ₹{p['price']} — size {p['size']}, "
            f"color {p['color']}, stock {p['stock']}")


@mcp.tool()
def add_to_cart(session_id: str, product_id: int, quantity: int = 1) -> str:
    """Add a product to the shopper's cart. session_id identifies this
    shopping session — reuse the same session_id across a conversation."""
    r = requests.post(f"{STORE_API}/cart/add",
                       json={"session_id": session_id, "product_id": product_id, "quantity": quantity})
    if r.status_code == 404:
        return f"Product {product_id} not found."
    return f"Added to cart. Current cart: {r.json()['cart']}"


@mcp.tool()
def view_cart(session_id: str) -> str:
    """View the current cart contents and subtotal for a session."""
    r = requests.get(f"{STORE_API}/cart/{session_id}")
    data = r.json()
    if not data["items"]:
        return "Cart is empty."
    lines = "\n".join(f"{i['quantity']}x {i['name']} — ₹{i['line_total']}" for i in data["items"])
    return f"{lines}\nSubtotal: ₹{data['subtotal']}"


@mcp.tool()
def apply_coupon(session_id: str, code: str) -> str:
    """Apply a discount coupon code to the session's cart."""
    r = requests.post(f"{STORE_API}/cart/apply-coupon", json={"session_id": session_id, "code": code})
    if r.status_code == 400:
        return "Invalid or expired coupon code."
    data = r.json()
    return f"Applied {data['code']}: {data['discount_pct']}% off."


@mcp.tool()
def checkout(session_id: str, coupon_code: str | None = None) -> str:
    """Complete checkout for the session's cart. Always marks the order as
    agent-initiated so the merchant's attribution dashboard can distinguish
    it from a human-driven purchase."""
    params = {"coupon": coupon_code} if coupon_code else {}
    r = requests.post(f"{STORE_API}/checkout", params=params,
                       json={"session_id": session_id, "actor": "agent", "agent_name": "urumi-shopping-agent"})
    if r.status_code == 400:
        return "Checkout failed: cart is empty."
    order = r.json()
    flag_note = " NOTE: this order was flagged for manual fraud review." if order["flagged_for_review"] else ""
    return f"Order {order['order_id']} placed. Total: ₹{order['total']}.{flag_note}"


if __name__ == "__main__":
    mcp.run(transport="stdio")

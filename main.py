"""
Mock storefront backend. Carts are session-based (in-memory, keyed by a
session_id the caller supplies) so both a human browser flow and an agent
flow can use the exact same endpoints — the only difference is who's
calling, which is exactly the distinction agentic-commerce platforms need
to detect and report on.
"""
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Mock Storefront API")

with open("catalog.json") as f:
    CATALOG = {p["id"]: p for p in json.load(f)}

CARTS: dict[str, list] = {}          # session_id -> [{product_id, qty}]
ORDERS: list = []                    # completed orders, each tagged with actor type
COUPONS = {"WELCOME10": 0.10, "AGENT5": 0.05}


class CartItem(BaseModel):
    session_id: str
    product_id: int
    quantity: int = 1


class CouponRequest(BaseModel):
    session_id: str
    code: str


class CheckoutRequest(BaseModel):
    session_id: str
    actor: str = "human"   # "human" or "agent" — this is the attribution signal
    agent_name: Optional[str] = None


@app.get("/products/{product_id}")
def get_product(product_id: int):
    p = CATALOG.get(product_id)
    if not p:
        raise HTTPException(404, "Product not found")
    return p


@app.post("/cart/add")
def add_to_cart(item: CartItem):
    if item.product_id not in CATALOG:
        raise HTTPException(404, "Product not found")
    cart = CARTS.setdefault(item.session_id, [])
    for line in cart:
        if line["product_id"] == item.product_id:
            line["quantity"] += item.quantity
            return {"cart": cart}
    cart.append({"product_id": item.product_id, "quantity": item.quantity})
    return {"cart": cart}


@app.get("/cart/{session_id}")
def view_cart(session_id: str):
    cart = CARTS.get(session_id, [])
    enriched = []
    total = 0.0
    for line in cart:
        p = CATALOG[line["product_id"]]
        line_total = p["price"] * line["quantity"]
        total += line_total
        enriched.append({**p, "quantity": line["quantity"], "line_total": round(line_total, 2)})
    return {"items": enriched, "subtotal": round(total, 2)}


@app.post("/cart/apply-coupon")
def apply_coupon(req: CouponRequest):
    discount = COUPONS.get(req.code.upper())
    if discount is None:
        raise HTTPException(400, "Invalid or expired coupon code")
    return {"code": req.code.upper(), "discount_pct": discount * 100}


@app.post("/checkout")
def checkout(req: CheckoutRequest, coupon: Optional[str] = None):
    cart = CARTS.get(req.session_id)
    if not cart:
        raise HTTPException(400, "Cart is empty")

    subtotal = sum(CATALOG[line["product_id"]]["price"] * line["quantity"] for line in cart)
    discount = COUPONS.get((coupon or "").upper(), 0.0)
    total = round(subtotal * (1 - discount), 2)

    # Simple fraud/anomaly guardrail: flag unusually large agent-initiated orders
    flagged = req.actor == "agent" and total > 20000

    order = {
        "order_id": str(uuid.uuid4())[:8],
        "actor": req.actor,
        "agent_name": req.agent_name,
        "items": cart,
        "subtotal": round(subtotal, 2),
        "coupon": (coupon or "").upper() if discount else None,
        "total": total,
        "flagged_for_review": flagged,
        "created_at": datetime.utcnow().isoformat(),
    }
    ORDERS.append(order)
    CARTS[req.session_id] = []
    return order


@app.get("/orders")
def list_orders():
    return ORDERS


@app.get("/orders/attribution")
def order_attribution():
    """Merchant-facing view: how much revenue is coming from AI agents vs
    humans, and how many agent orders got flagged — the dashboard reads this."""
    human_orders = [o for o in ORDERS if o["actor"] == "human"]
    agent_orders = [o for o in ORDERS if o["actor"] == "agent"]
    return {
        "human_order_count": len(human_orders),
        "human_revenue": round(sum(o["total"] for o in human_orders), 2),
        "agent_order_count": len(agent_orders),
        "agent_revenue": round(sum(o["total"] for o in agent_orders), 2),
        "agent_flagged_count": sum(1 for o in agent_orders if o["flagged_for_review"]),
        "orders": ORDERS,
    }


@app.get("/health")
def health():
    return {"status": "ok", "catalog_size": len(CATALOG)}

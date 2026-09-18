"""
Merchant-facing dashboard: agent vs human order attribution + fraud flags.
Run: streamlit run dashboard/dashboard.py
(requires app/main.py running on :8001)
"""
import requests
import streamlit as st
import pandas as pd

STORE_API = "http://localhost:8001"

st.set_page_config(page_title="Agentic Commerce Dashboard", page_icon="📊", layout="wide")
st.title("📊 Agentic Commerce Attribution Dashboard")
st.caption("Distinguishing AI-agent checkouts from human checkouts, with fraud-review flags")

try:
    data = requests.get(f"{STORE_API}/orders/attribution").json()
except requests.exceptions.ConnectionError:
    st.error("Storefront API not running. Start it with: uvicorn main:app --port 8001 (from app/)")
    st.stop()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Human orders", data["human_order_count"])
col2.metric("Human revenue", f"₹{data['human_revenue']:,.2f}")
col3.metric("Agent orders", data["agent_order_count"])
col4.metric("Agent revenue", f"₹{data['agent_revenue']:,.2f}")

if data["agent_flagged_count"]:
    st.warning(f"⚠️ {data['agent_flagged_count']} agent-initiated order(s) flagged for manual fraud review "
               f"(unusually large order value).")

st.subheader("All orders")
if data["orders"]:
    df = pd.DataFrame(data["orders"])
    df = df[["order_id", "actor", "agent_name", "subtotal", "coupon", "total", "flagged_for_review", "created_at"]]
    st.dataframe(df, use_container_width=True)
else:
    st.info("No orders yet — place one via the shopping agent (agents/agent.py) or the storefront API directly.")

st.subheader("Revenue split")
if data["human_revenue"] or data["agent_revenue"]:
    chart_df = pd.DataFrame({
        "channel": ["Human", "Agent"],
        "revenue": [data["human_revenue"], data["agent_revenue"]],
    })
    st.bar_chart(chart_df.set_index("channel"))

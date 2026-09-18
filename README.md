# Agentic Checkout — Autonomous Shopping Agent (MCP-based)

An AI agent that takes a shopper's natural-language intent, semantically
searches a 500-SKU catalog, reasons over the top candidates against stated
constraints, adds the best match to cart, and completes checkout — end to
end, via MCP tool-use. Includes a merchant-facing dashboard that separates
AI-agent revenue from human revenue and flags suspicious agent orders,
which is exactly the attribution/fraud problem merchants are dealing with
as agentic referrals scale in 2026.

## Architecture

```
 shopper intent ("waterproof jacket under 3000, size M")
        |
        v
 ┌───────────────┐        MCP tools (stdio)          ┌──────────────────┐
 │ LangGraph      │ ───────────────────────────────► │  MCP server       │
 │ shopping agent │ ◄─────────────────────────────── │ (mcp_server.py)   │
 └───────────────┘                                    └──────────────────┘
        |                                                       |
        | reasons over top-k results                            v
        | against price/size/color                    semantic search (FAISS +
        | before adding to cart                        sentence-transformers)
        v                                                       |
   checkout (tagged actor="agent")                              v
        |                                              mock storefront API
        v                                              (FastAPI, cart/checkout)
 merchant dashboard (Streamlit)
 — human vs agent revenue split
 — flags large agent orders for fraud review
```

- **Catalog** (`app/seed_catalog.py`) — 500 generated SKUs across 5 categories
  with varied natural-language descriptions, so semantic search has to do
  real work (queries won't just keyword-match).
- **Semantic search** (`app/vector_search.py`) — local sentence-transformers
  embeddings + FAISS, no API key required for search itself.
- **MCP server** (`agents/mcp_server.py`) — exposes `search_products`,
  `get_product_details`, `add_to_cart`, `view_cart`, `apply_coupon`,
  `checkout` as MCP tools, the same shape as real shopping-MCP servers
  (e.g. UCP Shopping) already emerging in the agentic-commerce ecosystem.
  Any MCP-compatible client could drive a purchase through these tools,
  not just the LangGraph agent in this repo.
- **LangGraph agent** (`agents/agent.py`) — deliberately separates the
  "compare candidates against constraints" reasoning from the tool-call
  loop, so it doesn't just buy the first search hit.
- **Storefront API** (`app/main.py`) — session-based cart + checkout;
  every order is tagged `actor: human` or `actor: agent`, and agent orders
  over ₹20,000 are flagged for manual review as a basic fraud guardrail.
- **Dashboard** (`dashboard/dashboard.py`) — merchant view of agent vs
  human revenue and flagged orders.

## Setup

```bash
pip install -r requirements.txt

cd app
python seed_catalog.py        # generates catalog.json (500 SKUs)
python vector_search.py --build   # builds the FAISS index (downloads a small
                                   # embedding model on first run — needs internet)
uvicorn main:app --port 8001 --reload   # storefront API

# separate terminal
export OPENAI_API_KEY=sk-...
cd agents && python agent.py    # CLI shopping agent (spawns the MCP server itself)

# separate terminal, once you've placed an order or two
streamlit run dashboard/dashboard.py
```

Quick sanity check without an LLM at all:
```bash
python app/vector_search.py --query "waterproof running jacket" --max-price 3000
```

## Example prompts to try with the agent

- "Find me a waterproof running jacket under ₹3000, size M"
- "I need a laptop backpack, nothing too flashy" (tests semantic match beyond keywords)
- "Add the second one to my cart and apply code AGENT5"
- "Checkout"

## Why this design

This mirrors where e-commerce is actually heading in 2026: ChatGPT
completing purchases in-conversation, Google's Universal Cart, Stripe's
Agentic Commerce Protocol, and MCP shopping servers letting any AI
assistant transact on a shopper's behalf. Two things merchants (like
Urumi's customers) specifically need from this shift are (1) knowing how
much of their traffic/revenue is agent-driven vs human, and (2) catching
the new fraud patterns agentic traffic introduces — both of which this
project builds explicitly, not just the checkout flow itself.

## Honest limitations / next steps

- The fraud check is a single price threshold — a real version would look
  at velocity (orders per session per minute), address/payment mismatches,
  etc.
- No real payment integration — checkout is simulated.
- The MCP server currently only serves this one LangGraph agent over
  stdio; exposing it over HTTP/SSE would let it serve any MCP client
  (Claude Desktop, ChatGPT, etc.), which is worth doing if you want to
  demo real multi-client interoperability.

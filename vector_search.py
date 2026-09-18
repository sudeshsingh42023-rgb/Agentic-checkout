"""
Semantic search over the product catalog so "waterproof running jacket
under 3000" matches products whose description doesn't contain those exact
words. Uses sentence-transformers (local, no API key needed) + FAISS.

Build the index once:
    python vector_search.py --build

Then import `search(query, top_k)` from agent/MCP code.
"""
import json
import argparse
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = "catalog.index"
IDS_PATH = "catalog_ids.json"

_model = None
_index = None
_ids = None
_catalog_by_id = None


def _load_catalog():
    global _catalog_by_id
    if _catalog_by_id is None:
        with open("catalog.json") as f:
            items = json.load(f)
        _catalog_by_id = {p["id"]: p for p in items}
    return _catalog_by_id


def build_index():
    catalog = _load_catalog()
    model = SentenceTransformer(MODEL_NAME)
    texts, ids = [], []
    for p in catalog.values():
        texts.append(f"{p['name']}. {p['description']}. Category: {p['category']}. "
                      f"Color: {p['color']}. Size: {p['size']}. Price: {p['price']}")
        ids.append(p["id"])

    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(np.array(embeddings, dtype="float32"))

    faiss.write_index(index, INDEX_PATH)
    with open(IDS_PATH, "w") as f:
        json.dump(ids, f)
    print(f"Built FAISS index over {len(ids)} products.")


def _load():
    global _model, _index, _ids
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    if _index is None:
        _index = faiss.read_index(INDEX_PATH)
        with open(IDS_PATH) as f:
            _ids = json.load(f)


def search(query: str, top_k: int = 8, max_price: float | None = None):
    _load()
    catalog = _load_catalog()
    q_emb = _model.encode([query], normalize_embeddings=True)
    scores, indices = _index.search(np.array(q_emb, dtype="float32"), top_k * 3)

    results = []
    for idx, score in zip(indices[0], scores[0]):
        product_id = _ids[idx]
        product = catalog[product_id]
        if max_price is not None and product["price"] > max_price:
            continue
        results.append({**product, "relevance": round(float(score), 3)})
        if len(results) >= top_k:
            break
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--query", type=str)
    parser.add_argument("--max-price", type=float, default=None)
    args = parser.parse_args()

    if args.build:
        build_index()
    elif args.query:
        for r in search(args.query, max_price=args.max_price):
            print(f"[{r['relevance']}] {r['name']} — {r['description']} — ₹{r['price']} (size {r['size']})")

"""Read-only MCP tools for a controlled enterprise workflow."""
import os
import re
from collections import Counter
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

mcp = FastMCP("AgentBridge")
ROOT = Path(__file__).parent
POLICIES = {
    "billing-refund": "Refund requests must be submitted within 30 days of purchase. Finance approves exceptions.",
    "data-export": "Account owners can export records via Settings. Export files expire after 24 hours.",
    "incident-escalation": "Page the on-call engineer for critical outages. Notify incident command within 15 minutes.",
    "access-review": "Managers review privileged access quarterly. Revoke access when the employee leaves.",
    "backup-restore": "Backup restoration requires an approved recovery ticket. Test restores monthly.",
    "purchase-approval": "Purchases above 5000 require approval from the procurement manager.",
}


class PolicyHit(BaseModel):
    source: str
    text: str
    score: float


def tokens(value):
    return re.findall(r"[a-z0-9]+", value.lower())


@mcp.tool()
def search_policy(query: str = Field(min_length=2, max_length=300),
                  limit: int = Field(default=3, ge=1, le=5)) -> list[PolicyHit]:
    """Retrieve enterprise policy passages with source IDs."""
    q = Counter(tokens(query))
    hits = []
    for key, passage in POLICIES.items():
        words = set(tokens(key + " " + passage))
        score = sum(count for term, count in q.items() if term in words and len(term) > 2)
        if score:
            hits.append(PolicyHit(source=key, text=passage, score=score))
    return sorted(hits, key=lambda hit: (-hit.score, hit.source))[:limit]


class Order(BaseModel):
    order_id: str
    status: str


@mcp.tool()
def lookup_order(order_id: str = Field(pattern=r"^ORD-[0-9]{4}$")) -> Order | None:
    """Fetch a single order status using a parameterized database query."""
    engine = create_engine(os.getenv("DATABASE_URL", f"sqlite:///{(ROOT / 'orders.db').as_posix()}"))
    try:
        with engine.connect() as connection:
            row = connection.execute(text("SELECT order_id, status FROM orders WHERE order_id = :id"),
                                     {"id": order_id}).mappings().one_or_none()
        return Order.model_validate(dict(row)) if row else None
    finally:
        engine.dispose()


@mcp.tool()
def service_status(service: str = Field(pattern=r"^(billing|exports)$")) -> dict[str, str]:
    """Fetch validated service health from the configured internal REST fixture."""
    import httpx

    base = os.getenv("STATUS_API", "http://127.0.0.1:8020")
    with httpx.Client(base_url=base, timeout=2, follow_redirects=False, trust_env=False) as client:
        response = client.get("/status/" + service)
        response.raise_for_status()
        payload = response.json()
    if not isinstance(payload, dict) or payload.get("service") != service or payload.get("state") not in {"up", "degraded"}:
        raise ValueError("Upstream status did not match its contract.")
    return {"service": service, "state": payload["state"]}


if __name__ == "__main__":
    mcp.run()

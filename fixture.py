"""Seed fixture data and expose a local status REST API."""
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine, text

ROOT = Path(__file__).parent
app = FastAPI(title="AgentBridge fixture")


@app.get("/status/{service}")
def status(service: str):
    states = {"billing": "up", "exports": "degraded"}
    if service not in states:
        raise HTTPException(404)
    return {"service": service, "state": states[service]}


def seed():
    engine = create_engine(os.getenv("DATABASE_URL", f"sqlite:///{(ROOT / 'orders.db').as_posix()}"))
    with engine.begin() as db:
        db.execute(text("CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, status TEXT NOT NULL)"))
        db.execute(text("INSERT INTO orders VALUES (:id, :status) ON CONFLICT (order_id) DO NOTHING"),
                   [{"id": "ORD-1001", "status": "shipped"}, {"id": "ORD-1002", "status": "pending"}])
    engine.dispose()


if __name__ == "__main__":
    seed()

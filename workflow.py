"""MCP client with restricted workflows and source-grounded policy answers."""
import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).parent
ROUTES = {"policy": ("search_policy", "query"), "order": ("lookup_order", "order_id"),
          "status": ("service_status", "service")}
QUERIES = [
    ("refund submitted after purchase", "billing-refund"),
    ("who approves refund exceptions", "billing-refund"),
    ("where can account owners export records", "data-export"),
    ("how long until export files expire", "data-export"),
    ("page on-call for critical outage", "incident-escalation"),
    ("notify incident command", "incident-escalation"),
    ("quarterly privileged access review", "access-review"),
    ("revoke access when employee leaves", "access-review"),
    ("recovery ticket for restoration", "backup-restore"),
    ("test backup restores monthly", "backup-restore"),
    ("purchases above 5000", "purchase-approval"),
    ("procurement manager approval", "purchase-approval"),
]


async def run(route, value):
    env = {key: os.environ[key] for key in ("DATABASE_URL", "STATUS_API") if key in os.environ}
    params = StdioServerParameters(command=sys.executable, args=[str(ROOT / "bridge.py")], env=env)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        manifest = {tool.name for tool in (await session.list_tools()).tools}
        if route == "benchmark":
            checks = []
            for query, expected in QUERIES:
                result = await session.call_tool("search_policy", {"query": query})
                hits = (result.structuredContent or {}).get("result", [])
                checks.append({"query": query, "expected": expected,
                               "found": hits[0]["source"] if hits else None})
            good = await session.call_tool("lookup_order", {"order_id": "ORD-1001"})
            invalid = await session.call_tool("lookup_order", {"order_id": "invalid"})
            empty = await session.call_tool("search_policy", {"query": "unicorn nebula"})
            status = await session.call_tool("service_status", {"service": "exports"})
            bad_service = await session.call_tool("service_status", {"service": "unlisted"})
            report = {"tools_discovered": sorted(manifest), "top1": sum(x["expected"] == x["found"] for x in checks),
                      "queries": checks, "order_lookup_ok": not good.isError and "shipped" in str(good.structuredContent),
                      "invalid_rejected": invalid.isError,
                      "rest_lookup_ok": not status.isError and "degraded" in str(status.structuredContent),
                      "unlisted_service_rejected": bad_service.isError,
                      "unsupported_query_empty": not empty.isError and not (empty.structuredContent or {}).get("result")}
            (ROOT / "results.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return report
        tool, field = ROUTES[route]
        if tool not in manifest:
            return {"ok": False, "error": "Expected tool is unavailable"}
        result = await session.call_tool(tool, {field: value})
        if result.isError:
            return {"ok": False, "error": "Tool call failed. Check the input or upstream service."}
        return {"ok": True, "evidence": result.structuredContent}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", choices=[*ROUTES, "benchmark"])
    parser.add_argument("value", nargs="?", default="")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(run(args.route, args.value)), indent=2))

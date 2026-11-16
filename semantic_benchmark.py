"""Compare lexical and semantic retrieval through MCP on paraphrased requests."""
import asyncio
import json
import os
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CASES = [
    ("Can I get my money back four weeks later?", "billing-refund"),
    ("How can I download a copy of my information?", "data-export"),
    ("Who should I contact if the whole site goes down?", "incident-escalation"),
    ("Remove permissions after staff departure", "access-review"),
    ("What authorization is needed to recover from a saved copy?", "backup-restore"),
    ("Who signs off on a large company purchase?", "purchase-approval"),
]


async def main():
    report = {}
    env = {key: os.environ[key] for key in ("EMBEDDING_MODEL", "HF_HOME", "HF_HUB_OFFLINE") if key in os.environ}
    params = StdioServerParameters(command=sys.executable, args=[str(Path(__file__).with_name("bridge.py"))], env=env)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        for route, tool in (("policy", "search_policy"), ("semantic", "search_semantic")):
            rows = []
            for query, expected in CASES:
                response = await session.call_tool(tool, {"query": query})
                if response.isError:
                    raise RuntimeError(str(response.content))
                hits = (response.structuredContent or {}).get("result", [])
                rows.append({"query": query, "expected": expected,
                             "retrieved": [hit["source"] for hit in hits]})
            report[route] = {
                "top1": sum(row["retrieved"][:1] == [row["expected"]] for row in rows),
                "top3": sum(row["expected"] in row["retrieved"] for row in rows), "cases": rows,
            }
    Path(__file__).with_name("semantic-results.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

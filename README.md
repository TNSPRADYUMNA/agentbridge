# AgentBridge

AgentBridge is a read-only MCP integration prototype for internal policy retrieval, order lookup, and service status. Its Python client discovers the tools over MCP stdio, checks that the requested tool is present, invokes it with a structured payload, and returns typed evidence. The MCP server validates arguments before making calls.

| Tool | Integration | Contract |
| --- | --- | --- |
| `search_policy` | Six synthetic internal policies | Rank passages by token overlap and return source IDs |
| `lookup_order` | SQLite fixture or PostgreSQL connection | Parameterized lookup for a validated order ID |
| `service_status` | FastAPI REST fixture or configured service | Allowlisted service names, bounded timeout, and validated response |

## Reproduce

Python 3.11. In the first terminal:

```sh
python -m pip install -r requirements.txt
python fixture.py
python -m uvicorn fixture:app --host 127.0.0.1 --port 8020
```

In a second terminal:

```sh
python workflow.py benchmark
python workflow.py policy "when do export files expire"
python workflow.py order ORD-1001
python workflow.py status exports
```

The Docker image runs the MCP server on stdin/stdout. Build it with `docker build -t agentbridge .` and start it with `docker run --rm -i agentbridge`. Configure `STATUS_API` to a reachable REST service for the status tool. For PostgreSQL, use a `postgresql+psycopg://` URL in `DATABASE_URL` and provision the orders schema with `fixture.py` against a development database. Use a SELECT-only role for the runtime server. The verified benchmark uses SQLite.

## Fixture results

The real MCP transport discovered 3 tools. Policy retrieval ranked the expected source first on **12 of 12 hand-authored questions**. SQL lookup and the local REST lookup returned expected values. An invalid order ID and unlisted service were rejected. An unrelated question returned no passages. [Raw report](results.json)

These questions were written for six short policies and share vocabulary with them. The benchmark checks integration wiring and retrieval behavior on the fixture. Cross-domain retrieval and paraphrase robustness remain unmeasured.

## Optional evidence-grounded generation

The default client returns retrieved passages and source IDs for inspection. Save a workflow response as UTF-8 JSON and run `python draft.py evidence.json` to ask a compatible chat-completions provider for a draft. Configure the full `LLM_CHAT_URL`, `LLM_MODEL`, and `LLM_API_KEY` through the environment. The command sends the evidence to that provider and returns text for review. It has no tool-execution authority. LLM output quality is outside the reported benchmark.

The implemented stack uses Python, the MCP SDK, FastAPI, Pydantic, HTTPX and SQLAlchemy. Retrieval is lexical and routing is explicit. Dense retrieval, LangGraph, LangChain and ChromaDB remain beyond the implemented prototype. Docker and PostgreSQL configurations were not exercised in the benchmark.

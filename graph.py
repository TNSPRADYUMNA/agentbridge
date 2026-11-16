"""Run a restricted, stateful agent workflow over MCP."""
import argparse
import asyncio
import json
from typing import TypedDict

from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, START, StateGraph

from workflow import run


class State(TypedDict, total=False):
    route: str
    value: str
    result: dict
    answer: dict
    generate: bool


async def invoke(state: State):
    return {"result": await run(state["route"], state["value"])}


def render(result):
    if not result["ok"]:
        return {"status": "failed", "message": result["error"]}
    evidence = result.get("evidence")
    if not evidence or evidence == {"result": []} or evidence == {"result": None}:
        return {"status": "no_evidence", "evidence": []}
    return {"status": "grounded", "evidence": evidence}


def compose(state):
    answer = RunnableLambda(render).invoke(state["result"])
    if state.get("generate") and answer["status"] == "grounded":
        from draft import draft

        answer["draft"] = draft(answer["evidence"])
    return {"answer": answer}


builder = StateGraph(State)
builder.add_node("invoke", invoke)
builder.add_node("compose", compose)
builder.add_edge(START, "invoke")
builder.add_edge("invoke", "compose")
builder.add_edge("compose", END)
graph = builder.compile()


async def main(route, value, generate=False):
    state = await graph.ainvoke({"route": route, "value": value, "generate": generate})
    return state["answer"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", choices=("policy", "semantic", "order", "status"))
    parser.add_argument("value")
    parser.add_argument("--draft", action="store_true", help="Send retrieved evidence to the configured LLM")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(main(args.route, args.value, args.draft)), indent=2))

from langgraph.graph import StateGraph, START
from src.graph.state import SandboxState
from src.graph.nodes import (
    coder_node,
    executor_node,
    critic_node,
    success_node,
    fail_node,
)


def should_retry(state: SandboxState) -> str:
    if state.get("sandbox_result") and state["sandbox_result"].success:
        return "success"
    if state["retry_count"] < state["max_retries"]:
        return "critic"
    return "fail"


def build_sandbox_graph(max_retries: int = 3) -> StateGraph:
    builder = StateGraph(SandboxState)

    builder.add_node("coder", coder_node)
    builder.add_node("executor", executor_node)
    builder.add_node("critic", critic_node)
    builder.add_node("success", success_node)
    builder.add_node("fail", fail_node)

    builder.add_edge(START, "coder")
    builder.add_edge("coder", "executor")
    builder.add_conditional_edges(
        "executor",
        should_retry,
        {
            "success": "success",
            "critic": "critic",
            "fail": "fail",
        },
    )
    builder.add_edge("critic", "coder")

    return builder.compile()

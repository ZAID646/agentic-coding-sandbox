from src.graph.state import SandboxState
from src.agents.coder import generate_code
from src.agents.critic import analyze_error
from src.sandbox.executor import execute_code


def coder_node(state: SandboxState) -> dict:
    last_error = None
    if state.get("error_analysis"):
        last_error = state["error_analysis"]

    code = generate_code(state["user_prompt"], previous_error=last_error)

    trace_entry = {
        "node": "coder",
        "retry": state["retry_count"],
        "explanation": code.explanation[:200],
        "requirements": code.requirements,
    }

    return {
        "script": code.script,
        "requirements": code.requirements,
        "explanation": code.explanation,
        "trace": state.get("trace", []) + [trace_entry],
    }


def executor_node(state: SandboxState) -> dict:
    result = execute_code(state["script"], state.get("requirements"))

    trace_entry = {
        "node": "executor",
        "retry": state["retry_count"],
        "exit_code": result.exit_code,
        "success": result.success,
        "stdout_preview": result.stdout[:300] if result.stdout else "",
        "stderr_preview": result.stderr[:300] if result.stderr else "",
    }

    updates: dict = {
        "sandbox_result": result,
        "files": result.files,
        "trace": state.get("trace", []) + [trace_entry],
    }

    if result.success:
        updates["final_output"] = result.stdout
    else:
        updates["final_error"] = result.stderr

    return updates


def critic_node(state: SandboxState) -> dict:
    critique = analyze_error(
        script=state["script"],
        stderr=state["sandbox_result"].stderr,
        user_prompt=state["user_prompt"],
    )

    trace_entry = {
        "node": "critic",
        "retry": state["retry_count"],
        "error_analysis": critique.error_analysis[:300],
        "correction_strategy": critique.correction_strategy[:300],
        "confidence": critique.confidence,
    }

    prev = state.get("error_analysis") or ""
    return {
        "error_analysis": prev
        + f"\n--- Attempt {state['retry_count'] + 1} ---\n"
        + critique.error_analysis,
        "correction_strategy": critique.correction_strategy,
        "retry_count": state["retry_count"] + 1,
        "trace": state.get("trace", []) + [trace_entry],
    }


def success_node(state: SandboxState) -> dict:
    return {
        "final_output": state.get("final_output") or state.get("script", ""),
        "final_error": None,
    }


def fail_node(state: SandboxState) -> dict:
    return {
        "final_output": None,
        "final_error": state.get("final_error", "Unknown error after all retries exhausted."),
    }

import sys
import json
from src.graph.workflow import build_sandbox_graph
from src.graph.state import SandboxState
from src.config import MAX_RETRIES


def run_sandbox(user_prompt: str) -> dict:
    graph = build_sandbox_graph(max_retries=MAX_RETRIES)

    initial: SandboxState = {
        "user_prompt": user_prompt,
        "script": None,
        "requirements": [],
        "explanation": None,
        "sandbox_result": None,
        "error_analysis": None,
        "correction_strategy": None,
        "retry_count": 0,
        "max_retries": MAX_RETRIES,
        "trace": [],
        "final_output": None,
        "final_error": None,
        "files": {},
    }

    result = graph.invoke(initial)

    return {
        "success": result.get("final_error") is None,
        "output": result.get("final_output"),
        "error": result.get("final_error"),
        "retries_used": result.get("retry_count", 0),
        "trace": result.get("trace", []),
        "files": result.get("files", {}),
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python -m src.main '<prompt>'")
        sys.exit(1)

    prompt = sys.argv[1]
    result = run_sandbox(prompt)

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

[![Hugging Face Space](https://img.shields.io/badge/%F0%9F%A4%97%20Hugging%20Face-Live%20Demo-blue)](https://zaid646-agentic-coding-sandbox.hf.space)

# Agentic Coding Sandbox

A self-correcting agentic system that generates, executes, and autonomously debugs Python code inside an isolated Docker sandbox. Built with LangGraph for workflow orchestration and powered by LLM agents (OpenCode Zen / DeepSeek V4 Flash Free).

## Features

- **Three-Agent Architecture** — Coder generates Python code, Executor runs it in a sandboxed Docker container, Critic analyzes failures and prescribes fixes.
- **Autonomous Self-Healing** — On execution failure, the Critic agent analyzes the error (syntax, import, runtime, network, or file issues) and sends a correction strategy back to the Coder for a rewrite. Up to 3 retries per prompt.
- **Docker Sandbox Isolation** — Each execution runs in a read-only Python 3.14-slim container with tmpfs `/tmp`, memory limit (512 MB), PID limit (64), and no-new-privileges security policy. Network access is enabled.
- **Automatic Dependency Resolution** — Required pip packages are detected by the LLM and installed into the container before execution.
- **File and Chart Extraction** — Images (PNG, JPEG, GIF, SVG, WebP) saved to `/tmp` during execution are automatically captured, base64-encoded, and returned alongside stdout.
- **Multiple Interfaces** — CLI for scripting, Streamlit dashboard for interactive use, FastAPI for programmatic access.
- **Full Execution Trace** — Every step (code generation, execution result, error analysis) is recorded and returned for inspection.

## Architecture

```
User Prompt
    |
    v
[Coder Agent]  --generates-->  Python script + requirements
    |
    v
[Executor]  --runs in Docker sandbox-->
    |
    +-- Success? --> [Success Node] --> Final output + extracted files
    |
    +-- Failure (retries < 3)? --> [Critic Agent] --> error analysis + strategy --> Coder Agent (retry)
    |
    +-- Failure (retries >= 3)? --> [Fail Node] --> Final error
```

The workflow is implemented as a LangGraph `StateGraph` with conditional edges. The `should_retry` routing function checks the execution result and remaining retry budget to decide whether to loop back to the Critic or terminate.

## Prerequisites

- Python 3.12 or later
- Docker Engine running (tested with Colima on macOS at `~/.colima/default/docker.sock`)
- An API key for the LLM provider (OpenCode Zen / DeepSeek V4 Flash Free)

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/ZAID646/agentic-coding-sandbox.git
cd agentic-coding-sandbox
```

### 2. Install dependencies

Using uv (recommended):

```bash
uv sync
```

Or using pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your API key:

```
OPENCODE_ZEN_API_KEY=your-api-key-here
LLM_BASE_URL=https://opencode.ai/zen/v1
LLM_MODEL=deepseek-v4-flash-free
MAX_RETRIES=3
SANDBOX_IMAGE=python:3.14-slim
SANDBOX_TIMEOUT=30
```

### 4. Run

**CLI:**

```bash
python -m src.main "Use asyncio and aiohttp to fetch JSON from https://jsonplaceholder.typicode.com/todos/1 and print the title field."
```

**Streamlit Dashboard:**

Start the API server in one terminal:

```bash
python -m src.ui.api
```

Then in another terminal:

```bash
streamlit run src/ui/dashboard.py
```

Open the URL shown by Streamlit (default: `http://localhost:8501`).

**FastAPI (direct):**

```bash
python -m src.ui.api
```

Then send requests:

```bash
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Print the first 10 Fibonacci numbers."}'
```

Check health:

```bash
curl http://localhost:8000/health
```

## Project Structure

```
agentic-coding-sandbox/
├── pyproject.toml          # Project metadata and dependencies
├── README.md
├── LICENSE
├── .env.example            # Environment variable template
├── .gitignore
├── docker/                 # Reserved for custom Dockerfiles
├── tests/                  # Test suite
├── src/
│   ├── __init__.py
│   ├── config.py           # Environment configuration
│   ├── main.py             # CLI entry point and sandbox runner
│   ├── models.py           # Pydantic data models
│   ├── agents/
│   │   ├── coder.py        # Coder agent: generates Python code from prompt
│   │   └── critic.py       # Critic agent: analyzes errors and suggests fixes
│   ├── graph/
│   │   ├── state.py        # LangGraph state schema
│   │   ├── nodes.py        # Graph node implementations
│   │   └── workflow.py     # LangGraph StateGraph builder and routing logic
│   ├── sandbox/
│   │   └── executor.py     # Docker sandbox execution and file extraction
│   └── ui/
│       ├── api.py          # FastAPI REST endpoint
│       └── dashboard.py    # Streamlit interactive dashboard
└── uv.lock                 # Locked dependencies (uv)
```

## How the Self-Healing Loop Works

1. **Coder Agent** receives the user's natural-language prompt and produces a Python script (optionally with a list of pip requirements). The LLM is instructed to output structured JSON containing the script, an explanation, and the requirements list.

2. **Executor** takes the script and optionally builds a custom Docker image with the required pip packages installed. It wraps the script in a base64-encoded payload to avoid shell escaping issues and runs it inside a read-only container with:
   - Network access enabled
   - `/tmp` mounted as tmpfs (64 MB) for temporary file output
   - `MPLCONFIGDIR` set to `/tmp` so matplotlib works out of the box
   - 512 MB memory limit and 64 PID limit
   - All Linux capabilities dropped; `no-new-privileges` enabled

   After execution, the container logs are scanned for `__SANDBOX_FILE__` markers to extract any generated images from `/tmp`.

3. **Critic Agent** is invoked only if the execution fails and the retry budget has not been exhausted. It receives the original prompt, the script, and the full stderr output, and returns an error analysis with a specific correction strategy. The Critic recognizes common failure patterns: missing packages (recommends adding to requirements), network errors (suggests URL checks or retry logic), syntax errors, and file-not-found issues.

4. **Retry Loop** feeds the Critic's correction strategy (along with the original prompt) back to the Coder agent. The Coder rewrites the script incorporating the fix. This cycle repeats up to `MAX_RETRIES` times (default: 3). If execution eventually succeeds, the result is returned. If all retries are exhausted, the final error is returned.

## Configuration

| Environment Variable   | Default                               | Description                            |
|------------------------|---------------------------------------|----------------------------------------|
| `OPENCODE_ZEN_API_KEY` | (required)                            | API key for the LLM provider           |
| `LLM_BASE_URL`         | `https://opencode.ai/zen/v1`          | LLM API base URL                       |
| `LLM_MODEL`            | `deepseek-v4-flash-free`              | LLM model identifier                   |
| `MAX_RETRIES`          | `3`                                   | Maximum self-healing attempts           |
| `SANDBOX_IMAGE`        | `python:3.14-slim`                    | Docker image for code execution         |
| `SANDBOX_TIMEOUT`      | `30`                                  | Container execution timeout in seconds  |

## API Reference

### POST `/run`

Executes a coding task.

Request body:

```json
{
  "prompt": "Print the first 10 Fibonacci numbers."
}
```

Response:

```json
{
  "success": true,
  "output": "0\n1\n1\n2\n3\n5\n8\n13\n21\n34",
  "error": null,
  "retries_used": 0,
  "trace": [...],
  "files": {}
}
```

### GET `/health`

Returns `{"status": "ok"}` when the server is running.

## Tech Stack

- **Python 3.12+** — Core runtime
- **LangGraph** — Workflow orchestration with state graphs and conditional edges
- **OpenAI Python SDK** — LLM API calls (OpenCode Zen / DeepSeek V4 Flash Free)
- **Docker SDK for Python** — Container lifecycle management
- **FastAPI + Uvicorn** — REST API server
- **Streamlit** — Interactive dashboard UI
- **Pydantic** — Data validation and serialization
- **python-dotenv** — Environment variable management

## License

MIT License. See [LICENSE](LICENSE) for details.

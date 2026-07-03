from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
from src.main import run_sandbox

app = FastAPI(title="Agentic Coding Sandbox")


class SandboxRequest(BaseModel):
    prompt: str


class SandboxResponse(BaseModel):
    success: bool
    output: str | None
    error: str | None
    retries_used: int
    trace: list[dict]
    files: dict[str, str] = {}


@app.post("/run", response_model=SandboxResponse)
def run_sandbox_endpoint(req: SandboxRequest):
    return run_sandbox(req.prompt)


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

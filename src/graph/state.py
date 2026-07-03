from typing import TypedDict, Optional
from src.models import SandboxResult


class SandboxState(TypedDict):
    user_prompt: str
    script: Optional[str]
    requirements: list[str]
    explanation: Optional[str]
    sandbox_result: Optional[SandboxResult]
    error_analysis: Optional[str]
    correction_strategy: Optional[str]
    retry_count: int
    max_retries: int
    trace: list[dict]
    final_output: Optional[str]
    final_error: Optional[str]
    files: dict[str, str]

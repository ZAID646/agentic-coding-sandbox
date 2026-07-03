from pydantic import BaseModel


class CodeResponse(BaseModel):
    explanation: str
    script: str
    requirements: list[str]


class CritiqueResponse(BaseModel):
    error_analysis: str
    correction_strategy: str
    confidence: float


class SandboxResult(BaseModel):
    stdout: str
    stderr: str
    exit_code: int
    success: bool
    files: dict[str, str] = {}

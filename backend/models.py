from typing import Literal
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    classification: Literal['OBSERVED'] = 'OBSERVED'
    type: str
    file: str
    line: int | None = None
    detail: str


class Declaration(BaseModel):
    file: str
    line: int
    constraint: str
    marker: str = ''
    group: str = 'runtime'
    active: bool | None = True
    url: str | None = None


class Usage(BaseModel):
    file: str
    line: int
    symbol: str
    kind: str
    snippet: str
    mapping: str


class Dependency(BaseModel):
    name: str
    declared_versions: list[Declaration] = Field(default_factory=list)
    risk_level: Literal['high', 'medium', 'low', 'unknown'] = 'low'
    risk_indicators: list[str] = Field(default_factory=list)
    usage_locations: list[Usage] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    ai_recommendation: dict | None = None
    ai_error: str | None = None


class ScanRequest(BaseModel):
    repository_path: str = Field(min_length=1, max_length=4096)


class ScanResult(BaseModel):
    scan_id: str
    repository: str
    repository_path: str
    status: str = 'success'
    fingerprint: str
    generated_at: str
    dependencies: list[Dependency]
    scan_errors: list[str] = Field(default_factory=list)
    python_files: int = 0
    test_files: list[str] = Field(default_factory=list)
    manifests: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    ai_status: str = 'not_run'
    model_info: dict = Field(default_factory=dict)


class VerifyRequest(BaseModel):
    scan_id: str
    dependency_name: str = Field(min_length=1, max_length=200)
    proposed_version: str = Field(min_length=1, max_length=100)
    trusted_repository: bool = False


class CapsuleRequest(BaseModel):
    scan_id: str


class Outcome(BaseModel):
    status: str = 'NOT RUN'
    classification: str = 'OBSERVED'
    commands: list[list[str]] = Field(default_factory=list)
    exit_code: int | None = None
    output: str = ''
    reason: str = ''
    python_version: str | None = None
    duration_seconds: float = 0
    passed: int | None = None
    failed: int | None = None
    skipped: int | None = None
    tests_completed: bool = False
    installation_problem: bool = False


class Verification(BaseModel):
    scan_id: str
    dependency_name: str
    proposed_version: str
    verification_status: str
    baseline: Outcome
    migration: Outcome
    static_comparison: dict
    compatibility_gaps: list[str]
    limitations: list[str]

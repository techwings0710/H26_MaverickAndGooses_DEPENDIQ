from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Recommendation(BaseModel):
    model_config = ConfigDict(extra='forbid', str_max_length=6000)
    proposed_replacement: str = Field(min_length=1)
    technical_reasoning: str = Field(min_length=1)
    migration_steps: list[str] = Field(min_length=1, max_length=15)
    suggested_tests: list[str] = Field(min_length=1, max_length=15)
    potential_compatibility_gaps: list[str] = Field(max_length=15)
    uncertainties: list[str] = Field(min_length=1, max_length=15)
    confidence: Literal['low', 'medium', 'high']
    classification: Literal['AI-SUGGESTED'] = 'AI-SUGGESTED'
    verified: Literal[False] = False

"""Data models: what the LLM must return, and what the final report contains."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator

Implemented = Literal["yes", "partial", "no"]
Tested = Literal["yes", "no"]


class Criterion(BaseModel):
    id: str  # "AC1", "AC2", ...
    text: str


class Requirement(BaseModel):
    title: str
    user_story: str
    criteria: list[Criterion]


# ---- LLM output schema (validated with pydantic) ----


class Evidence(BaseModel):
    file: str
    snippet: str


class Verdict(BaseModel):
    id: str
    implemented: Implemented
    tested: Tested
    evidence: list[Evidence] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    reasoning: str

    @field_validator("implemented", "tested", mode="before")
    @classmethod
    def _lowercase(cls, value):
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("id", mode="before")
    @classmethod
    def _normalize_id(cls, value):
        # Accept "1", "ac1", " AC1 " and turn them into "AC1".
        value = str(value).strip().upper()
        return f"AC{value}" if value.isdigit() else value


class LLMOutput(BaseModel):
    criteria: list[Verdict]


# ---- Report ----


class CheckedEvidence(Evidence):
    verified: bool
    is_test_file: bool
    note: str = ""  # why it failed verification


class CriterionResult(BaseModel):
    id: str
    text: str
    implemented: Implemented
    tested: Tested
    confidence: float
    reasoning: str
    evidence: list[CheckedEvidence]
    review_reasons: list[str] = Field(default_factory=list)

    @property
    def needs_human_review(self) -> bool:
        return bool(self.review_reasons)

    @property
    def has_gap(self) -> bool:
        return self.implemented != "yes" or self.tested != "yes"


class CallStat(BaseModel):
    purpose: str  # "initial" or "repair"
    model: str
    latency_s: float
    prompt_tokens: int
    completion_tokens: int
    retries: int


class CheckReport(BaseModel):
    title: str
    user_story: str
    model: str
    prompt_version: str
    results: list[CriterionResult]
    calls: list[CallStat]

    @property
    def total_snippets(self) -> int:
        return sum(len(r.evidence) for r in self.results)

    @property
    def unverified_snippets(self) -> int:
        return sum(1 for r in self.results for e in r.evidence if not e.verified)

    @property
    def total_tokens(self) -> int:
        return sum(c.prompt_tokens + c.completion_tokens for c in self.calls)

    @property
    def total_latency_s(self) -> float:
        return sum(c.latency_s for c in self.calls)

    def has_gaps(self) -> bool:
        """True if anything should block a release: a gap or an unverified claim."""
        return any(r.has_gap or r.needs_human_review for r in self.results)

    def to_json_dict(self) -> dict:
        data = self.model_dump()
        for result, raw in zip(self.results, data["results"], strict=True):
            raw["needs_human_review"] = result.needs_human_review
        data["summary"] = {
            "criteria": len(self.results),
            "gaps": sum(r.has_gap for r in self.results),
            "needs_human_review": sum(r.needs_human_review for r in self.results),
            "total_snippets": self.total_snippets,
            "unverified_snippets": self.unverified_snippets,
            "total_tokens": self.total_tokens,
            "total_latency_s": round(self.total_latency_s, 3),
        }
        return data

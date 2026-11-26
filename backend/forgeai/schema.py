from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
Tool = Literal["csv_lookup", "calculator", "current_date", "weather"]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Requirements(Model):
    scope: Text
    audience: Text
    tone: Text
    must_answer: list[Text] = Field(min_length=1)
    must_refuse: list[Text]
    assumptions: list[Text]
    unresolved: list[Text]
    original_brief: str = ""
    requester_answers: dict[str, str] = Field(default_factory=dict)
    behavior: list[Text] = Field(default_factory=list)


class Questions(Model):
    questions: list[Text] = Field(max_length=5)


class Settings(Model):
    chunk_words: int = Field(ge=24, le=180)
    overlap: int = Field(ge=0)
    top_k: int = Field(ge=1, le=8)
    min_score: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def check_stride(self):
        if self.overlap >= self.chunk_words:
            raise ValueError("Overlap must be smaller than chunk size")
        return self


class Selection(Model):
    name: Tool
    reason: Text


class Design(Model):
    system_prompt: Text
    settings: Settings
    tools: list[Selection]


class Passage(Model):
    id: Text
    file: Text
    text: Text
    page: int | None = None
    row: int | None = None
    cells: dict[str, str] | None = None


class Quote(Model):
    id: Text
    quote: Text


class Finding(Model):
    status: Literal["supported", "partial", "unsupported"]
    evidence: list[Quote]
    limitation: str
    retrieval_miss: bool = False
    inconclusive: bool = False
    tool: Tool | None = None


class Answer(Model):
    answer: Text
    citations: list[Text]
    refused: bool
    outcome: Literal["grounded", "clarification", "insufficient_evidence", "out_of_scope", "partial", "tool_assisted", "ungrounded"] | None = None

    @model_validator(mode="after")
    def grounded(self):
        if not self.refused and not self.citations and self.outcome != "clarification":
            raise ValueError("Answers require evidence")
        if self.outcome == "clarification" and (self.refused or self.citations):
            raise ValueError("A clarification has no refusal or citations")
        if self.outcome in {"grounded", "partial", "tool_assisted"} and self.refused:
            raise ValueError("An answer outcome cannot be marked refused")
        if self.outcome in {"insufficient_evidence", "out_of_scope", "ungrounded"} and not self.refused:
            raise ValueError("This outcome requires an abstention")
        return self


class Config(Design):
    version: Literal[1]
    model: Text
    embedding: Text
    requirements: Requirements
    coverage: dict[str, Finding]
    document_manifest: dict[str, str]
    output_contract: dict
    corpus_sha256: Text
    sources_sha256: Text | None = None
    evidence_only: bool = False
    precise_citations: bool = False
    verify_scope: bool = False
    requested_model: str | None = None
    generation_models: list[str] = Field(default_factory=list)
    behavioral_evaluation: bool = False


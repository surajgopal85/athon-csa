from __future__ import annotations

from datetime import date
from enum import Enum

from pydantic import BaseModel


class Severity(str, Enum):
    FATAL = "fatal"
    CORRECTABLE = "correctable"
    INFORMATIONAL = "informational"


class GateResult(BaseModel):
    gate_id: str
    passed: bool
    severity: Severity
    citation: str
    message: str
    fix: str | None = None


class Prescriber(BaseModel):
    name: str
    credential: str
    license_number: str


class Facility(BaseModel):
    name: str
    licensed_r501_19: bool
    bed_count: int
    is_imd: bool
    accreditation: str


# --- Evidence models (extraction layer output) ---


class Acuity(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class GoalStatus(str, Enum):
    MET = "met"
    PARTIALLY_MET = "partially_met"
    NOT_MET = "not_met"
    REGRESSED = "regressed"
    UNABLE_TO_ASSESS = "unable_to_assess"


class EvidenceAssertion(BaseModel):
    assertion: str
    source_text: str
    confidence: float
    conflicting: bool
    unquantified: bool


class DimensionEvidence(BaseModel):
    dimension: str
    acuity: Acuity
    assertions: list[EvidenceAssertion]


class GoalEvidence(BaseModel):
    goal_id: str
    status: GoalStatus
    assertions: list[EvidenceAssertion]


class ExtractedEvidence(BaseModel):
    case_id: str
    dimensions: list[DimensionEvidence]
    goals: list[GoalEvidence]


# --- Scoring models (clinical scoring output) ---


class Decision(str, Enum):
    APPROVE = "APPROVE"
    DENY_WITH_TRANSITION = "DENY_WITH_TRANSITION"
    DENY = "DENY"


class ScoreResult(BaseModel):
    case_id: str
    decision: Decision
    decision_confidence: float
    procedural_results: list[GateResult]
    has_fatal_gate: bool
    credible_high_dimensions: list[str]
    rationale: list[str]


# --- Episode model (procedural layer input) ---


class Episode(BaseModel):
    member_id: str
    member_age: int
    asam_level_requested: str
    intake_date: date
    days_elapsed_at_request: int
    first_requested_dos: date
    days_requested: int
    submission_date: date
    last_reassessment_date: date
    prior_reassessment_date: date
    has_reassessment: bool
    prescriber: Prescriber
    facility: Facility

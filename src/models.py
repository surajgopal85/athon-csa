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

from __future__ import annotations

import asyncio
import json
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.extraction import extract_evidence
from src.models import (
    Decision,
    Episode,
    ExtractedEvidence,
    Facility,
    GateResult,
    Prescriber,
    Severity,
)
from src.procedural import (
    check_age_eligibility,
    check_facility_licensing,
    check_pa_duration_cap,
    check_reassessment_presence,
    check_reassessment_timeliness,
    check_submission_window,
)
from src.scoring import score_case

app = FastAPI(title="CSA Scoring Engine")
templates = Jinja2Templates(directory="templates")

ALL_GATES = [
    check_age_eligibility,
    check_facility_licensing,
    check_pa_duration_cap,
    check_reassessment_presence,
    check_reassessment_timeliness,
    check_submission_window,
]

# In-memory cache of results after pipeline run
_results_cache: dict = {}
_evidence_cache: dict = {}


def _load_cases() -> list[dict]:
    with open("cases-v1.json") as f:
        return json.load(f)["cases"]


def _build_episode(case: dict) -> Episode:
    ep = case["episode"]
    return Episode(
        member_id=ep["member_id"],
        member_age=ep["member_age"],
        asam_level_requested=ep["asam_level_requested"],
        intake_date=date.fromisoformat(ep["intake_date"]),
        days_elapsed_at_request=ep["days_elapsed_at_request"],
        first_requested_dos=date.fromisoformat(ep["first_requested_dos"]),
        days_requested=ep["days_requested"],
        submission_date=date.fromisoformat(ep["submission_date"]),
        last_reassessment_date=date.fromisoformat(ep["last_reassessment_date"]),
        prior_reassessment_date=date.fromisoformat(ep["prior_reassessment_date"]),
        has_reassessment="reassessment" in case and bool(case["reassessment"]),
        prescriber=Prescriber(**ep["prescriber"]),
        facility=Facility(**ep["facility"]),
    )


def _next_action(score_result, gate_results: list[GateResult]) -> str:
    """Determine the specific next action for the billing person."""
    # Fatal gate → specific procedural fix
    fatal = [g for g in gate_results if not g.passed and g.severity == Severity.FATAL]
    if fatal:
        return f"Cannot proceed: {fatal[0].message}"

    # Correctable gate → specific fix
    correctable = [
        g for g in gate_results if not g.passed and g.severity == Severity.CORRECTABLE
    ]

    if score_result.decision == Decision.APPROVE:
        if correctable:
            return f"Approve pending correction: {correctable[0].fix}"
        return "Submit for approval. Clinical documentation supports continued stay."

    if score_result.decision == Decision.DENY_WITH_TRANSITION:
        return (
            "Request up to 14 calendar transition days per UT-7-19-4-3-a. "
            "Clinical documentation does not support continued stay at current level."
        )

    # Hard deny
    if not score_result.credible_high_dimensions and not score_result.has_fatal_gate:
        return (
            "Denial expected. Strengthen clinical documentation: "
            "add measurable progress notes, specific ASAM dimension assessments, "
            "and goal-level tracking before resubmission."
        )
    return "Denial expected."


async def _run_pipeline():
    """Run the full pipeline on all cases and cache results."""
    cases = _load_cases()
    client = anthropic.AsyncAnthropic()

    async def process(case):
        case_id = case["case_id"]
        episode = _build_episode(case)
        gate_results = [gate(episode) for gate in ALL_GATES]

        has_fatal = any(
            not g.passed and g.severity == Severity.FATAL for g in gate_results
        )

        evidence = None
        if not has_fatal:
            try:
                evidence = await extract_evidence(case, client)
            except Exception as e:
                print(f"  {case_id}: Extraction error: {e}")

        result = score_case(case_id, gate_results, evidence)
        action = _next_action(result, gate_results)

        return case_id, {
            "case": case,
            "episode": episode,
            "gate_results": gate_results,
            "evidence": evidence,
            "score": result,
            "next_action": action,
        }

    tasks = [process(case) for case in cases]
    pairs = await asyncio.gather(*tasks)
    for case_id, data in pairs:
        _results_cache[case_id] = data


@app.on_event("startup")
async def startup():
    await _run_pipeline()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    cases = []
    for case_id in sorted(_results_cache.keys()):
        data = _results_cache[case_id]
        ep = data["case"]["episode"]
        score = data["score"]
        cases.append(
            {
                "case_id": case_id,
                "member_age": ep["member_age"],
                "decision": score.decision.value,
                "next_action": data["next_action"],
                "decision_confidence": score.decision_confidence,
                "has_fatal": score.has_fatal_gate,
                "gate_failures": [
                    g for g in data["gate_results"] if not g.passed
                ],
            }
        )
    return templates.TemplateResponse(request, "index.html", {"cases": cases})


@app.get("/case/{case_id}", response_class=HTMLResponse)
async def case_detail(request: Request, case_id: str):
    data = _results_cache.get(case_id)
    if not data:
        return HTMLResponse("<h1>Case not found</h1>", status_code=404)

    score = data["score"]
    evidence = data["evidence"]
    gate_results = data["gate_results"]
    ep = data["case"]["episode"]

    # Build dimension display data
    dims = []
    if evidence:
        for dim in evidence.dimensions:
            avg_conf = (
                sum(a.confidence for a in dim.assertions) / len(dim.assertions)
                if dim.assertions
                else 0.0
            )
            dims.append(
                {
                    "name": dim.dimension,
                    "acuity": dim.acuity.value,
                    "avg_confidence": avg_conf,
                    "is_credible_high": dim.dimension
                    in score.credible_high_dimensions,
                    "has_conflict": any(a.conflicting for a in dim.assertions),
                    "has_unquantified": any(
                        a.unquantified for a in dim.assertions
                    ),
                    "assertions": dim.assertions,
                }
            )

    # Build goal display data
    goals = []
    if evidence:
        for goal in evidence.goals:
            avg_conf = (
                sum(a.confidence for a in goal.assertions) / len(goal.assertions)
                if goal.assertions
                else 0.0
            )
            goals.append(
                {
                    "goal_id": goal.goal_id,
                    "status": goal.status.value,
                    "avg_confidence": avg_conf,
                    "assertions": goal.assertions,
                }
            )

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "case_id": case_id,
            "episode": ep,
            "decision": score.decision.value,
            "decision_confidence": score.decision_confidence,
            "next_action": data["next_action"],
            "has_fatal": score.has_fatal_gate,
            "gate_results": gate_results,
            "dimensions": dims,
            "goals": goals,
            "rationale": score.rationale,
        },
    )

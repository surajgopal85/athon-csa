from __future__ import annotations

from src.models import (
    Acuity,
    Decision,
    ExtractedEvidence,
    GateResult,
    GoalStatus,
    ScoreResult,
    Severity,
)

CONFIDENCE_FLOOR = 0.6


def score_case(
    case_id: str,
    gate_results: list[GateResult],
    evidence: ExtractedEvidence | None,
) -> ScoreResult:
    """Score a case based on procedural gate results and extracted evidence.

    Logic:
      1. Any fatal gate failed → DENY (skip clinical layer)
      2. Has credible high-acuity dimension → APPROVE
         (acuity=high AND avg confidence >= 0.6)
      3. Has real documentation AND goal tracking → DENY_WITH_TRANSITION
         (any dimension confidence >= 0.6, AND at least one goal
          is not unable_to_assess)
      4. Otherwise → DENY
    """
    rationale: list[str] = []

    # Step 1: Check for fatal procedural failures
    fatal_failures = [
        g for g in gate_results
        if not g.passed and g.severity == Severity.FATAL
    ]
    has_fatal = len(fatal_failures) > 0

    if has_fatal:
        for g in fatal_failures:
            rationale.append(f"Fatal procedural failure: {g.message} [{g.citation}]")
        return ScoreResult(
            case_id=case_id,
            decision=Decision.DENY,
            procedural_results=gate_results,
            has_fatal_gate=True,
            credible_high_dimensions=[],
            rationale=rationale,
        )

    # Note correctable failures in rationale but don't block scoring
    correctable_failures = [
        g for g in gate_results
        if not g.passed and g.severity == Severity.CORRECTABLE
    ]
    for g in correctable_failures:
        rationale.append(f"Correctable: {g.message} Fix: {g.fix} [{g.citation}]")

    # If no evidence (shouldn't happen if procedural passed, but guard)
    if evidence is None:
        rationale.append("No extracted evidence available.")
        return ScoreResult(
            case_id=case_id,
            decision=Decision.DENY,
            procedural_results=gate_results,
            has_fatal_gate=False,
            credible_high_dimensions=[],
            rationale=rationale,
        )

    # Step 2: Find credible high-acuity dimensions
    credible_high: list[str] = []
    has_any_credible: bool = False

    for dim in evidence.dimensions:
        if not dim.assertions:
            continue

        avg_confidence = (
            sum(a.confidence for a in dim.assertions) / len(dim.assertions)
        )

        if avg_confidence >= CONFIDENCE_FLOOR:
            has_any_credible = True

        if dim.acuity == Acuity.HIGH and avg_confidence >= CONFIDENCE_FLOOR:
            credible_high.append(dim.dimension)
            rationale.append(
                f"{dim.dimension}: high acuity, avg confidence {avg_confidence:.2f}"
            )

    # Step 2 decision: credible high-acuity dimensions exist → APPROVE
    if credible_high:
        return ScoreResult(
            case_id=case_id,
            decision=Decision.APPROVE,
            procedural_results=gate_results,
            has_fatal_gate=False,
            credible_high_dimensions=credible_high,
            rationale=rationale,
        )

    # Step 3: Check for goal tracking — at least one goal must have
    # a determinable status (not unable_to_assess)
    has_goal_tracking = any(
        g.status != GoalStatus.UNABLE_TO_ASSESS for g in evidence.goals
    )

    # No credible high dims, but has real documentation AND goal tracking
    # → orderly transition
    if has_any_credible and has_goal_tracking:
        rationale.append(
            "No credible high-acuity dimension. Documentation supports "
            "orderly transition (UT-7-19-4-3-a, up to 14 calendar days)."
        )
        return ScoreResult(
            case_id=case_id,
            decision=Decision.DENY_WITH_TRANSITION,
            procedural_results=gate_results,
            has_fatal_gate=False,
            credible_high_dimensions=[],
            rationale=rationale,
        )

    # Step 4: Insufficient documentation or no goal tracking → hard deny
    reasons = []
    if not has_any_credible:
        reasons.append(
            f"no dimension has evidence above confidence floor ({CONFIDENCE_FLOOR})"
        )
    if not has_goal_tracking:
        reasons.append("no goal has a determinable status (all unable_to_assess)")
    rationale.append(f"Insufficient documentation: {'; '.join(reasons)}.")

    return ScoreResult(
        case_id=case_id,
        decision=Decision.DENY,
        procedural_results=gate_results,
        has_fatal_gate=False,
        credible_high_dimensions=[],
        rationale=rationale,
    )

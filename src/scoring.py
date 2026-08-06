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
CONFLICTING_PENALTY = 0.6


def _effective_confidence(dim) -> float:
    """Compute effective confidence for a dimension.

    Applies a penalty when any assertion in the dimension has
    conflicting=True. Conflicting evidence shouldn't carry the
    same weight as clean evidence.
    """
    if not dim.assertions:
        return 0.0

    avg = sum(a.confidence for a in dim.assertions) / len(dim.assertions)

    if any(a.conflicting for a in dim.assertions):
        avg *= CONFLICTING_PENALTY

    return avg


def score_case(
    case_id: str,
    gate_results: list[GateResult],
    evidence: ExtractedEvidence | None,
) -> ScoreResult:
    """Score a case based on procedural gate results and extracted evidence.

    Logic:
      1. Any fatal gate failed → DENY (skip clinical layer)
      2. Has credible high-acuity dimension → APPROVE
         (acuity=high AND effective confidence >= 0.6;
          conflicting evidence is penalized)
      3. Has real documentation AND goal tracking → DENY_WITH_TRANSITION
      4. Otherwise → DENY

    decision_confidence reflects how certain we are in the decision:
      - 1.0 for fatal procedural denials (certain)
      - Based on driving dimensions' effective confidence for approvals
      - Reduced when conflicting or unquantified evidence is present
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
            decision_confidence=1.0,
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
            decision_confidence=1.0,
            procedural_results=gate_results,
            has_fatal_gate=False,
            credible_high_dimensions=[],
            rationale=rationale,
        )

    # Step 2: Find credible high-acuity dimensions
    credible_high: list[str] = []
    credible_high_confidences: list[float] = []
    has_any_credible: bool = False

    for dim in evidence.dimensions:
        if not dim.assertions:
            continue

        eff_conf = _effective_confidence(dim)
        has_conflict = any(a.conflicting for a in dim.assertions)
        has_unquant = any(a.unquantified for a in dim.assertions)

        if eff_conf >= CONFIDENCE_FLOOR:
            has_any_credible = True

        if dim.acuity == Acuity.HIGH and eff_conf >= CONFIDENCE_FLOOR:
            credible_high.append(dim.dimension)
            credible_high_confidences.append(eff_conf)

            flags = []
            if has_conflict:
                flags.append("conflicting")
            if has_unquant:
                flags.append("unquantified")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            rationale.append(
                f"{dim.dimension}: high acuity, "
                f"effective confidence {eff_conf:.2f}{flag_str}"
            )
        elif dim.acuity == Acuity.HIGH and has_conflict:
            raw_avg = (
                sum(a.confidence for a in dim.assertions) / len(dim.assertions)
            )
            rationale.append(
                f"{dim.dimension}: high acuity but conflicting evidence "
                f"reduced effective confidence from {raw_avg:.2f} to "
                f"{eff_conf:.2f} (below floor)"
            )

    # Step 2 decision: credible high-acuity dimensions exist → APPROVE
    if credible_high:
        decision_conf = (
            sum(credible_high_confidences) / len(credible_high_confidences)
        )
        return ScoreResult(
            case_id=case_id,
            decision=Decision.APPROVE,
            decision_confidence=round(decision_conf, 2),
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
            decision_confidence=0.7,
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
        decision_confidence=0.9,
        procedural_results=gate_results,
        has_fatal_gate=False,
        credible_high_dimensions=[],
        rationale=rationale,
    )

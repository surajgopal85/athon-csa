from __future__ import annotations

from src.models import (
    Acuity,
    Decision,
    DimensionEvidence,
    EvidenceAssertion,
    ExtractedEvidence,
    GateResult,
    GoalEvidence,
    GoalStatus,
    Severity,
)
from src.scoring import CONFIDENCE_FLOOR, score_case


def _gate_pass(gate_id: str = "age_eligibility") -> GateResult:
    return GateResult(
        gate_id=gate_id,
        passed=True,
        severity=Severity.FATAL,
        citation="UT-test",
        message="Pass.",
    )


def _gate_fatal_fail(gate_id: str = "submission_window") -> GateResult:
    return GateResult(
        gate_id=gate_id,
        passed=False,
        severity=Severity.FATAL,
        citation="UT-test",
        message="Fatal failure.",
    )


def _gate_correctable_fail(gate_id: str = "pa_duration_cap") -> GateResult:
    return GateResult(
        gate_id=gate_id,
        passed=False,
        severity=Severity.CORRECTABLE,
        citation="UT-test",
        message="Correctable failure.",
        fix="Resubmit.",
    )


def _assertion(
    confidence: float = 0.9,
    conflicting: bool = False,
    unquantified: bool = False,
) -> EvidenceAssertion:
    return EvidenceAssertion(
        assertion="Test assertion.",
        source_text="Test source.",
        confidence=confidence,
        conflicting=conflicting,
        unquantified=unquantified,
    )


def _dim(
    dimension: str,
    acuity: Acuity,
    confidence: float = 0.9,
) -> DimensionEvidence:
    return DimensionEvidence(
        dimension=dimension,
        acuity=acuity,
        assertions=[_assertion(confidence=confidence)],
    )


def _goal(
    goal_id: str,
    status: GoalStatus,
    confidence: float = 0.9,
) -> GoalEvidence:
    return GoalEvidence(
        goal_id=goal_id,
        status=status,
        assertions=[_assertion(confidence=confidence)],
    )


def _evidence(
    dims: list[DimensionEvidence],
    goals: list[GoalEvidence],
    case_id: str = "TEST-001",
) -> ExtractedEvidence:
    return ExtractedEvidence(case_id=case_id, dimensions=dims, goals=goals)


# =====================================================================
# Step 1: Fatal procedural failure → DENY
# =====================================================================


class TestFatalGateDeny:
    def test_fatal_gate_denies_immediately(self):
        """CSA-005 pattern: good clinical evidence, fatal procedural failure."""
        gates = [_gate_pass(), _gate_fatal_fail()]
        evidence = _evidence(
            dims=[_dim("d5_relapse_potential", Acuity.HIGH, 0.95)],
            goals=[_goal("G1", GoalStatus.MET)],
        )
        result = score_case("CSA-005", gates, evidence)
        assert result.decision == Decision.DENY
        assert result.has_fatal_gate is True
        assert result.credible_high_dimensions == []

    def test_fatal_gate_skips_clinical_layer(self):
        """Rationale should mention the procedural failure, not clinical evidence."""
        gates = [_gate_fatal_fail()]
        evidence = _evidence(
            dims=[_dim("d6_recovery_environment", Acuity.HIGH, 1.0)],
            goals=[_goal("G1", GoalStatus.REGRESSED)],
        )
        result = score_case("TEST", gates, evidence)
        assert result.decision == Decision.DENY
        assert any("Fatal procedural failure" in r for r in result.rationale)
        assert not any("high acuity" in r for r in result.rationale)

    def test_multiple_fatal_gates(self):
        gates = [_gate_fatal_fail("gate_a"), _gate_fatal_fail("gate_b")]
        result = score_case("TEST", gates, None)
        assert result.decision == Decision.DENY
        assert len([r for r in result.rationale if "Fatal" in r]) == 2


# =====================================================================
# Step 2: Credible high-acuity dimension → APPROVE
# =====================================================================


class TestApprove:
    def test_csa001_pattern(self):
        """High D5 and D6 with good confidence, goals partially met."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[
                _dim("d1_withdrawal", Acuity.LOW, 0.95),
                _dim("d5_relapse_potential", Acuity.HIGH, 0.93),
                _dim("d6_recovery_environment", Acuity.HIGH, 0.94),
            ],
            goals=[
                _goal("G1", GoalStatus.PARTIALLY_MET),
                _goal("G2", GoalStatus.PARTIALLY_MET),
                _goal("G3", GoalStatus.NOT_MET),
            ],
        )
        result = score_case("CSA-001", gates, evidence)
        assert result.decision == Decision.APPROVE
        assert "d5_relapse_potential" in result.credible_high_dimensions
        assert "d6_recovery_environment" in result.credible_high_dimensions

    def test_csa004_pattern(self):
        """Bereavement: D3, D5, D6 high, goals regressed."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[
                _dim("d3_emotional_behavioral", Acuity.HIGH, 0.94),
                _dim("d5_relapse_potential", Acuity.HIGH, 0.98),
                _dim("d6_recovery_environment", Acuity.HIGH, 1.0),
            ],
            goals=[
                _goal("G1", GoalStatus.REGRESSED),
                _goal("G2", GoalStatus.REGRESSED),
                _goal("G3", GoalStatus.REGRESSED),
            ],
        )
        result = score_case("CSA-004", gates, evidence)
        assert result.decision == Decision.APPROVE
        assert len(result.credible_high_dimensions) == 3

    def test_single_credible_high_dim_suffices(self):
        """CSA-007 pattern: only D6 is high."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[
                _dim("d1_withdrawal", Acuity.LOW, 0.90),
                _dim("d5_relapse_potential", Acuity.MODERATE, 0.91),
                _dim("d6_recovery_environment", Acuity.HIGH, 0.94),
            ],
            goals=[_goal("G1", GoalStatus.PARTIALLY_MET)],
        )
        result = score_case("CSA-007", gates, evidence)
        assert result.decision == Decision.APPROVE
        assert result.credible_high_dimensions == ["d6_recovery_environment"]

    def test_high_acuity_below_confidence_floor_does_not_approve(self):
        """High acuity at 0.30 confidence (CSA-003 D5 pattern) → not credible."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[_dim("d5_relapse_potential", Acuity.HIGH, 0.30)],
            goals=[_goal("G1", GoalStatus.UNABLE_TO_ASSESS, 0.20)],
        )
        result = score_case("TEST", gates, evidence)
        assert result.decision != Decision.APPROVE
        assert result.credible_high_dimensions == []

    def test_correctable_gate_does_not_block_approve(self):
        """CSA-007 pattern: correctable failure + clinical approval."""
        gates = [_gate_pass(), _gate_correctable_fail()]
        evidence = _evidence(
            dims=[_dim("d6_recovery_environment", Acuity.HIGH, 0.94)],
            goals=[_goal("G1", GoalStatus.PARTIALLY_MET)],
        )
        result = score_case("CSA-007", gates, evidence)
        assert result.decision == Decision.APPROVE
        assert any("Correctable" in r for r in result.rationale)


# =====================================================================
# Step 3: Real documentation + goal tracking → DENY_WITH_TRANSITION
# =====================================================================


class TestDenyWithTransition:
    def test_csa002_pattern(self):
        """All goals met, no high dims, good documentation → transition."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[
                _dim("d1_withdrawal", Acuity.LOW, 0.90),
                _dim("d5_relapse_potential", Acuity.MODERATE, 0.92),
                _dim("d6_recovery_environment", Acuity.LOW, 0.90),
            ],
            goals=[
                _goal("G1", GoalStatus.MET),
                _goal("G2", GoalStatus.MET),
                _goal("G3", GoalStatus.MET),
            ],
        )
        result = score_case("CSA-002", gates, evidence)
        assert result.decision == Decision.DENY_WITH_TRANSITION
        assert any("UT-7-19-4-3-a" in r for r in result.rationale)

    def test_credible_dims_but_no_high_with_goal_tracking(self):
        """Moderate acuity, good confidence, goals tracked → transition."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[_dim("d5_relapse_potential", Acuity.MODERATE, 0.85)],
            goals=[_goal("G1", GoalStatus.PARTIALLY_MET)],
        )
        result = score_case("TEST", gates, evidence)
        assert result.decision == Decision.DENY_WITH_TRANSITION

    def test_credible_dims_but_no_goal_tracking_denies(self):
        """Credible dimension data but all goals unable_to_assess → hard DENY."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[_dim("d1_withdrawal", Acuity.LOW, 0.80)],
            goals=[
                _goal("G1", GoalStatus.UNABLE_TO_ASSESS, 0.30),
                _goal("G2", GoalStatus.UNABLE_TO_ASSESS, 0.25),
            ],
        )
        result = score_case("TEST", gates, evidence)
        assert result.decision == Decision.DENY
        assert any("unable_to_assess" in r for r in result.rationale)


# =====================================================================
# Step 4: Insufficient documentation → DENY
# =====================================================================


class TestHardDeny:
    def test_csa003_pattern(self):
        """All dims below confidence floor, all goals unable_to_assess."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[
                _dim("d1_withdrawal", Acuity.LOW, 0.50),
                _dim("d3_emotional_behavioral", Acuity.MODERATE, 0.40),
                _dim("d5_relapse_potential", Acuity.HIGH, 0.30),
                _dim("d6_recovery_environment", Acuity.HIGH, 0.30),
            ],
            goals=[
                _goal("G1", GoalStatus.UNABLE_TO_ASSESS, 0.30),
                _goal("G2", GoalStatus.UNABLE_TO_ASSESS, 0.25),
                _goal("G3", GoalStatus.UNABLE_TO_ASSESS, 0.20),
            ],
        )
        result = score_case("CSA-003", gates, evidence)
        assert result.decision == Decision.DENY
        assert result.has_fatal_gate is False
        assert result.credible_high_dimensions == []

    def test_no_evidence_at_all(self):
        gates = [_gate_pass()]
        result = score_case("TEST", gates, None)
        assert result.decision == Decision.DENY
        assert any("No extracted evidence" in r for r in result.rationale)

    def test_empty_dimensions_and_goals(self):
        gates = [_gate_pass()]
        evidence = _evidence(dims=[], goals=[])
        result = score_case("TEST", gates, evidence)
        assert result.decision == Decision.DENY


# =====================================================================
# Confidence floor behavior
# =====================================================================


class TestConfidenceFloor:
    def test_exactly_at_floor_counts(self):
        """Confidence == 0.6 should clear the floor."""
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[_dim("d5_relapse_potential", Acuity.HIGH, CONFIDENCE_FLOOR)],
            goals=[_goal("G1", GoalStatus.NOT_MET)],
        )
        result = score_case("TEST", gates, evidence)
        assert result.decision == Decision.APPROVE

    def test_just_below_floor_does_not_count(self):
        gates = [_gate_pass()]
        evidence = _evidence(
            dims=[_dim("d5_relapse_potential", Acuity.HIGH, 0.59)],
            goals=[_goal("G1", GoalStatus.NOT_MET)],
        )
        result = score_case("TEST", gates, evidence)
        assert result.decision != Decision.APPROVE

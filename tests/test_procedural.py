from datetime import date

import pytest

from src.models import Episode, Facility, Prescriber, Severity
from src.procedural import check_submission_window


def _make_episode(**overrides) -> Episode:
    defaults = dict(
        member_id="UT-000000",
        member_age=34,
        asam_level_requested="3.5",
        intake_date=date(2026, 6, 8),
        days_elapsed_at_request=28,
        first_requested_dos=date(2026, 7, 6),
        days_requested=14,
        submission_date=date(2026, 7, 3),
        last_reassessment_date=date(2026, 7, 5),
        prior_reassessment_date=date(2026, 6, 21),
        prescriber=Prescriber(
            name="M. Reyes",
            credential="LCSW",
            license_number="UT-7741082",
        ),
        facility=Facility(
            name="Diamond Recovery Center",
            licensed_r501_19=True,
            bed_count=24,
            is_imd=True,
            accreditation="CARF",
        ),
    )
    defaults.update(overrides)
    return Episode(**defaults)


# --- Passing cases ---


class TestSubmissionWindowPass:
    def test_csa001_on_window_boundary_start(self):
        """CSA-001: submitted=07-03, first_dos=07-06. Window=[07-03..07-06]."""
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 6),
            submission_date=date(2026, 7, 3),
        )
        result = check_submission_window(ep)
        assert result.passed is True
        assert result.gate_id == "submission_window"

    def test_csa002_within_window(self):
        """CSA-002: submitted=07-02, first_dos=07-05. Window=[07-02..07-05]."""
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 5),
            submission_date=date(2026, 7, 2),
        )
        result = check_submission_window(ep)
        assert result.passed is True

    def test_submitted_on_first_dos(self):
        """Submitted exactly on first_requested_dos — latest possible."""
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 6),
            submission_date=date(2026, 7, 6),
        )
        result = check_submission_window(ep)
        assert result.passed is True

    def test_submitted_one_day_before(self):
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 6),
            submission_date=date(2026, 7, 5),
        )
        result = check_submission_window(ep)
        assert result.passed is True

    def test_submitted_two_days_before(self):
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 6),
            submission_date=date(2026, 7, 4),
        )
        result = check_submission_window(ep)
        assert result.passed is True


# --- Failing: too early ---


class TestSubmissionWindowTooEarly:
    def test_csa005_eight_days_early(self):
        """CSA-005: submitted=06-29, first_dos=07-07. Window=[07-04..07-07]. Fatal."""
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 7),
            submission_date=date(2026, 6, 29),
        )
        result = check_submission_window(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL
        assert "UT-7-19-4-2-b" in result.citation
        assert result.fix is None

    def test_one_day_too_early(self):
        """Submitted one day before the window opens."""
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 6),
            submission_date=date(2026, 7, 2),
        )
        result = check_submission_window(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL

    def test_far_too_early(self):
        """Submitted weeks before the window."""
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 6),
            submission_date=date(2026, 6, 15),
        )
        result = check_submission_window(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL


# --- Failing: too late ---


class TestSubmissionWindowTooLate:
    def test_one_day_late(self):
        """Submitted one day after first_requested_dos."""
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 6),
            submission_date=date(2026, 7, 7),
        )
        result = check_submission_window(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL
        assert "UT-7-19-4-2-a" in result.citation
        assert result.fix is None

    def test_several_days_late(self):
        ep = _make_episode(
            first_requested_dos=date(2026, 7, 6),
            submission_date=date(2026, 7, 10),
        )
        result = check_submission_window(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL


# --- Gate result shape ---


class TestGateResultShape:
    def test_pass_has_all_fields(self):
        ep = _make_episode()
        result = check_submission_window(ep)
        assert result.gate_id == "submission_window"
        assert result.passed is True
        assert result.severity == Severity.FATAL
        assert "UT-7-19-4-2" in result.citation
        assert result.message
        assert result.fix is None

    def test_fail_has_all_fields(self):
        ep = _make_episode(submission_date=date(2026, 6, 20))
        result = check_submission_window(ep)
        assert result.gate_id == "submission_window"
        assert result.passed is False
        assert result.severity == Severity.FATAL
        assert result.citation
        assert result.message
        assert result.fix is None  # fatal = no fix


# --- Edge: reads first_requested_dos, never derives ---


class TestReadsFirstRequestedDOS:
    def test_uses_episode_field_not_computed(self):
        """Ensure the gate reads first_requested_dos from the episode,
        not from intake_date + days_elapsed_at_request. These differ
        when an authorization ended early or covered an absence."""
        ep = _make_episode(
            intake_date=date(2026, 6, 8),
            days_elapsed_at_request=28,
            # If derived: 06-08 + 28 = 07-06. But actual first_dos is 07-10.
            first_requested_dos=date(2026, 7, 10),
            submission_date=date(2026, 7, 7),
        )
        result = check_submission_window(ep)
        # Window for 07-10: [07-07..07-10]. Submitted 07-07 = pass.
        # If it derived 07-06: window=[07-03..07-06]. 07-07 = too late = fail.
        assert result.passed is True

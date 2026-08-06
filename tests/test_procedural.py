from datetime import date

import pytest

from src.models import Episode, Facility, Prescriber, Severity
from src.procedural import (
    check_age_eligibility,
    check_facility_licensing,
    check_pa_duration_cap,
    check_reassessment_presence,
    check_reassessment_timeliness,
    check_submission_window,
)


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
        has_reassessment=True,
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


# =====================================================================
# PA Duration Cap — UT-7-19-4-a / UT-7-19-4-b
# =====================================================================


class TestPaDurationCapAdolescent:
    def test_csa007_over_cap(self):
        """CSA-007: age 16, requested 45 days. Adolescent cap is 30. Correctable."""
        ep = _make_episode(member_age=16, days_requested=45)
        result = check_pa_duration_cap(ep)
        assert result.passed is False
        assert result.severity == Severity.CORRECTABLE
        assert result.citation == "UT-7-19-4-a"
        assert result.fix is not None
        assert "30" in result.fix

    def test_at_cap(self):
        """Exactly 30 days for an adolescent — should pass."""
        ep = _make_episode(member_age=17, days_requested=30)
        result = check_pa_duration_cap(ep)
        assert result.passed is True
        assert result.fix is None

    def test_under_cap(self):
        ep = _make_episode(member_age=14, days_requested=14)
        result = check_pa_duration_cap(ep)
        assert result.passed is True

    def test_age_18_is_adolescent(self):
        """18 is the upper bound of adolescent — 30-day cap, not 60."""
        ep = _make_episode(member_age=18, days_requested=31)
        result = check_pa_duration_cap(ep)
        assert result.passed is False
        assert result.citation == "UT-7-19-4-a"


class TestPaDurationCapAdult:
    def test_adult_within_cap(self):
        """CSA-001 pattern: age 34, 14 days requested. Well under 60."""
        ep = _make_episode(member_age=34, days_requested=14)
        result = check_pa_duration_cap(ep)
        assert result.passed is True
        assert result.citation == "UT-7-19-4-b"
        assert result.fix is None

    def test_adult_at_cap(self):
        ep = _make_episode(member_age=45, days_requested=60)
        result = check_pa_duration_cap(ep)
        assert result.passed is True

    def test_adult_over_cap(self):
        ep = _make_episode(member_age=45, days_requested=61)
        result = check_pa_duration_cap(ep)
        assert result.passed is False
        assert result.severity == Severity.CORRECTABLE
        assert result.citation == "UT-7-19-4-b"
        assert result.fix is not None
        assert "60" in result.fix

    def test_age_19_is_adult(self):
        """19 is the lower bound of adult — 60-day cap, not 30."""
        ep = _make_episode(member_age=19, days_requested=31)
        result = check_pa_duration_cap(ep)
        assert result.passed is True
        assert result.citation == "UT-7-19-4-b"


class TestPaDurationCapShape:
    def test_fail_has_fix(self):
        """Correctable failures must always populate fix."""
        ep = _make_episode(member_age=16, days_requested=45)
        result = check_pa_duration_cap(ep)
        assert result.fix is not None

    def test_pass_has_no_fix(self):
        """Passing gates never have a fix."""
        ep = _make_episode(member_age=34, days_requested=14)
        result = check_pa_duration_cap(ep)
        assert result.fix is None

    def test_gate_id(self):
        ep = _make_episode()
        result = check_pa_duration_cap(ep)
        assert result.gate_id == "pa_duration_cap"


# =====================================================================
# Reassessment Timeliness — UT-7-19-4-2-d
# =====================================================================


class TestReassessmentTimelinessPass:
    """All 7 real cases pass this gate."""

    def test_csa001(self):
        """lrd=07-05, frd=07-06. One day before."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 5),
            first_requested_dos=date(2026, 7, 6),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is True

    def test_csa002(self):
        """lrd=07-04, frd=07-05."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 4),
            first_requested_dos=date(2026, 7, 5),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is True

    def test_csa003(self):
        """lrd=07-07, frd=07-08."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 7),
            first_requested_dos=date(2026, 7, 8),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is True

    def test_csa004(self):
        """lrd=07-04, frd=07-05."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 4),
            first_requested_dos=date(2026, 7, 5),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is True

    def test_csa005(self):
        """lrd=07-06, frd=07-07."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 6),
            first_requested_dos=date(2026, 7, 7),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is True

    def test_csa006(self):
        """lrd=07-06, frd=07-07."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 6),
            first_requested_dos=date(2026, 7, 7),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is True

    def test_csa007(self):
        """lrd=07-07, frd=07-08."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 7),
            first_requested_dos=date(2026, 7, 8),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is True

    def test_same_day(self):
        """Reassessment on the exact first_requested_dos — boundary, should pass."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 6),
            first_requested_dos=date(2026, 7, 6),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is True


class TestReassessmentTimelinessFail:
    def test_one_day_late(self):
        """Reassessment performed one day after frd."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 7),
            first_requested_dos=date(2026, 7, 6),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL
        assert result.citation == "UT-7-19-4-2-d"
        assert result.fix is None

    def test_several_days_late(self):
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 12),
            first_requested_dos=date(2026, 7, 6),
        )
        result = check_reassessment_timeliness(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL


class TestReassessmentTimelinessShape:
    def test_gate_id(self):
        ep = _make_episode()
        result = check_reassessment_timeliness(ep)
        assert result.gate_id == "reassessment_timeliness"

    def test_fatal_no_fix_on_pass(self):
        ep = _make_episode()
        result = check_reassessment_timeliness(ep)
        assert result.severity == Severity.FATAL
        assert result.fix is None

    def test_fatal_no_fix_on_fail(self):
        """Fatal gates never have a fix — can't redo a late reassessment."""
        ep = _make_episode(
            last_reassessment_date=date(2026, 7, 10),
            first_requested_dos=date(2026, 7, 6),
        )
        result = check_reassessment_timeliness(ep)
        assert result.severity == Severity.FATAL
        assert result.fix is None


# =====================================================================
# Age Eligibility — UT-7-19-3-b
# =====================================================================


class TestAgeEligibilityPass:
    def test_csa007_youngest_case(self):
        """CSA-007: age 16. Youngest in the set, well above 12."""
        ep = _make_episode(member_age=16)
        result = check_age_eligibility(ep)
        assert result.passed is True

    def test_age_12_boundary(self):
        """Exactly 12 — minimum eligible age."""
        ep = _make_episode(member_age=12)
        result = check_age_eligibility(ep)
        assert result.passed is True

    def test_adult(self):
        ep = _make_episode(member_age=34)
        result = check_age_eligibility(ep)
        assert result.passed is True


class TestAgeEligibilityFail:
    def test_age_11_boundary(self):
        """11 — one year below the cutoff."""
        ep = _make_episode(member_age=11)
        result = check_age_eligibility(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL
        assert result.citation == "UT-7-19-3-b"
        assert result.fix is None

    def test_young_child(self):
        ep = _make_episode(member_age=5)
        result = check_age_eligibility(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL


class TestAgeEligibilityShape:
    def test_gate_id(self):
        ep = _make_episode()
        result = check_age_eligibility(ep)
        assert result.gate_id == "age_eligibility"

    def test_fatal_no_fix(self):
        ep = _make_episode(member_age=11)
        result = check_age_eligibility(ep)
        assert result.fix is None


# =====================================================================
# Facility Licensing — UT-7-19-2-a
# =====================================================================


class TestFacilityLicensingPass:
    def test_licensed_facility(self):
        """All 7 cases use Diamond Recovery Center, licensed=True."""
        ep = _make_episode()
        result = check_facility_licensing(ep)
        assert result.passed is True
        assert result.citation == "UT-7-19-2-a"


class TestFacilityLicensingFail:
    def test_unlicensed_facility(self):
        ep = _make_episode(
            facility=Facility(
                name="Unlicensed House",
                licensed_r501_19=False,
                bed_count=10,
                is_imd=False,
                accreditation="None",
            ),
        )
        result = check_facility_licensing(ep)
        assert result.passed is False
        assert result.severity == Severity.FATAL
        assert result.citation == "UT-7-19-2-a"
        assert result.fix is None
        assert "Unlicensed House" in result.message


class TestFacilityLicensingShape:
    def test_gate_id(self):
        ep = _make_episode()
        result = check_facility_licensing(ep)
        assert result.gate_id == "facility_licensing"

    def test_fatal_no_fix(self):
        ep = _make_episode(
            facility=Facility(
                name="Bad Facility",
                licensed_r501_19=False,
                bed_count=5,
                is_imd=False,
                accreditation="None",
            ),
        )
        result = check_facility_licensing(ep)
        assert result.fix is None


# =====================================================================
# Reassessment Presence — UT-7-19-4-2-c
# =====================================================================


class TestReassessmentPresencePass:
    def test_reassessment_included(self):
        """All 7 cases include a reassessment."""
        ep = _make_episode()
        result = check_reassessment_presence(ep)
        assert result.passed is True
        assert result.fix is None


class TestReassessmentPresenceFail:
    def test_reassessment_missing(self):
        ep = _make_episode(has_reassessment=False)
        result = check_reassessment_presence(ep)
        assert result.passed is False
        assert result.severity == Severity.CORRECTABLE
        assert result.citation == "UT-7-19-4-2-c"
        assert result.fix is not None


class TestReassessmentPresenceShape:
    def test_gate_id(self):
        ep = _make_episode()
        result = check_reassessment_presence(ep)
        assert result.gate_id == "reassessment_presence"

    def test_correctable_has_fix_on_fail(self):
        ep = _make_episode(has_reassessment=False)
        result = check_reassessment_presence(ep)
        assert result.severity == Severity.CORRECTABLE
        assert result.fix is not None

    def test_no_fix_on_pass(self):
        ep = _make_episode(has_reassessment=True)
        result = check_reassessment_presence(ep)
        assert result.fix is None

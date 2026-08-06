from __future__ import annotations

from datetime import timedelta

from src.models import Episode, GateResult, Severity


_ADOLESCENT_AGE_MAX = 18
_ADOLESCENT_DAYS_CAP = 30
_ADULT_DAYS_CAP = 60

def check_reassessment_presence(episode: Episode) -> GateResult:
    """UT-7-19-4-2-c: A continued-stay PA request must include a completed reassessment and treatment plan review using ASAM criteria.
    
    SEVERITY: Correctable, as a reassessment that has been done can be retrieved and attached. 
    """
    if not episode.has_reassessment:
        return GateResult(
            gate_id="reassessment_presence",
            passed=False,
            severity=Severity.CORRECTABLE,
            citation="UT-7-19-4-2-c",
            message="Continued-stay PA request does not include a reassessment.",
            fix="Resubmit with completed reassessment and treatment plan review using ASAM criteria.",
        )

    return GateResult(
        gate_id="reassessment_presence",
        passed=True,
        severity=Severity.CORRECTABLE,
        citation="UT-7-19-4-2-c",
        message="Reassessment included with submission.",
    )

def check_facility_licensing(episode: Episode) -> GateResult:
    """UT-7-19-2-a: Providers must be licensed by the DHHS Office of Licensing and meet the requirements in Utah Administrative Code R501-19.
    
    Severity is FATAL: unlicensed facilities cannot practice addiction rehabilitation/behavioral health treatment. 
    """

    if not episode.facility.licensed_r501_19:
        return GateResult(
            gate_id="facility_licensing",
            passed=False,
            severity=Severity.FATAL,
            citation="UT-7-19-2-a",
            message=f"Facility {episode.facility.name} is not licensed under R501-19.",
        )

    return GateResult(
        gate_id="facility_licensing",
        passed=True,
        severity=Severity.FATAL,
        citation="UT-7-19-2-a",
        message=f"Facility {episode.facility.name} is licensed under R501-19.",
    )

def check_age_eligibility(episode: Episode) -> GateResult:
    """UT-7-19-3-b: SUD residential treatment is limited to members age 12 and older.
    
    Severity is FATAL: members under age 12 are ineligible.
    """

    age = episode.member_age

    if age < 12:
        return GateResult(
            gate_id="age_eligibility",
            passed=False,
            severity=Severity.FATAL,
            citation="UT-7-19-3-b",
            message=f"Members age is {age}, so they are ineligible for services."
        )

    return GateResult(
        gate_id="age_eligibility",
        passed=True,
        severity=Severity.FATAL,
        citation="UT-7-19-3-b",
        message=f"Members age is {age}, so they are eligible for services."
    )


def check_reassessment_timeliness(episode: Episode) -> GateResult:
    """UT-7-19-4-2-d: Last reassessment date must be no later than first requested date of service.

    Severity is FATAL: you cannot rectify a past discrepancy in the order,
    so this will result in rejection.
    """
    lrd = episode.last_reassessment_date
    frd = episode.first_requested_dos

    if lrd > frd:
        return GateResult(
            gate_id="reassessment_timeliness",
            passed=False,
            severity=Severity.FATAL,
            citation="UT-7-19-4-2-d",
            message=(
                f"Reassessment performed {lrd.isoformat()}, after "
                f"first requested DOS {frd.isoformat()}."
            ),
        )

    return GateResult(
        gate_id="reassessment_timeliness",
        passed=True,
        severity=Severity.FATAL,
        citation="UT-7-19-4-2-d",
        message=(
            f"Reassessment performed {lrd.isoformat()}, on or before "
            f"first requested DOS {frd.isoformat()}."
        ),
    )



def check_pa_duration_cap(episode: Episode) -> GateResult:
    """UT-7-19-4-a/b: PA duration cap by age bracket.

    Adolescent (12-18): up to 30 calendar days per request.
    Adult (19+): up to 60 calendar days per request.

    Severity is CORRECTABLE: an over-length request has a specific fix
    (resubmit at the cap).
    """
    if episode.member_age <= _ADOLESCENT_AGE_MAX:
        cap = _ADOLESCENT_DAYS_CAP
        citation = "UT-7-19-4-a"
        bracket = "adolescent (age 12-18)"
    else:
        cap = _ADULT_DAYS_CAP
        citation = "UT-7-19-4-b"
        bracket = "adult (age 19+)"

    if episode.days_requested > cap:
        return GateResult(
            gate_id="pa_duration_cap",
            passed=False,
            severity=Severity.CORRECTABLE,
            citation=citation,
            message=(
                f"Requested {episode.days_requested} days for "
                f"{bracket} member (age {episode.member_age}). "
                f"Maximum is {cap} calendar days per request."
            ),
            fix=f"Resubmit with {cap} days or fewer.",
        )

    return GateResult(
        gate_id="pa_duration_cap",
        passed=True,
        severity=Severity.CORRECTABLE,
        citation=citation,
        message=(
            f"Requested {episode.days_requested} days for "
            f"{bracket} member (age {episode.member_age}). "
            f"Within {cap}-day cap."
        ),
    )


def check_submission_window(episode: Episode) -> GateResult:
    """UT-7-19-4-2: Continued stay submission window.

    The PA request must be submitted:
      - no later than the first requested date of service (UT-7-19-4-2-a)
      - no earlier than four calendar days of, and including, the first
        requested date of service (UT-7-19-4-2-b)

    These two rules define a single four-calendar-day window ending on
    first_requested_dos. Severity is FATAL: once the window has passed
    there is no correction.

    Reads first_requested_dos off the episode record. Never derives it.
    """
    first_dos = episode.first_requested_dos
    submitted = episode.submission_date

    # Window: [first_dos - 3 days, first_dos] inclusive
    # "four calendar days of, and including, the first requested date of service"
    window_start = first_dos - timedelta(days=3)
    window_end = first_dos

    if submitted > window_end:
        return GateResult(
            gate_id="submission_window",
            passed=False,
            severity=Severity.FATAL,
            citation="UT-7-19-4-2-a",
            message=(
                f"Submission date {submitted.isoformat()} is after "
                f"first requested DOS {first_dos.isoformat()}. "
                f"Continued-stay PA must be submitted no later than "
                f"the first requested date of service."
            ),
        )

    if submitted < window_start:
        return GateResult(
            gate_id="submission_window",
            passed=False,
            severity=Severity.FATAL,
            citation="UT-7-19-4-2-b",
            message=(
                f"Submission date {submitted.isoformat()} is before "
                f"the four-calendar-day window starting "
                f"{window_start.isoformat()}. Continued-stay PA must "
                f"be submitted no earlier than four calendar days of, "
                f"and including, the first requested date of service."
            ),
        )

    return GateResult(
        gate_id="submission_window",
        passed=True,
        severity=Severity.FATAL,
        citation="UT-7-19-4-2-a,UT-7-19-4-2-b",
        message=(
            f"Submission date {submitted.isoformat()} is within the "
            f"four-calendar-day window "
            f"[{window_start.isoformat()}, {window_end.isoformat()}]."
        ),
    )

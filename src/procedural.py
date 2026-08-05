from __future__ import annotations

from datetime import timedelta

from src.models import Episode, GateResult, Severity


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

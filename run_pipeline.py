"""Run the full pipeline: procedural gates → extraction → scoring."""
from __future__ import annotations

import asyncio
import json
from datetime import date

from dotenv import load_dotenv

load_dotenv()

import anthropic

from src.extraction import extract_evidence
from src.models import Episode, Facility, GateResult, Prescriber
from src.procedural import (
    check_age_eligibility,
    check_facility_licensing,
    check_pa_duration_cap,
    check_reassessment_presence,
    check_reassessment_timeliness,
    check_submission_window,
)
from src.scoring import score_case


ALL_GATES = [
    check_age_eligibility,
    check_facility_licensing,
    check_pa_duration_cap,
    check_reassessment_presence,
    check_reassessment_timeliness,
    check_submission_window,
]


def build_episode(case: dict) -> Episode:
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


def run_procedural_gates(episode: Episode) -> list[GateResult]:
    return [gate(episode) for gate in ALL_GATES]


async def process_case(case: dict, client) -> dict:
    case_id = case["case_id"]

    # Step 1: Procedural gates
    episode = build_episode(case)
    gate_results = run_procedural_gates(episode)

    has_fatal = any(
        not g.passed and g.severity.value == "fatal" for g in gate_results
    )

    # Step 2: Extraction (skip if fatal)
    evidence = None
    if not has_fatal:
        try:
            evidence = await extract_evidence(case, client)
        except Exception as e:
            print(f"  {case_id}: Extraction error: {e}")

    # Step 3: Scoring
    result = score_case(case_id, gate_results, evidence)
    return {
        "case_id": case_id,
        "age": episode.member_age,
        "decision": result.decision.value,
        "has_fatal_gate": result.has_fatal_gate,
        "credible_high_dims": result.credible_high_dimensions,
        "rationale": result.rationale,
        "gate_failures": [
            {"gate": g.gate_id, "severity": g.severity.value, "message": g.message}
            for g in gate_results
            if not g.passed
        ],
    }


async def main():
    with open("cases-v1.json") as f:
        data = json.load(f)

    client = anthropic.AsyncAnthropic()
    cases = data["cases"]

    tasks = [process_case(case, client) for case in cases]
    results = await asyncio.gather(*tasks)

    print("\n" + "=" * 70)
    print("PIPELINE RESULTS")
    print("=" * 70)

    for r in results:
        print(f"\n{r['case_id']} (age {r['age']})")
        print(f"  Decision: {r['decision']}")

        if r["gate_failures"]:
            for gf in r["gate_failures"]:
                print(f"  Gate failure [{gf['severity']}]: {gf['message']}")

        if r["credible_high_dims"]:
            print(f"  Credible high dimensions: {', '.join(r['credible_high_dims'])}")

        for line in r["rationale"]:
            print(f"  > {line}")

    # Save full results
    with open("pipeline_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n\nFull results saved to pipeline_results.json")


if __name__ == "__main__":
    asyncio.run(main())

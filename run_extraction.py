"""Run the extraction layer against all 7 cases and print results."""
from __future__ import annotations

import asyncio
import json

from dotenv import load_dotenv

load_dotenv()

import anthropic

from src.extraction import extract_evidence


async def main():
    with open("cases-v1.json") as f:
        data = json.load(f)

    client = anthropic.AsyncAnthropic()
    cases = data["cases"]

    tasks = [extract_evidence(case, client) for case in cases]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for case, result in zip(cases, results):
        print(f"\n{'='*60}")
        print(f"Case: {case['case_id']}")
        print(f"{'='*60}")

        if isinstance(result, Exception):
            print(f"ERROR: {result}")
            continue

        print("\nDimensions:")
        for dim in result.dimensions:
            avg_conf = (
                sum(a.confidence for a in dim.assertions) / len(dim.assertions)
                if dim.assertions
                else 0.0
            )
            conflicting = any(a.conflicting for a in dim.assertions)
            unquantified = any(a.unquantified for a in dim.assertions)
            flags = []
            if conflicting:
                flags.append("CONFLICTING")
            if unquantified:
                flags.append("UNQUANTIFIED")
            flag_str = f" [{', '.join(flags)}]" if flags else ""
            print(
                f"  {dim.dimension}: {dim.acuity.value} "
                f"(avg confidence: {avg_conf:.2f}){flag_str}"
            )

        print("\nGoals:")
        for goal in result.goals:
            avg_conf = (
                sum(a.confidence for a in goal.assertions) / len(goal.assertions)
                if goal.assertions
                else 0.0
            )
            print(
                f"  {goal.goal_id}: {goal.status.value} "
                f"(avg confidence: {avg_conf:.2f})"
            )

    # Save full results for inspection
    output = []
    for case, result in zip(cases, results):
        if not isinstance(result, Exception):
            output.append(result.model_dump())
    with open("extraction_results.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n\nFull results saved to extraction_results.json")


if __name__ == "__main__":
    asyncio.run(main())

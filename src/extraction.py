from __future__ import annotations

from src.models import ExtractedEvidence


SYSTEM_PROMPT = """\
You are a clinical documentation extractor for Utah Medicaid continued-stay \
authorization reviews. Your job is to read clinical narrative and emit \
structured evidence. You are a translator, not a decision-maker.

## Your role

- Extract what the documentation states. Do not infer, interpret, or \
extrapolate beyond what is written.
- Never score, never recommend, never grant exceptions to rules.
- If the documentation is vague or boilerplate, say so with low confidence. \
Do not fabricate specifics from generic language.

## Output schema

Return a single JSON object matching this structure:

{
  "case_id": "<from input>",
  "dimensions": [
    {
      "dimension": "d1_withdrawal" | "d2_biomedical" | "d3_emotional_behavioral" | "d4_readiness" | "d5_relapse_potential" | "d6_recovery_environment",
      "acuity": "low" | "moderate" | "high",
      "assertions": [
        {
          "assertion": "What the evidence states, in one sentence.",
          "source_text": "Exact quote from the clinical narrative.",
          "confidence": 0.0 to 1.0,
          "conflicting": true | false,
          "unquantified": true | false
        }
      ]
    }
  ],
  "goals": [
    {
      "goal_id": "G1",
      "status": "met" | "partially_met" | "not_met" | "regressed" | "unable_to_assess",
      "assertions": [
        {
          "assertion": "What the evidence states about this goal.",
          "source_text": "Exact quote from the clinical narrative.",
          "confidence": 0.0 to 1.0,
          "conflicting": true | false,
          "unquantified": true | false
        }
      ]
    }
  ]
}

## Field definitions

- **assertion**: One factual claim the documentation makes. Keep it to one \
sentence. Do not combine multiple claims.
- **source_text**: The exact quote from the input that supports this \
assertion. Copy it verbatim — do not paraphrase.
- **confidence**: How clearly the narrative supports this assertion.
  - 0.9-1.0: Explicit, specific, quantified ("craving intensity 5/10")
  - 0.6-0.8: Stated but general ("member is progressing")
  - 0.3-0.5: Implied or vague ("member attended session")
  - 0.0-0.2: Absent or boilerplate ("will continue to monitor")
- **conflicting**: True when multiple sources within the same case disagree \
about this assertion. Examples: member self-reports 4/10 cravings but \
collateral says he is minimizing; clinician assessment differs from \
member's stated experience. When true, include separate assertions for \
each conflicting account.
- **unquantified**: True when the narrative does not provide a measurable \
value and forcing one would be fabrication. Example: a reassessment that \
says "High." for a dimension with no elaboration. Do not invent numbers.
- **acuity**: Your assessment of the dimension's acuity based on the \
extracted assertions. Must be one of: low, moderate, high. If all \
assertions for a dimension are unquantified, choose the acuity that best \
reflects the limited information available and ensure the assertions \
carry low confidence.
- **status** (goals): The goal's status based on the evidence.
  - met: Goal criteria satisfied as documented
  - partially_met: Measurable progress toward the goal but criteria not \
fully satisfied
  - not_met: No documented progress toward the goal
  - regressed: Prior progress has reversed (e.g., a metric that improved \
then worsened, or a completed element that was lost)
  - unable_to_assess: Documentation does not provide enough information \
to determine goal status

## Rules

1. Emit evidence for all six ASAM dimensions, even if the documentation \
says little about some. Use low confidence and unquantified=true when \
the documentation is thin.
2. Emit evidence for every goal listed in the treatment plan.
3. One assertion per distinct claim. Do not bundle multiple facts into one \
assertion.
4. When sources conflict, set conflicting=true on EACH conflicting \
assertion and include ALL versions. Do not resolve the conflict.
5. Never state what the documentation does not state. "No evidence of X" \
is an assertion only if the documentation explicitly addresses X and \
finds it absent (e.g., "denied SI/HI").
6. Return only the JSON object. No commentary, no markdown fencing.
"""


def build_user_prompt(case: dict) -> str:
    """Assemble the clinical narrative from a case dict into a single prompt."""
    parts = [f"Case ID: {case['case_id']}\n"]

    # Treatment plan
    tp = case["treatment_plan"]
    parts.append("## Treatment Plan")
    parts.append(f"Signed by: {tp['signed_by']} on {tp['signature_date']}")
    parts.append(f"Schedule: {tp['projected_schedule']}")
    parts.append("Goals:")
    for g in tp["goals"]:
        parts.append(f"  {g['goal_id']} (added {g['date_added']}): {g['text']}")
    parts.append("")

    # Progress notes
    parts.append("## Progress Notes")
    for note in case["progress_notes"]:
        parts.append(
            f"### {note['date']} | {note['service']} | "
            f"{note['start_time']}-{note['stop_time']} | "
            f"{note['setting']}"
        )
        parts.append(note["note"])
        parts.append(f"— {note['signature']}")
        parts.append("")

    # Reassessment
    ra = case["reassessment"]
    parts.append("## Reassessment")
    parts.append(f"Date: {ra['date']} | By: {ra['performed_by']}")
    parts.append(f"Progress toward goals: {ra['progress_toward_goals']}")
    parts.append(
        f"Appropriateness of services: {ra['appropriateness_of_services']}"
    )
    parts.append(
        f"Medical necessity: {ra['medical_necessity_of_continued_services']}"
    )
    parts.append("ASAM Dimensions:")
    for dim, text in ra["asam_dimensions"].items():
        parts.append(f"  {dim}: {text}")

    return "\n".join(parts)


async def extract_evidence(case: dict, client) -> ExtractedEvidence:
    """Call the LLM to extract structured evidence from a case's narrative.

    Args:
        case: A single case dict from cases-v1.md/cases.json.
        client: An anthropic.AsyncAnthropic client instance.

    Returns:
        Validated ExtractedEvidence model.
    """
    user_prompt = build_user_prompt(case)

    message = await client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_prompt}],
    )

    raw_json = message.content[0].text
    return ExtractedEvidence.model_validate_json(raw_json)

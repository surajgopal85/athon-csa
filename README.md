# CSA Scoring Engine

A prototype that predicts whether Utah Medicaid will approve a continued-stay authorization (CSA) for substance use disorder residential treatment at ASAM Level 3.5.

The bulk of the build time was spent understanding context, which led me to believe the important question not to be "does this patient need care", but rather, "will the payer pay." The gap between these 2 questions is where the value of this software lies.

## Why Utah Medicaid

Source: [Utah Medicaid Provider Manual — Behavioral Health Services (July 2026)](https://medicaid-documents.dhhs.utah.gov/Documents%2Fmanuals%2Fpdfs%2FMedicaid+Provider+Manuals%2FBehavioral+Health+Services%2FBehavioralHealthServices7-26.pdf)

Utah Medicaid's behavioral health manual is publicly available, rule-dense, and specific to payer *and* service line. It draws distinctions that generalized clinical tools miss: the 60-day episode cliff governs mental health residential, not SUD residential. The adolescent PA cap is 30 days, not 60. The submission window is four calendar days, not business days. An engine that keys only on payer without encoding these service-line distinctions will silently apply the wrong ruleset. TL;DR, this deterministic ruleset is specific to SUD residential scenarios.

Starting with one payer's one service line forces the architecture to be rule-specific from day one. The scoring logic cannot hide behind "generally applicable" because the rules are idiosyncratic and specific. Every gate traces to a chapter, page, and citation ID in the manual linked above.

## Quick start

```bash
# Clone and install
git clone https://github.com/surajgopal85/athon-csa.git && cd athon-csa
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install anthropic

# Set your Anthropic API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# Run the app
make serve
```

The app starts at `localhost:8000`. Startup takes ~60 seconds — it runs all 7 baseline cases through the extraction API on boot. Once loaded, the dashboard shows every case with a color-coded decision and the specific next action for the billing person.

Other commands:
- `make test` — run all 77 tests
- `make pipeline` — run the CLI pipeline without the server

### Upload your own cases

Go to `localhost:8000/upload` and upload a JSON file. The format guide is on the page. Upload a single case:

```json
{
  "case_id": "MY-CASE-001",
  "episode": { ... },
  "treatment_plan": { ... },
  "progress_notes": [ ... ],
  "reassessment": { ... }
}
```

Or multiple cases wrapped in `{"cases": [...]}`. Each case runs through the full pipeline (procedural gates, LLM extraction, clinical scoring) and appears on the dashboard immediately.

### Generating synthetic test cases

To stress-test the engine with new scenarios, use Claude or any LLM to generate cases matching the schema in `data/cases-v1.json`. A useful prompt:

> Generate a synthetic CSA case packet for a [describe the clinical scenario].
> The case must include: a case_id, an episode block with member_id, member_age,
> asam_level_requested ("3.5"), intake_date, days_elapsed_at_request,
> first_requested_dos, days_requested, submission_date, last_reassessment_date,
> prior_reassessment_date, prescriber (name, credential, license_number),
> and facility (name, licensed_r501_19, bed_count, is_imd, accreditation).
> Include a treatment_plan with 3 goals, 4 progress_notes referencing goals
> by ID with craving scores, and a reassessment with ASAM dimensions
> (2-3 sentences each). Use dates in June-July 2026.

The `data/stress-test-cases.json` file contains 25 synthetic cases across five categories (procedural failures, clinical approvals, transition denials, hard denials, edge cases) that can be uploaded directly.

## Architecture

Two buckets, and they never mix.

### 1. Procedural gates

Pure functions over episode metadata. No narrative input, no model calls, no I/O. Each gate reads structured fields (dates, ages, licensing flags) and emits pass/fail, a severity, and a citation.

Six gates implemented, 53 unit tests:

| Gate | Citation | Severity |
|------|----------|----------|
| Age eligibility | UT-7-19-3-b | Fatal |
| Facility licensing | UT-7-19-2-a | Fatal |
| PA duration cap | UT-7-19-4-a/b | Correctable |
| Reassessment presence | UT-7-19-4-2-c | Correctable |
| Reassessment timeliness | UT-7-19-4-2-d | Fatal |
| Submission window | UT-7-19-4-2-a/b | Fatal |

Severity determines what happens next. **Fatal** means the request is dead — there is no correction. **Correctable** means the request fails as submitted but a specific fix exists, and the engine tells the billing person what it is.

### 2. Clinical scoring

Rules over structured evidence extracted by the LLM. The LLM sits between the procedural and clinical layers and does exactly one job: read unstructured clinical narrative, emit structured evidence. Per ASAM dimension: the assertion, a pointer to the source text, a confidence score, plus `conflicting` and `unquantified` as required fields.

The LLM never scores and never grants exceptions to rules. Every decision is made by the rules layer so every score is traceable to specific extracted evidence.

### Three-state output

Not binary. The engine produces `APPROVE`, `DENY_WITH_TRANSITION`, or `DENY`.

- **APPROVE**: At least one ASAM dimension is high acuity with evidence above the confidence floor. Continued stay at this level is supported.
- **DENY_WITH_TRANSITION**: Clinical case doesn't support continued stay, but the documentation is substantive and goal tracking is present. Utah authorizes up to 14 calendar transition days (UT-7-19-4-3-a). The engine recommends this proactively rather than waiting for a denial.
- **DENY**: Fatal procedural failure, or documentation is too thin to justify any continued stay.

A fourth display state, **CORRECT AND RESUBMIT**, surfaces when the clinical case would approve but a correctable procedural failure blocks it. The billing person sees the imperative ("DO NOT SUBMIT AS WRITTEN") before anything else.

## How the scoring works

The scoring layer applies four rules in order:

1. **Any fatal gate failed?** Hard deny. Skip clinical evidence entirely.
2. **Credible high-acuity dimension?** Approve. A dimension counts as credible when its acuity is high AND its evidence clears a 0.6 confidence floor. Conflicting evidence (multiple sources disagree) is penalized — effective confidence is reduced by 40%, so contested dimensions need near-perfect raw confidence to drive an approval.
3. **Real documentation with goal tracking?** Transition. The clinician did their job — notes have substance, goals are tracked — but the evidence doesn't support *this* level of care. Step down with 14 transition days.
4. **Otherwise?** Hard deny. Either the documentation is empty or goals are untracked.

The confidence floor exists because a reassessment can claim "D5: High" in one word, but if four weeks of progress notes contain zero supporting evidence, the claim is unsupported. The notes win. This is a deliberate design choice: the engine rewards clinical thoroughness, not assertion.

## What we learned from testing

### Blind comparison against answer key (7 cases)

I built my own predictions independently, then compared with Claude's. 6 of 7 matched on the first run.

| Case | Engine | Key | Notes |
|------|--------|-----|-------|
| CSA-001 | APPROVE | APPROVE | D5/D6 high, active-using partner at discharge address |
| CSA-002 | DENY WITH TRANSITION | DENY/TRANSITION | All goals met, member requesting discharge |
| CSA-003 | DENY | DENY | Boilerplate documentation, no goal tracking |
| CSA-004 | APPROVE | APPROVE | Bereavement destroyed housing plan, goals regressed |
| CSA-005 | DENY (fatal) | DENY (fatal) | Submitted 8 days before window. Strong clinical case killed by timing |
| CSA-006 | APPROVE (partial) | UNCERTAIN, lean approve | Self-report unreliability, conflicting evidence |
| CSA-007 | CORRECT AND RESUBMIT | DENY as submitted, CORRECTABLE | 45 days requested, adolescent cap is 30 |

**CSA-003 vs CSA-004** is the most instructive pair. Both have zero progress this review period. CSA-004 approves because the barrier (mother's death) is documented with dates and specifics across three notes, a crisis session was delivered, and the regimen was adjusted. CSA-003 denies because the documentation says nothing — the same progress finding, opposite outcomes, difference entirely in documentation quality. This is the engine working as intended: the engine rewards robust clinical narratives; even moreso, it penalizes the lack of clinical narrative underpinning requests and summative evaluations.

**CSA-006** was the disagreement between Claude and my engine. The engine initially returned a clean high-confidence APPROVE. Two bugs: the extraction layer gave craving self-reports too-high confidence despite hedging language ("maybe a 4 but it depends"), and the scoring layer ignored the `conflicting` flag entirely. I made the decision to separate these into two independent fixes — a scoring penalty for conflicting evidence (code change, deployed) and prompt calibration via few-shot examples (deferred, identified as highest-priority improvement). The conflict penalty is a hypothesis derived from one case, not a calibration. Validating it needs a larger case set with known outcomes — that is the first thing to build with more time, and it is the difference between fitting and calibrating.

### Stress test (25 cases)

We generated 25 synthetic cases across five categories: procedural failures, clinical approvals, transition denials, hard denials, and edge cases.

**Procedural layer: 5/5 correct.** Every gate — late submission, underage member, over-length request, unlicensed facility, early submission — fired correctly with the right severity. The procedural layer is deterministic and does not depend on the LLM. It is the most reliable component and the most immediately valuable: these are the mistakes that cost providers money, and the engine catches them before submission.

**Transition denials: 5/5 correct.** Cases with met goals and low acuity consistently received DENY_WITH_TRANSITION with a specific recommendation to request transition days. This is the engine's most distinctive output — it recommends the middle path proactively rather than waiting for a denial that the provider then has to appeal.

**Clinical approvals: 3/8 correct.** Five cases failed because the extraction layer hit output token limits under concurrent load. JSON responses were truncated mid-string and failed schema validation. After increasing the token limit and adding a truncation retry, these cases extracted correctly in isolated testing but still fail intermittently under 20+ concurrent API calls. This is a rate-limiting and concurrency problem, not a logic problem.

**Hard denials: 0/4 correct.** These exposed a real architectural gap. Cases where a member left AMA, where notes were copy-pasted verbatim, and where the reassessment contradicted the notes all passed through the engine. The scoring layer operates on confidence and acuity — it has no concept of clinical red flags. The extraction layer processes substantive-looking text successfully; it cannot tell that "member left the program five days ago" should be disqualifying, or that four identical notes indicate fabrication rather than stability. This is the most important finding from the stress test, and consequently, another very important area to lean into for testing and propose new additions to the extraction layer.

## How we responded to failures

The project produced three categories of failure, and we handled each differently.

**Conflicting evidence (CSA-006).** Diagnosed as two independent bugs — one in extraction (prompt calibration), one in scoring (missing penalty). Fixed the scoring layer immediately. Deferred the extraction fix with an honest assessment: the 0.6 penalty constant comes from one case. This is acknowledged as a hypothesis, not a calibration.

**Correctable display (CSA-007).** The initial output showed APPROVE with a correctable note buried below. A review caught that a billing person would see APPROVE first and submit a 45-day request that gets denied downstream. We added a distinct display state (CORRECT AND RESUBMIT) with imperative copy that frontloads the required action. The clinical verdict still exists — it just cannot be the first thing the billing person sees when the request as submitted cannot be approved.

**Extraction truncation (stress test).** Five clinical-approval cases returned hard denies because the LLM's JSON output exceeded the token limit. Doubled the output limit and added a retry with shortened source quotes. Fixed in isolated testing; still intermittent under concurrent load. Documented as a concurrency problem requiring batching, not a logic fix.

**Scoring red flags (stress test).** AMA departures, copy-paste notes, and contradictory reassessments all passed the engine. We did not attempt a quick fix because these require a fundamentally different detection mechanism — pattern matching on content rather than confidence scoring on dimensions. Documented honestly as a known gap rather than shipping a brittle heuristic.

## What the engine is and is not

The engine is a **guidance and time-saving tool**. It tells a billing person "this request will likely be approved," "this request needs correction before submission," or "this request is unlikely to be approved — consider requesting transition days instead." It does not make the decision. It does not replace the payer's review. It surfaces the procedural and clinical factors that drive the decision so the billing person can act on them without reading every note and cross-referencing every rule manually.

The beta values — the confidence floor, the conflict penalty, the goal-tracking requirement — are starting points informed by a small case set. They are presented as guidance, not as scores that map to approval probabilities. The engine is transparent about its confidence level on every decision. When it says APPROVE at 84% confidence, that is not "84% chance of approval" — it is "the evidence I found for this decision averages 84% clarity." The distinction matters.

## What to build next

### Immediate

- **Few-shot examples in the extraction prompt.** One clean case, one with conflicting evidence, one with thin documentation. The single highest-impact improvement for extraction quality, especially calibrating confidence on hedging language. Few-shot construction is something I genuinely only discovered in working on this project.
- **Concurrency controls.** Semaphore or queue to limit parallel API calls. The extraction logic works; the infrastructure doesn't handle load. This I have previously encountered in other contexts, but prioritized getting the architecture where I wanted it before optimization for lots of cases. 
- **Clinical red-flag detection.** A second pass that checks for patterns the confidence model can't catch: AMA departures in notes, identical note text across sessions, reassessment claims contradicting note trajectory. This is a rules layer, not an LLM layer — the patterns are specific and enumerable. To me, the most interesting of the immediate improvements. 

### Medium-term

- **Scoring criteria arrays.** Multiple scoring configurations (aggressive, conservative, baseline) that weight dimensions and confidence thresholds differently. Run cases against all three, compare outcomes, report where they diverge. The divergence points are more interesting than any single score — they show which cases are genuinely on the line and which are clear regardless of how you weight the evidence.
- **Calibration dataset.** 100+ cases with known payer outcomes to calibrate the confidence floor and conflict penalty against real decisions. This converts hypothesis-driven constants into evidence-driven ones and is the prerequisite for any claim about accuracy. Would be nice to pull, normalize, and run on anonymized clinical data, and compare results to synthetic generation - this could determine optimal training dataset conditions.
- **Temporal evidence tracking.** The current extraction treats all four progress notes as a flat set. A better model would track trajectories: is the member improving, plateauing, or regressing? The extraction schema already supports this (the `regressed` goal status exists), but the scoring layer doesn't yet weight direction of change. A member whose cravings went 8 → 5 → 5 → 5 is different from one whose went 8 → 5 → 7 → 7, even if the final number is the same.

### Longer-term

- **Multi-payer rule encoding.** The architecture separates rules from logic deliberately. Adding a second payer means a new citation set and new gate functions — the extraction layer, scoring framework, and output design carry over. The question is whether different payers' rules are structurally similar enough to share the gate interface. Given Athon's goals of expanding to an array of different recovery centers, an engine that routes based on public rulesets on geolocated basis could be a smart addition.
- **Proactive transition-day recommendation.** The engine already identifies DENY_WITH_TRANSITION cases. The next step is recommending transition days *during* the documentation phase, before submission — "based on what you've documented so far, continued stay is unlikely to be approved, but you qualify for transition days if you submit now."
- **EHR integration contract.** The extraction layer assumes raw clinical text. In production, that text comes from an EHR. Defining what fields the EHR emits, how the engine adapts when fields are missing, and what fallback extraction looks like is the bridge between prototype and product.

## Stack

Python, FastAPI, Pydantic, Jinja2. No database, no React, no Docker. Claude Sonnet for extraction only — never for scoring, never for rule application.

## File structure

```
src/
  models.py       # Pydantic schemas: Episode, GateResult, Evidence, Score
  procedural.py   # Six procedural gates, pure functions
  extraction.py   # LLM extraction: narrative -> structured evidence
  scoring.py      # Clinical scoring: evidence -> three-state decision
  main.py         # FastAPI app, upload endpoint, orchestration
templates/
  index.html      # Dashboard: all cases, color-coded decisions
  result.html     # Case detail: gates, dimensions, goals, rationale
  upload.html     # File upload with format guide
tests/
  test_procedural.py  # 53 gate tests
  test_scoring.py     # 24 scoring tests
data/
  cases-v1.json            # 7 original cases
  stress-test-cases.json   # 25 stress test cases
citations.md               # Utah Medicaid rules, atomized with stable IDs
Makefile                    # serve, test, pipeline
```

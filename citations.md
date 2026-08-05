# Utah Medicaid Behavioral Health — Source Citations

Source: **Utah Medicaid Provider Manual – Behavioral Health Services**
Updated: **July 2026**
File: `BehavioralHealthServices7-26.pdf`

Ordered by manual chapter for easy verification against the source. ID format is `UT-{chapter}-{seq}`. Reference IDs in `rules.json` rather than prose.

---

## Chapter 1-1 — Definitions

### Page 8

- `UT-1-1-a` — Medically Necessary Services means the same as defined in Utah Administrative Code R414-1-2(18).
- `UT-1-1-b` — Institution for Mental Diseases (IMD) means the same as defined in 42 CFR 435.1010.
- `UT-1-1-c` — Mental Health Therapist means the same as defined in the Mental Health Practice Act, Title 58-60-102.

### Page 7

- `UT-1-1-d` — Behavioral health services are a covered benefit when the services meet the definition of medical necessity as defined in Utah Administrative Code R414-1-2.

> **UNVERIFIED.** The manual defines medical necessity by reference only. The operative text lives in R414-1-2(18) at rules.utah.gov and has not yet been pulled. The step-down / "more conservative or substantially less costly" logic depends on it. Confirm before encoding.

---

## Chapter 3 — Provider Participation and Requirements

### 3-1 Providers Qualified to Prescribe — Page 9

- `UT-3-1-a` — Behavioral health services must be prescribed by a mental health therapist as defined in Title 58-60-102, Mental Health Professional Practice.

### 3-2 Providers Qualified to Render — Page 9

- `UT-3-2-a` — All providers must render services only within their scope of practice.

### 3-4 Unlicensed Behavioral Health Providers — Page 11

- `UT-3-4-a` — Unlicensed providers must be supervised by a licensed mental health provider.
- `UT-3-4-b` — Unlicensed providers must report services under the National Provider Identifier of their supervisor.
- `UT-3-4-c` — The modifier HL must be used to indicate when an unlicensed provider performed the service.

---

## Chapter 4 — Record Keeping

### 4-1 Required Documentation — Page 11

- `UT-4-1-a` — For each service, providers must develop and maintain sufficient written documentation to support the medical necessity and the provision of the prescribed behavioral health service.
- `UT-4-1-b` — Documentation must include the specific service rendered to the member.
- `UT-4-1-c` — Documentation must include the date, start time, stop time, and duration of the service.

### 4-1 Required Documentation — Page 12

- `UT-4-1-d` — Documentation must include the physical setting in which the service was rendered.
- `UT-4-1-e` — When services are provided via telehealth, the record must specify the provider's setting and explicitly state that the service was provided via telehealth.
- `UT-4-1-f` — The service summary must include the treatment plan goal or goals addressed.
- `UT-4-1-g` — The service summary must include the specific intervention or interventions used.
- `UT-4-1-h` — The service summary must include a record of what occurred during the service.
- `UT-4-1-i` — Documentation must include the signature and licensure or credentials of the individual who rendered the service.

> **Note.** Chapter 4-1 contains no progress-or-barriers requirement. That rule lives in 7-10.4 only. Do not cite 4-1 for it.

---

## Chapter 6 — Treatment Plan

### Pages 13–14

- `UT-6-a` — When behavioral health services are deemed medically necessary, a mental health therapist is responsible for developing an individualized treatment plan in collaboration with the member.
- `UT-6-b` — A mental health therapist is responsible for conducting reassessments and treatment plan reviews with the member as clinically indicated.
- `UT-6-c` — Reassessments and treatment plan reviews must ensure the treatment plan remains current and accurately reflects the member's goals and needed behavioral health services.
- `UT-6-d` — Initial treatment plans and subsequent treatment plan reviews and updates must be documented.
- `UT-6-e` — The treatment plan must include measurable treatment goals.
- `UT-6-f` — The date each treatment goal is added must be included.
- `UT-6-g` — The treatment plan must include the specific treatment methods that will be used to meet the measurable treatment goals.
- `UT-6-h` — The treatment plan must include a projected schedule for service delivery.
- `UT-6-i` — The projected schedule must include the expected frequency and duration of each treatment method.
- `UT-6-j` — The treatment plan must include the licensure or credentials of the individuals who will furnish the medically necessary services.
- `UT-6-k` — The treatment plan must include the signature and licensure or credentials of the mental health therapist who developed the treatment plan.

---

## Chapter 7-10.4 — Group Psychosocial Rehabilitative Services in Licensed Day Treatment, Licensed Residential Treatment, and School Day Treatment Programs

### Page 26

For each date of participation, documentation must include:

- `UT-7-10-4-a` — the name of each group in which the member participated
- `UT-7-10-4-b` — the date of each group
- `UT-7-10-4-c` — the start and stop time of each group
- `UT-7-10-4-d` — the duration of each group

### Page 27

- `UT-7-10-4-e` — Documentation must include the setting in which each group service was rendered.
- `UT-7-10-4-f` — When group services are provided via telehealth, the provider setting and a notation that the service was provided via telehealth must be documented.
- `UT-7-10-4-g` — One summary note for each unique type of psychosocial rehabilitative group the member participated in during the immediately preceding two-week period must be prepared at the close of the two-week period.
- `UT-7-10-4-h` — The summary note may be written by the provider who conducted the group or by a provider most familiar with the member's involvement and progress across groups.
- `UT-7-10-4-i` — The summary note must include the name of the group.
- `UT-7-10-4-j` — The summary note must include the treatment goal or goals addressed in the group.
- `UT-7-10-4-k` — The summary note must include the member's progress toward treatment goals.
- `UT-7-10-4-l` — If there was no reportable progress, the summary note must document reasons or barriers.
- `UT-7-10-4-m` — The summary note must include the signature and licensure or credentials of the individual who prepared the documentation.
- `UT-7-10-4-n` — If a co-leader is present, the note must include the co-leader's name and licensure or credentials.

> **Encoding note.** `UT-7-10-4-k` and `UT-7-10-4-l` form one gate: fail only when there is no reportable progress **and** no documented reason or barrier. Flat absence of progress is not itself a violation.

---

## Chapter 7-19 — Substance Use Disorder Residential Treatment

### 7-19.1 General — Page 37

- `UT-7-19-1-a` — SUD residential treatment provides specialized treatment in a 24-hour group living environment for individuals with substance use disorders.

### 7-19.2 Provider Participation — Pages 37–38

- `UT-7-19-2-a` — Providers must be licensed by the DHHS Office of Licensing and meet the requirements in Utah Administrative Code R501-19.
- `UT-7-19-2-b` — Programs cannot refuse to accept a member solely because the member uses medication-assisted treatment consistent with the recommendation of a qualified healthcare professional.
- `UT-7-19-2-c` — Programs must allow a member to receive medication-assisted treatment as recommended by a qualified healthcare professional.

### 7-19.3 Limitations — Page 38

- `UT-7-19-3-a` — Prior authorization is required for all members receiving SUD residential treatment.
- `UT-7-19-3-b` — SUD residential treatment is limited to members age 12 and older.
- `UT-7-19-3-c` — The service is reportable on hospital admission and discharge dates.

### 7-19.4 Prior Authorization — Page 38

- `UT-7-19-4-a` — PA requests for adolescent members age 12 through 18 may be approved for up to 30 calendar days per request.
- `UT-7-19-4-b` — PA requests for adult members age 19 or older may be approved for up to 60 calendar days per request.
- `UT-7-19-4-c` — Members may receive one initial PA per treatment episode without accompanying medical documentation.
- `UT-7-19-4-d` — If a PMHP, UMIC Plan, or HOME program issued the initial PA and the member changes to FFS during the treatment episode, continued-stay PA requests must be submitted within PRISM.

> **Encoding note.** `UT-7-19-4-a` and `UT-7-19-4-b` are one age-conditional gate. Severity is CORRECTABLE: an over-length request has a specific fix (resubmit at the cap).

### 7-19.4.1 Initial Admission PA Request — Page 39

- `UT-7-19-4-1-a` — The initial admission PA request must be submitted no later than 2 business days after the date of admission.
- `UT-7-19-4-1-b` — No supporting documentation is required with the initial admission PA request.

> **Encoding note.** Business days here, not calendar days. Contrast `UT-7-19-4-2-*` and `UT-7-19-4-3-*`, which are calendar days. Two different clocks.

### 7-19.4.2 Continued Stay PA Request — Page 39

- `UT-7-19-4-2-a` — A continued-stay PA request must be submitted no later than the first requested date of service.
- `UT-7-19-4-2-b` — A continued-stay PA request must be submitted no earlier than four calendar days of, and including, the first requested date of service indicated on the PA request.
- `UT-7-19-4-2-c` — A continued-stay PA request must include a completed reassessment and treatment plan review using ASAM criteria.
- `UT-7-19-4-2-d` — The reassessment and treatment plan review must be no later than the first date of service requested on the PA request form.

> **Encoding note.** `UT-7-19-4-2-a` and `UT-7-19-4-2-b` define a single four-calendar-day window ending on the first requested DOS. Encode as one gate or a single early submission emits two violations. Severity is FATAL: once the window has passed there is no correction.
>
> Read `first_requested_dos` off the episode record. Do not derive it from days elapsed.

### 7-19.4.3 Transition Days — Page 39

- `UT-7-19-4-3-a` — If the provider determines that medical necessity for continued stay is not met, the provider may request up to 14 calendar transition days to allow time to transition the member to the medically necessary ASAM level of care.
- `UT-7-19-4-3-b` — When Medicaid determines that the clinical documentation does not support the need for continued stay, 14 transitional calendar days may be authorized to allow time for transition to the medically necessary ASAM level of care.

> **Encoding note.** This is why output is three-state rather than binary. `UT-7-19-4-3-a` is the proactive path and is the actionable recommendation when the engine predicts a step-down denial.

### 7-19.4.4 Member Absence from the Program — Page 39

- `UT-7-19-4-4-a` — If a member is absent for three calendar days or less, the provider must request a modification to the current PA request using the modification request form.
- `UT-7-19-4-4-b` — The modification information must include the dates the member was absent.
- `UT-7-19-4-4-c` — If a member is absent for more than three calendar days, the provider must request a new non-clinical PA.
- `UT-7-19-4-4-d` — The comments section must include the date the member left the program.

### 7-19.4.5 Modification Requests — Page 40

- `UT-7-19-4-5-a` — If a modification to an authorization is required, the provider must submit the modification request form and supporting documentation for the existing PA no later than 10 calendar days after the modification date.
- `UT-7-19-4-5-b` — Modification requests submitted after 10 calendar days are not considered timely and result in denial.

### 7-19.5 Coding and Billing — Page 40

- `UT-7-19-5-a` — Facilities may report the per-diem bundled service code only for dates when at least one qualifying behavioral health service is provided.
- `UT-7-19-5-b` — Qualifying services are: psychiatric diagnostic evaluation; psychotherapy (individual, group, or family); injectable administration of a drug; nursing assessment; case management; mental health assessment; peer services; training or skills development; community support services; psychosocial rehabilitative services; therapeutic behavioral services; targeted case management.
- `UT-7-19-5-c` — H0018: Substance Use Disorder Residential Treatment, IMD — per diem.
- `UT-7-19-5-d` — H2036: Substance Use Disorder Residential Treatment, non-IMD — per diem.

---

## Appendix: Rules That Do NOT Apply to This Service Line

Recorded deliberately. These are real rules in the same manual that govern adjacent services. They are excluded from `rules.json` on purpose.

### 7-18.4 Mental Health Residential Treatment, Programs with 17 or More Beds (IMDs) — Page 34

- `UT-NA-a` — Mental health residential treatment in an IMD is limited to 60 days per episode of care, regardless of medical necessity.
- `UT-NA-b` — If a mental health residential treatment episode exceeds 60 days, none of the days of the treatment episode are reportable or reimbursable.

### 7-17.1 Psychiatric Specialty Hospitals Considered IMDs — Page 33

- `UT-NA-c` — For inpatient psychiatric services in a psychiatric specialty hospital, members under 21 require no PA; members 21-64 require PA with a 60-day maximum length of stay per treatment episode; members 65 and older require no PA.
- `UT-NA-d` — If inpatient psychiatric treatment exceeds 60 days, no part of the stay is eligible for reimbursement.

### 7-18.5 Prior Authorization for MH Residential in IMDs — Pages 35–36

- `UT-NA-e` — MH residential PA requests are approved for up to 7 calendar days per request. (Contrast `UT-7-19-4-a` / `UT-7-19-4-b`: 30 or 60 calendar days for SUD residential.)
- `UT-NA-f` — MH residential continued-stay PA requests must include the anticipated discharge date in the comments section, and the clinical documentation must support it. No equivalent requirement appears in 7-19.4.2 for SUD.
- `UT-NA-g` — MH residential transition days are capped at 7 calendar days. (Contrast `UT-7-19-4-3-a`: 14 calendar days for SUD.)

> **Why this appendix exists.** The 60-day episode cliff with total forfeiture is frequently quoted as "the Utah 60-day rule" and is easy to misapply. It governs mental health residential and inpatient psychiatric services, not SUD residential. Utah's rules are specific to payer **and service line**, and an engine that keys only on payer will silently apply the wrong ruleset.
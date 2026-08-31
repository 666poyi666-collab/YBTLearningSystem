# Zero-Base Simulation Gates

## Contents

1. Purpose and boundary
2. Two simulation layers
3. Persona set
4. Five stress-test rounds
5. Growing learner protocol
6. Per-item attempt protocol
7. Repair rules
8. Pass conditions
9. Evidence states

## 1. Purpose and Boundary

The five-persona simulation is a synthetic route audit: it tests whether the written route exposes enough information to start, continue, correct, and check every item. It is not mathematical solving, a scored learner evaluation, or proof that a real learner mastered the section.

Any learner simulation may use only:

- The assigned course transcripts as the equivalent of watching the videos.
- The answer-free knowledge route.
- The real target question during its attempt.
- Verified visual descriptions.
- Minimal hints allowed by the current route.

The learner may not use target answers, target worked solutions, answer sidecars, other personas' attempts, or evaluator conclusions.

## 2. Two Simulation Layers

Use two separate layers:

1. `route_stress_audit`: the fixed five-persona, five-round suite. It searches systematically for route defects and remains section-local machine evidence. Its records are `route_assessments`, not grades.
2. `primary-user-proxy`: one persistent, chapter-level route actor that approximates the current user's workflow. It starts with minimal zero-base assumptions, works in textbook order, and carries evidence-backed predictions across sections and runs. Predictions remain separate from confirmed user facts.

Never merge their attempts or profile claims. Neither layer can fill real-user progress. Loading a transcript proves availability, not course consumption; writing method steps without a final answer proves no mathematical correctness.

## 3. Persona Set

Use exactly five stable profiles in every round:

1. `literal-zero-base`: follows wording literally and misses unstated prerequisites.
2. `recognition-weak`: remembers formulas but struggles to classify the problem.
3. `algebra-weak`: finds the method but loses signs, domains, ratios, or transformations.
4. `visual-weak`: struggles to translate diagrams, coordinates, and spatial relations.
5. `self-check-weak`: can proceed but rarely detects an invalid result alone.

Do not make personas deliberately irrational. They represent plausible novice failure modes.

## 4. Five Stress-Test Rounds

### Round 1: Baseline Entry

Use route version 1. Test whether every persona can identify a relevant course/method and write the first mathematical line for every item. Record only the first blocker.

### Round 2: Prerequisite Repair

Apply repairs for missing definitions, prerequisite bridges, course calls, and recognition cues. Re-run all items, not only failed ones, because route edits can introduce regressions.

### Round 3: Continuation and Transfer

Use the current route on the same canonical items without reusing prior attempts. Test whether the learner can move from the first line through the method sequence and transfer the method to direct variants.

### Round 4: Mixed Retrieval

Present items in a deterministic mixed order internally while preserving textbook order in the final route. Test method selection when neighboring methods compete.

### Round 5: Cold Proxy

Start from an answer-free fresh learner context with only course and final-route content. Do not call this a 24-hour retest. Test every item again and bind all results to the final route hash.

## 5. Growing Learner Protocol

The controller runs `primary-user-proxy` only after the active chapter's section routes validate and merge.

1. Load the prior chapter progress file. For chapter 1, initialize only `zero_base`; do not invent detailed weaknesses.
2. Before an item, load every required course that is neither available nor blocked. Record transcript and `full_text` hashes as availability evidence. Record `simulated_completed` only when a separate actor actually consumes the content and that event is evidenced; loading is not consumption.
3. Attempt items in the reconstructed textbook order. Do not reset context or profile at section boundaries.
4. Freeze the attempt record before evaluation. The attempt must bind its section and learner-input snapshot. Grader-only files cannot be opened until the frozen artifact exists.
5. When evidence reveals a strength, gap, uncertainty, hint dependency, visual difficulty, or self-check gap, append a profile-history record and increment the profile version.
6. Apply the smallest route repair, then retry only when the repair is available in an answer-free context. Preserve all superseded attempts.
7. At chapter close, compute unfinished course keys and unresolved item keys. Carry the final profile into the next active chapter.

The growing learner is one sequential actor. Running one independent copy per section and merging their profiles is invalid. Rebuilding a report from profile version 1 on every run is also invalid; preserve immutable run records and derive the current snapshot from them.

## 6. Per-Item Attempt Protocol

For each persona and item:

1. Name the course and method family being called.
2. State the recognition cue.
3. Write the first line without a solved value.
4. List the next actions in order.
5. Perform the route's self-check.
6. Record the first blocker if any.
7. If blocked, apply at most the route's minimal correction prompt and record whether it restores progress.

Freeze the attempt record before route assessment. Each item must have 25 records across five rounds. These records need not contain a final answer, but then they cannot be mathematically graded.

Persist the actual text in `course_call`, `recognition_statement`, `first_line_attempt`, `continuation_attempt`, and `self_check_attempt`. Do not replace the learner attempt with evaluator booleans.

## 7. Repair Rules

Convert a failure into the smallest reusable route change:

- Cannot choose a course -> fix course mapping or ordering.
- Cannot classify the item -> add recognition cues and a contrast with the nearest competing method.
- Cannot write the first line -> add a symbolic first-line template.
- Cannot continue -> split the method into explicit actions or add a missing prerequisite bridge.
- Diagram is ambiguous -> block on visual evidence; never add a guessed relation.
- Repeated algebra error -> add a local sign/domain/ratio checkpoint.
- Cannot self-check -> add an independent substitution, dimension, sign, range, geometry, or alternative-form check.

Increment the route version after every repair set. Do not silently edit a route while retaining its old hash.

Each repair must name its failed item keys and the exact route field changed. A generic sentence such as “补充识别焦点” without before/after content is not a repair record.

## 8. Pass Conditions

A section route stress audit passes only when:

- Five rounds exist.
- Every round has all five personas.
- Every persona has exactly one result for every canonical item.
- Every item therefore has exactly 25 current-source attempt records.
- `failed_item_keys` exactly matches the incomplete records in every round.
- Attempt text is item-specific and persona-specific rather than copied in bulk.
- Every failed round has concrete, field-level repairs tied to its failed items.
- Round 5 binds the final route hash.
- All Round 5 items have `recognized_method`, `first_line_written`, `continuation_complete`, and `self_check_complete` true.
- No Round 5 item remains dependent on an unstated prerequisite or unverified image.
- `scripts/audit_student_question_isolation.py` reports all 1,209 projections passed and no learner context contains answer leakage.
- No source hash changed during the run.
- Every attempt ID is globally unique and binds the section plus input snapshot.
- The complete versioned run is activated only after every section validates; partial runs never replace the current pointer.

If an actual final answer exists and an arithmetic slip is independently corrected using the route's self-check, record it separately from the route assessment. A route-only attempt uses `mathematical_correctness=not_evaluated_no_final_answer`. Any hidden evaluator rescue or answer-derived persona text fails isolation.

The growing learner chapter completes only when:

- Its course ledger exactly covers the required course union.
- Every required course is `simulated_completed` with answer-free consumption evidence.
- Every canonical item received a final answer and independent mathematical verdict in source order.
- No unresolved item remains.
- Profile versions are monotonic and every change has frozen attempt evidence.
- The chapter progress validator passes.

## 9. Evidence States

- `route_stress_audit=passed`: the fixed five-persona protocol found the current route actionable for current source hashes. It says nothing about mathematical correctness.
- `primary_user_proxy=not_run_no_final_learner_answers`: route attempts exist, but no final answers were graded and courses remain unfinished.
- `growing_learner=completed`: `primary-user-proxy` actually consumed required courses and completed independently graded item attempts for current hashes.
- `independent_acceptance=not_run`: another task has not yet independently validated the delivery.
- `human_acceptance=not_run`: no real learner evidence.
- `cold_24h_retest=not_run`: no real 24-hour retest.

Never promote a proxy result into a human or delayed-retention claim.

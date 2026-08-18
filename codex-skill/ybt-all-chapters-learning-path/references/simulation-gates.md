# Zero-Base Simulation Gates

## Contents

1. Purpose and boundary
2. Persona set
3. Five rounds
4. Per-item attempt protocol
5. Repair rules
6. Pass conditions
7. Evidence states

## 1. Purpose and Boundary

Simulation tests whether the route lets a zero-base learner use the assigned courses to start, continue, correct, and check every item. It is a proxy evaluation, not proof that a real learner mastered the section.

The learner may use only:

- The assigned course transcripts as the equivalent of watching the videos.
- The answer-free knowledge route.
- The real target question during its attempt.
- Verified visual descriptions.
- Minimal hints allowed by the current route.

The learner may not use target answers, target worked solutions, answer sidecars, other personas' attempts, or evaluator conclusions.

## 2. Persona Set

Use exactly five stable profiles in every round:

1. `literal-zero-base`: follows wording literally and misses unstated prerequisites.
2. `recognition-weak`: remembers formulas but struggles to classify the problem.
3. `algebra-weak`: finds the method but loses signs, domains, ratios, or transformations.
4. `visual-weak`: struggles to translate diagrams, coordinates, and spatial relations.
5. `self-check-weak`: can proceed but rarely detects an invalid result alone.

Do not make personas deliberately irrational. They represent plausible novice failure modes.

## 3. Five Rounds

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

## 4. Per-Item Attempt Protocol

For each persona and item:

1. Name the course and method family being called.
2. State the recognition cue.
3. Write the first line without a solved value.
4. List the next actions in order.
5. Perform the route's self-check.
6. Record the first blocker if any.
7. If blocked, apply at most the route's minimal correction prompt and record whether it restores progress.

Freeze the attempt record before evaluation. Each item must have 25 records across five rounds.

Persist the actual text in `course_call`, `recognition_statement`, `first_line_attempt`, `continuation_attempt`, and `self_check_attempt`. Do not replace the learner attempt with evaluator booleans.

## 5. Repair Rules

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

## 6. Pass Conditions

A section proxy simulation passes only when:

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
- No learner context contains answer leakage.
- No source hash changed during the run.

If an arithmetic slip is detected and independently corrected using the route's self-check, record it as `passed_after_self_correction`, not an unqualified pass. Any hidden evaluator rescue fails the item.

## 7. Evidence States

- `proxy_simulation=passed`: the protocol above passed for the current route/source hashes.
- `independent_acceptance=not_run`: another task has not yet independently validated the delivery.
- `human_acceptance=not_run`: no real learner evidence.
- `cold_24h_retest=not_run`: no real 24-hour retest.

Never promote a proxy result into a human or delayed-retention claim.

# Delivery Output Schema

## Contents

1. Required files
2. `delivery.json`
3. Item method record
4. Simulation record
5. Markdown and HTML requirements
6. Evidence file
7. Growing learner chapter progress

## 1. Required Files

Each assignment writes only:

```text
reports/luna_sections/<task_id>/
  delivery.json
  learning_path_without_questions.md
  learning_path_without_questions.html
  evidence.md
  shared_defects.json          # only when defects exist
```

## 2. `delivery.json`

Required top-level shape:

```json
{
  "schema_version": "ybt-luna-section-delivery-v2",
  "task_id": "LUNA-YBT-01",
  "model_contract": {
    "model": "combo/protect-luna",
    "reasoning_effort": "max",
    "context_window": 1050000
  },
  "assigned_sections": ["..."],
  "source_binding": {
    "ready_sha256": "...",
    "packet_build_sha256": "...",
    "course_catalog_sha256": "...",
    "vision_sidecar_sha256": "...",
    "ocr_vision_evidence_sha256": "..."
  },
  "sections": [],
  "coverage": {
    "expected_items": 0,
    "delivered_items": 0,
    "duplicate_items": [],
    "missing_items": [],
    "unexpected_items": []
  },
  "proxy_simulation": "passed",
  "independent_acceptance": "not_run",
  "human_acceptance": "not_run",
  "cold_24h_retest": "not_run",
  "status": "passed"
}
```

Each section contains:

```json
{
  "section": "2.1",
  "label": "第1节 ...",
  "source_binding": {
    "packet_sha256": "...",
    "learning_packet_sha256": "...",
    "transcript_sha256": ["..."],
    "image_sha256": ["..."]
  },
  "ocr_vision": {
    "mode": "luna_paddle_crosscheck|paddle_glm_crosscheck",
    "luna_status": "passed|blocked",
    "paddle_status": "passed",
    "visual_status": "passed",
    "visual_model": "combo/protect-luna|glm-4.6v-flash",
    "evidence_path": "reports/.../ocr_vision_crosscheck.json",
    "evidence_sha256": "...",
    "conflict_item_keys": [],
    "status": "passed"
  },
  "overview": {
    "first_course": "exact catalog course_key",
    "new_courses_in_section_order": [],
    "already_learned_dependencies": [],
    "item_labels_in_order": []
  },
  "route_versions": [],
  "final_route_hash": "...",
  "cycles": [],
  "items": [],
  "simulation": {},
  "coverage": {},
  "status": "passed"
}
```

## 3. Item Method Record

Every canonical item appears exactly once:

```json
{
  "item_key": "LI:<item_id> or Q:<qid>",
  "ordinal": 1,
  "kind": "worked_example|direct_variant|abc_exercise",
  "label": "教材例1 or A1",
  "cycle_sequence": 1,
  "position": "知识点右侧例题|直属变式|类型题|A/B/C习题",
  "course_refs": ["exact catalog course_key"],
  "knowledge_refs": ["full descriptive knowledge label"],
  "type_refs": ["full descriptive type label"],
  "recognition_cues": ["..."],
  "method_model": "...",
  "first_written_line_template": "...",
  "continuation_actions": ["..."],
  "likely_blockers": ["..."],
  "minimal_correction_prompts": ["..."],
  "independent_self_checks": ["..."],
  "visual_dependency": {
    "status": "READY_TEXT_ONLY|VISION_VERIFIED|BLOCKED",
    "image_sha256": []
  },
  "route_version": 1
}
```

Rules:

- `course_refs` cannot be empty.
- Use exact course keys from `data/all_chapters_course_catalog.json`.
- Do not include `question_text`, `teaching_text`, `solution`, `answer`, correct options, or solved final values.
- `first_written_line_template` must contain symbols or placeholders derived from the problem form, but must stop before solving.
- Recognition and blockers must be item-specific enough to distinguish neighboring items.
- Do not display `item_key` in learner-facing output.

Cycle shape:

```json
{
  "sequence": 1,
  "title": "...",
  "new_courses": [],
  "already_learned_course_calls": [],
  "knowledge_labels": [],
  "worked_example_keys": [],
  "direct_variant_keys": [],
  "type_example_keys": [],
  "exercise_keys": [],
  "acceptance_checks": []
}
```

## 4. Simulation Record

Required section shape:

```json
{
  "protocol": "five-round-five-persona-v2",
  "rounds": [
    {
      "round": 1,
      "route_version": 1,
      "route_hash": "...",
      "personas": [
        {
          "persona_id": "R1-P1",
          "profile": "literal-zero-base",
          "item_results": [
            {
              "item_key": "LI:...",
              "course_call": ["exact catalog course_key"],
              "recognition_statement": "learner wording tied to this item",
              "first_line_attempt": "symbolic first line, without the final result",
              "continuation_attempt": ["ordered learner actions"],
              "self_check_attempt": "independent check actually attempted",
              "recognized_method": true,
              "first_line_written": true,
              "continuation_complete": true,
              "self_check_complete": true,
              "first_blocker": null,
              "correction_used": null,
              "verdict": "passed"
            }
          ]
        }
      ],
      "failed_item_keys": [],
      "route_repairs": []
    }
  ],
  "expected_attempts_per_item": 25,
  "actual_attempts_per_item": {},
  "unresolved_item_keys": [],
  "status": "passed"
}
```

Each round has exactly five distinct personas. Each persona has exactly one result for every section item. Later rounds bind the revised route hash. Never copy another persona's answer into a later attempt.

`failed_item_keys` must exactly equal the items with any failed/incomplete persona result in that round. A repair is an object with `item_keys`, `field`, `before`, `after`, and `reason`; its item keys must be drawn from the failed list. Passed rows have no blocker. `passed_after_self_correction` rows must record a correction and all four ability booleans must be true.

Attempts must be item-specific and persona-specific. Repeating one blocker, first line, continuation, and self-check across most items is invalid even when the counts equal 25.

## 5. Markdown and HTML Requirements

The learner-facing route starts with:

1. Section name.
2. First course to hear.
3. Remaining new courses in order.
4. Exact textbook item labels to complete.
5. One-line source and status summary.

For each cycle show:

1. New course, if any.
2. Already learned courses called by this cycle.
3. Knowledge label.
4. Adjacent examples.
5. Direct variants.
6. Type examples.
7. A/B/C items.
8. Cycle checks.

Do not repeat the seven learner fields for every item in Markdown/HTML. `delivery.json` retains those fields for machine reconciliation. Learner-facing files use this compact hierarchy:

1. Chapter or section status strip: required courses, user-facing course/loop/item progress, unresolved items, and current real-user state. Do not expose internal `simulated_completed` or proxy labels as if they were human progress.
2. Deduplicated course checklist in learning order.
3. Source-derived textbook map for the section.
4. One shared method block per truthful knowledge/type/cycle unit: recognition, method, first line, continuation, blocker, correction, and self-check.
5. Complete item-label checklist under that method block.
6. Item-specific note only when an item differs from the shared method or remains blocked.
7. Cycle acceptance check and next action.

Never expose fixed-persona attempts, growing-learner attempt transcripts, hashes, or validator details in learner-facing files.

HTML requirements:

- UTF-8 `<meta charset="utf-8">`.
- Responsive at 360 px and desktop widths.
- No card nesting.
- Restrained work-focused layout.
- Distinguish new course, learned course, worked example, variant, type item, exercise, blocked state, and verification state by accessible color plus text.
- MathJax-compatible LaTeX with balanced delimiters.
- Stable task numbering; dynamic content must not shift controls or labels.
- Prefer a compact chapter ledger, sticky or nearby section navigation, short method blocks, and scannable item checklists over repeated prose panels.
- The current approved workspace composition is: chapter progress strip, section navigation, dynamic next step, vertical cycle route, vertical course queue, and full-width cycle detail. Do not restore a horizontal cycle-tab wall or report-style metric grid.
- A learner-facing page may keep browser-local stars, listened cycles, passed items, questions, and a `复制进度` action. It must state that the copied browser state is not cloud progress until a confirmed `math_sync_progress_snapshot` succeeds. Confirmed errors/classifications are written by `math_record_wrong_question`; live wrong-question documents come from `math_export_wrong_questions`; deferred cycles remain distinct from completion.

## 6. Evidence File

`evidence.md` records:

- Exact files and hashes consumed.
- Commands run.
- Validator output.
- Coverage totals.
- Simulation counts and route versions.
- Shared defects.
- Final states for proxy simulation, independent acceptance, human acceptance, and 24-hour retest.

Do not paste credentials, full chat transcripts, or answer sidecars.

## 7. Growing Learner Chapter Progress

Persist the chapter-level learner at `data/learner_progress/chapter<chapter>.json`:

```json
{
  "schema_version": "ybt-growing-learner-chapter-v1",
  "chapter": 1,
  "source_binding": {
    "manifest_sha256": "...",
    "course_catalog_sha256": "...",
    "assignment_sha256": "...",
    "requirements_sha256": "...",
    "delivery_sha256": {}
  },
  "learner": {
    "learner_id": "primary-user-proxy",
    "mode": "persistent_zero_base_proxy",
    "profile_version": 1,
    "initial_assumptions": ["zero_base"],
    "confirmed_strengths": [],
    "confirmed_gaps": [],
    "uncertainties": [],
    "hint_dependencies": [],
    "self_check_gaps": [],
    "profile_history": [
      {
        "version": 1,
        "reason": "initialized_with_zero_base_assumption_only",
        "evidence": []
      }
    ]
  },
  "course_ledger": {
    "required_course_keys": [],
    "records": [
      {
        "course_key": "exact catalog course_key",
        "first_section": "1.1",
        "status": "planned",
        "completion_evidence": []
      }
    ],
    "unfinished_course_keys": [],
    "status": "not_started"
  },
  "sections": [
    {
      "section": "1.1",
      "status": "not_started",
      "profile_version_before": 1,
      "profile_version_after": 1,
      "attempted_item_keys": [],
      "passed_item_keys": [],
      "unresolved_item_keys": []
    }
  ],
  "coverage": {
    "canonical_items": 0,
    "attempted_items": 0,
    "passed_items": 0,
    "unresolved_items": 0,
    "remaining_items": 0
  },
  "simulated_learning_status": "not_started",
  "human_learning_status": "not_started",
  "cold_24h_retest": "not_run",
  "status": "not_started"
}
```

Rules:

- The required course set is the exact union of `course_refs` for every canonical item in the chapter's validated section deliveries.
- `planned` and `in_progress` courses appear in `unfinished_course_keys`. `simulated_completed` requires non-empty answer-free course-consumption evidence. `blocked` also remains unfinished.
- Section item sets are checked against canonical packets. A completed section has attempted and passed every item and has no unresolved item.
- Profile versions never decrease. A version increment requires a profile-history record tied to frozen attempt evidence.
- `status=completed` requires all required courses to be `simulated_completed`, every section to pass, and every canonical item to pass.
- `human_learning_status` and `cold_24h_retest` are never promoted by proxy evidence.

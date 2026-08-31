# Workflow Contract

## Contents

1. Authority and scope
2. Source boundary
3. Artifact chain
4. S0-S10 workflow
5. Course and textbook ordering
6. Visual and OCR gates
7. Answer isolation
8. Versioning and evidence states
9. Parallel-task discipline
10. Chapter learner handoff

## 1. Authority and Scope

Authority order:

1. Current explicit user words.
2. Current requirement acceptance criteria.
3. Real textbook pages and allowed course files.
4. Current source hashes, packets, tests, and runtime evidence.
5. Verified in-scope memory.
6. Old chats, draft reports, generated pages, and model claims.

Resolve the active project from the current repository or the task's explicit path.

The current static-route and audit target is the complete book: 5 chapters, 38 canonical sections, and 1,209 numbered learning items. Chapter 1 Section 1 remains the golden regression sample, but it does not delay Sections 1.2 through Chapter 5. These counts are not an excuse to skip live verification; compare them with `reports/all_chapters/packet-build-current.json` and the chapter manifests.

## 2. Source Boundary

Allowed course identity comes from `data/all_chapters_course_catalog.json`; committed transcripts are resolved by filename under `data/course_transcripts`. If raw videos are restored, supply their course root explicitly and verify each hash against the catalog instead of relying on a historical user path.

Allowed course directories:

- `3.1 空间向量与立体几何`
- `3.2 直线与圆的方程`
- `3.3 圆锥曲线的方程`
- `3.4 圆锥曲线方程的综合提升`
- `4.1 一元函数的导数及其应用`
- `4.2 一元函数的导数及其应用的综合提升`
- `4.3 数列`
- `4.4 数列的综合提升`

The mathematical `8.5` and `8.5课程` projects may be used only as requirement/course-mapping evidence. Do not import unrelated files or completion claims from neighboring projects.

Allowed textbook evidence:

- Current chapter manifests.
- PaddleOCR AI Studio outputs under `data/ocr_live_current`.
- Current Luna Max vision observations bound to the original image SHA, or READY-bound exact-SHA GLM fallback observations when the Luna host capability probe is blocked.
- Source-bound image crops in each OCR root.
- Current derived correction layer with explicit source anchors.

Forbidden contamination:

- 老人版课程.
- `8.5g`.
- 数学摄像头.
- Answer-book OCR in learner contexts.
- Courses outside the eight directories above.
- Course or transcript files whose SHA does not match the current catalog.

The supplementary `2026版 高中必刷题数学 选择性必修第一册 RJA` is a separate optional practice source. It may be recommended after the linked course/YBT unit is available, but it never blocks course, YBT, section, or chapter completion. Its PDF has no answer content; OCR locates a source page, while the original page image verifies the exact problem.

## 3. Artifact Chain

Read the artifacts in this order:

1. The active scope's current source audit and assignment binding. Legacy `reports/ch12_luna_dispatch/` files cover only their named chapter subset and cannot prove the five-chapter release.
2. `reports/all_chapters/packet-build-current.json`.
3. `data/all_chapters_course_catalog.json`.
4. Assigned chapter manifests.
5. Assigned `data/packets/<section>/learning_packet.json`.
6. Assigned `data/packets/<section>/student_packet.json` and `student_learning_items.json` when present.
7. Bound course transcripts.
8. Current Luna/Paddle cross-check records, or capability-blocked Luna plus READY-bound GLM/Paddle fallback records, bound to original image SHAs.
9. `data/chatgpt_context/chapter12_complete_audit.json` before any ChatGPT handoff or claim that the active chapters are statically complete.

Do not begin a delivery while `READY.json` is absent or its status is not `ready`. Hash every consumed file and write the hashes into `delivery.json`.

Packet status rules:

- `VERIFIED`: structural packet gate passed for the current hash.
- `UNVERIFIED`: diagnostic only; do not release the section.
- Visual sidecars and simulations can still block a structurally verified packet.
- The context audit is a separate static-completeness gate. It must bind question text, visual assets, transcripts, progress files, and hashes; it does not claim human learning completion.

## 4. S0-S10 Workflow

### S0 Assignment Intake

- Read this contract, the output schema, simulation gates, and the project execution document.
- Confirm the assigned section set and output directory.
- Confirm no overlap with another task.

### S1 Source Snapshot

- Verify READY, packet-build, course-catalog, packet, transcript, and visual hashes.
- Reject stale or missing files.
- Record exact source paths without copying secrets or credentials.
- Run the section context audit for the requested section and `scripts/audit_all_chapters_sources.py` plus `scripts/audit_all_section_learning_contracts.py` for the all-book release. The all-book static gate requires 5 chapters, 38 sections, 1,209 canonical items, verified packet/learning-packet status, no unresolved visual assets, and exactly-once route coverage.

### S2 Textbook Reconstruction

- Read every OCR page in the section range.
- Reconstruct left/right and top/bottom layout from headings, examples, images, and page continuation.
- Establish the source order and real parentage among knowledge blocks, adjacent examples, type examples, variants, and reinforcement exercises. Do not force a universal block order.
- Never sort solely by abstract dependency if it contradicts the textbook layout.
- Cross-check Luna Max page/diagram observations against PaddleOCR and the original image; use the documented exact-SHA GLM fallback only after a Luna host capability failure.

### S3 Bidirectional Coverage Audit

- Manifest -> packet: every declared example, variant, and exercise must exist once.
- Packet -> manifest: every extracted numbered item must be declared in the same section.
- Verify group and number, source doc, image count, and section boundary.
- Any gap, duplicate, or cross-section item fails the section before pedagogy work begins.

### S4 Course Mapping

- Read transcript text, not only course titles.
- Read the bound transcript JSON `full_text`; a non-empty transcript is the teacher-method source used in explanations.
- For each cycle, identify the transcript method actually used.
- Record required new courses, already-learned prerequisites, and optional methods separately.
- Do not claim a course covers an item merely because the section references the course.
- Emit required course keys for the chapter ledger. Coverage is not course completion.

### S5 Section Overview

- State the first course to hear.
- List each later course only when first introduced in the section.
- List all item labels to be completed, without copying question text.
- Explain the route in one scan-friendly sequence.

### S6 Item Method Route

For every item, produce:

- Course calls with exact catalog keys.
- Recognition cues visible in the problem form.
- Method model and why it applies.
- First written line as a template with symbols/placeholders, not the solved value.
- Ordered continuation actions.
- Likely first blockers for a zero-base learner.
- Minimal correction prompts that do not reveal the result.
- Independent self-checks.
- Visual dependency and current visual status.

### S7 Learner Simulation

- Use the five-round/five-persona protocol in `simulation-gates.md` as a synthetic internal route stress audit.
- Every persona attempts every item.
- Build persona input only from whitelisted fields in `student_learning_items.json`, `student_packet.json`, manifests and the answer-free route. Run the all-item question-isolation audit first.
- Persist and hash learner attempts before loading `learning_packet.json`, `packet.json`, answer sidecars, teaching solutions or grader evidence.
- Record the learner's actual course call, recognition statement, first line, continuation attempt, self-check attempt, and first break. Boolean-only rows are not evidence.
- When no final mathematical answer exists, set mathematical correctness to `not_evaluated_no_final_answer`. Route assessment cannot become a correctness or mastery result.

### S8 Route Repair

- Convert repeated blockers into a concrete route edit: prerequisite, course call, recognition cue, first line, continuation step, visual cue, or self-check.
- Increment `route_version` and bind its hash.
- Re-run affected items in the next round.
- Keep superseded versions for audit.

### S9 Export

- Generate answer-free Markdown and HTML.
- Hide internal IDs.
- Use descriptive labels and stable task numbering.
- Use UTF-8 and MathJax-compatible LaTeX.
- Show current state honestly; do not style blocked items as complete.
- Keep per-item and per-persona details in machine JSON. In learner-facing files, group shared guidance by the smallest truthful textbook unit and show item-specific text only when it differs.

### S10 Validation and Handoff

- Run the bundled validator.
- Run section-specific tests when available.
- Write `evidence.md` with commands and meaningful results.
- Return status with `passed`, `failed`, `blocked`, `not_run`, `unknown`, and `stale` kept separate.

### S11 ChatGPT Assistance Handoff

- Use the approved remote math MCP first; keep the approved GitHub repository as the static fallback and audit source. Do not paste or upload the whole repository.
- Send the project bootstrap prompt from `prompts/math_project_bootstrap.md` once.
- Before teaching, ChatGPT reads system status/current task/live progress, the current no-answer item, its image, and every bound course transcript `full_text`; use GitHub context audit only when MCP is unavailable or a static hash audit is requested.
- Search paired handouts through OCR, then read the exact source-page image before using formulas, diagrams, or question wording. Candidate page/course links are not verified links.
- Use the HTML page's current-cycle prompt or `复制进度` snapshot for browser-local progress. Only a successful MCP write updates real cloud progress; repository progress JSON remains the proxy/evidence ledger.
- Confirmed errors, blockers, and hint dependencies are immediately written with `math_record_wrong_question`. “整理当前错题” calls `math_export_wrong_questions`; a skipped cycle calls `math_defer_cycle` and remains distinct from completion.
- For handwritten submissions, save a line-by-line `math_record_handwriting_analysis` proposal first. A proposed first error is not a confirmed wrong-question record until the learner confirms it.
- Ask for one diagnosis, one minimal hint, and one next action; wait for the learner attempt before adding help.
- If an exact path cannot be read, report the path and mark the explanation `资料不足` or `课程覆盖缺口`.

## 5. Course and Textbook Ordering

The active chapter route owns course deduplication. A section task must supply precise course use; it must not decide that a course was chapter-new unless the assignment explicitly provides prior chapter course state.

Within each section:

1. Introduce a course at its first cycle use.
2. In later cycles, label it as already learned but still list it under item course calls.
3. Keep optional courses out of mandatory release gates unless the item actually needs them.
4. If the course assumes an unstated prerequisite, add a bridge before the item and test that bridge.

The item order inside each cycle follows the source page. Common roles are knowledge blocks with adjacent examples, type examples with their variants, and reinforcement exercises, followed by a cycle acceptance check. Preserve observed parent-child relationships and do not relocate an item merely to fill a common role.

## 6. Visual and OCR Gates

Use [ocr-vision-crosscheck.md](ocr-vision-crosscheck.md). PaddleOCR is text/layout evidence; Luna Max is the preferred independent layout/diagram/semantic evidence; current exact-SHA GLM evidence is the transparent fallback when Luna image input is host-blocked; the original image is final authority.

For an item with images:

- Every image path must exist.
- Every image SHA must match its sidecar.
- Every cross-check record must be current, model-bound, structured, meaningful, conflict-adjudicated, and answer-free.
- Luna arrays are `objects`, `relations`, `coordinates`, `ranges`, `text`, and `uncertainties`; Paddle evidence preserves text and coordinates.
- Missing visual-provider proof, missing Paddle source evidence, unresolved material conflict, hash mismatch, answer language, or an unseen image blocks the item. A recorded Luna host rejection does not block the fallback path when exact-SHA GLM/Paddle evidence passes.
- Legacy absolute image paths in packets must be resolved to the active chapter OCR image root and recorded in the context audit. Do not treat the legacy path string itself as the current file location.

Never use a diagram description to solve the item or identify a correct option. Use it only to restore visible objects, labels, positions, and direct relations.

## 7. Answer Isolation

Learner contexts may include:

- Course transcripts.
- Answer-free knowledge notes.
- Target question text during simulation.
- Verified visual descriptions.
- The current route and minimal hints.

Learner contexts may not include:

- Target worked solutions.
- Answer sidecars.
- Correct options or final numeric/symbolic results.
- A previous persona's solved attempt.
- Evaluator conclusions.

The isolation boundary is executable, not descriptive:

1. `scripts/audit_student_question_isolation.py` must report 1,209 passed and zero blocked learner projections.
2. `student_learning_items.json` and `student_packet.json` are projected through a field whitelist. Any solution tail, next knowledge block, abnormal-length extraction, or unresolved OCR/source defect blocks the item before persona signals are derived.
3. Frozen attempt JSONL is written first and binds section, item, input snapshot and attempt SHA.
4. Only then may the route assessor load grader-only sources. The assessor records source availability and route actionability; it cannot mark mathematical correctness without a final learner answer.
5. Answer OCR states remain distinct: automatic, text requiring review, and source-page-only. The latter two prohibit automatic grading.

Delivery Markdown/HTML omits question text because the learner reads the real book. It names the textbook item and teaches how to approach it.

## 8. Versioning and Evidence States

Bind every route version to:

- Packet SHA.
- Learning-packet SHA.
- Course-catalog SHA.
- Used transcript SHAs.
- Visual-sidecar SHA.
- Item-method content SHA.

Status definitions:

- `passed`: current hash satisfies the explicitly named machine gate. A passed route audit is not a passed mathematical assessment.
- `failed`: gate ran and found a defect.
- `blocked`: required source, visual, permission, or dependency is unavailable.
- `not_run`: required action was not executed.
- `unknown`: evidence is missing or cannot be interpreted.
- `stale`: evidence belongs to a different source or route hash.

Route stress testing and the growing proxy never prove human mastery. Real human observation and 24-hour cold retest remain separate.

## 9. Parallel-Task Discipline

- Section route construction may be parallel, but the growing learner is one chapter-level sequential actor and must not run independently in multiple section tasks.
- When the runtime supports delegation and the user has authorized learner simulation, the controller may delegate exactly one answer-isolated learner role for the active chapter. That learner must not delegate further or edit shared sources.
- Do not edit shared source or another task's directory.
- Write only to `reports/luna_sections/<task_id>/`.
- Report shared defects in `shared_defects.json`; the controller is the only shared-source writer.
- A task may inspect all course/catalog files required by its assigned sections, but it may not broaden its section set.
- Completion means the assigned delivery validates. It does not mean the whole book is complete.

## 10. Chapter Learner Handoff

After all active chapter section routes validate:

1. The controller merges sections in manifest order and builds the exact union of item-level required courses.
2. It initializes or loads `data/learner_progress/chapter<chapter>.json` using schema `ybt-growing-learner-chapter-v1`.
3. `primary-user-proxy` loads course transcripts and attempts items sequentially. Transcript availability, transcript consumption, route attempt and final mathematical answer are separate evidence events; a file hash proves only availability.
4. The profile starts with only the zero-base assumption. Every profile change cites frozen attempt evidence and increments `profile_version`.
5. The chapter status lists unfinished required courses and unresolved canonical items. It is `completed` only when both are empty, final answers were independently graded, and the progress validator passes. Route-only runs remain unfinished.
6. Real-user and 24-hour states remain independent fields.
7. Browser-local stars, listened cycles, passed items, and questions are exported through the page progress snapshot; they are not silently written into the chapter proxy ledger.

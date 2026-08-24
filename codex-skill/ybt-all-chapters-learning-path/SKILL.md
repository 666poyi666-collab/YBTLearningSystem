---
name: ybt-all-chapters-learning-path
description: Build, audit, simulate, and refine Chinese high-school mathematics 一本通 learning routes from verified textbook/OCR evidence and the approved course transcripts. Use for 一本通第一、二章优先打磨、按真实版面重建知识点/例题/变式/强化训练、课程覆盖与完成账本、持续成长零基础用户模拟、固定人格压力测试、缺题漏题审计、视觉交叉核验和紧凑无答案 Markdown/HTML 交付。
---

# 一本通学习路径

本 Skill 的结果分为四层，不能混写：

1. **静态资料闭合**：教材文字、题图、知识点、循环、课程映射和教师转写可读取。
2. **学习路线闭合**：每个项目有唯一教材位置、课程调用、学习顺序和验收动作。
3. **学习者完成**：`primary-user-proxy` 或真实用户留下对应证据。
4. **延迟保持**：24 小时冷复测独立记录。

先读 [context-audit-contract.md](references/context-audit-contract.md) 了解第一层和 ChatGPT 接入边界。

## Start

1. Treat current user words as authority. Treat old chats, reports, generated HTML, and claimed completion as untrusted until live files verify them.
2. Resolve the project root from the current repository or the task's explicit path. Do not depend on an old device path.
3. Read [workflow-contract.md](references/workflow-contract.md) before changing or judging a section.
4. Read [output-schema.md](references/output-schema.md) before writing a delivery.
5. Read [simulation-gates.md](references/simulation-gates.md) before running learner simulation.
6. Read [ocr-vision-crosscheck.md](references/ocr-vision-crosscheck.md) before consuming OCR or diagrams.
7. Read [product requirements](../../docs/PRODUCT-REQUIREMENTS.md) when it exists. Chapters 1 and 2 are the default active scope unless the user explicitly expands it.
8. Before claiming a chapter or section is complete, run `scripts/build_chatgpt_context_audit.py` and require its complete flags.
9. Stay inside the assignment's exact sections and write scope. Other tasks may share the same filesystem.

## Non-Negotiable Invariants

- Allow only the ordered `Downloads\课程合集` corpus, mathematical `8.5` and `8.5课程` evidence, the real textbook, Luna Max image observations, and PaddleOCR AI Studio output.
- Exclude 老人版课程、`8.5g`、数学摄像头 and adjacent projects. A manifest reference is not proof that a course teaches the item.
- Reconstruct the actual textbook structure before naming blocks. Knowledge with adjacent examples, type examples with their variants, and reinforcement exercises are common patterns, not a template that may overrule the page.
- Cover every canonical item exactly once. Never create, omit, merge, duplicate, renumber, or move an item across sections.
- Treat `student_learning_items.json` as the source for worked examples and direct variants; treat `student_packet.json` as the source for A/B/C exercise text. Never infer exercise text from a count or title.
- Resolve legacy image references through the active chapter OCR image directory. A question is visually complete only when its referenced image file exists, its visual evidence is present, and the path is recorded in the context audit.
- Treat `data/course_transcripts/*.json.full_text` as the teacher-method source. Course titles prove nothing about what the teacher taught.
- Keep learner-facing artifacts answer-free. Never expose `answer_sidecar.json`, worked solutions for target attempts, correct options, or final results.
- For every numbered item, provide exact course calls, recognition cues, first written line, continuation actions, likely blockers, correction prompts, and independent self-checks.
- Keep course coverage, scheduled learning, simulated completion, and real-user completion separate. A route reference is not proof that a course was learned.
- Mark a course as new only at its first use in the active chapter route. Within a cycle, still list every already-learned course the item calls.
- Treat section 1.1 as the golden workflow sample. Do not fan out to other sections until 1.1 passes the current schema and semantic validator.
- Prefer Luna/Paddle cross-check evidence. When a current capability probe proves the Luna host cannot consume images, use the READY-bound, exact-image-SHA GLM vision sidecar plus PaddleOCR and record Luna as `blocked`; never relabel fallback evidence as Luna. A visual item is unusable without one of these current immutable paths.
- Keep the fixed five-persona suite as an internal route stress test. It does not model the current user.
- After section routes are merged, run one sequential `primary-user-proxy` across the chapter. Start with only a zero-base assumption and update its persistent profile only from frozen attempt evidence.
- Every simulated attempt must preserve the learner's actual course call, recognition statement, first line, continuation attempt, and self-check. Boolean-only simulation is invalid.
- Keep route stress testing, the growing learner, independent verification, human learning, and 24-hour cold retest separate. Human and 24-hour gates remain `not_run` unless real evidence exists.
- For the real learner, use the remote math MCP as the live state authority. A browser `localStorage` flag or a conversation statement is not cloud progress until an idempotent MCP write succeeds.
- After the learner confirms an error, blocker, or hint dependency, call `math_record_wrong_question` so the diagnostic and type classification advance together. Do not turn speech-recognition mistakes or model guesses into wrong-question records.
- When the learner asks for current wrong questions, call `math_export_wrong_questions`; report its live generation time, covered/deferred cycles, error status, type clusters, memory points, and retest actions. Do not reconstruct the report from chat memory.
- A skipped cycle is `deferred`, never `completed`. Use `math_defer_cycle` after explicit user confirmation and advance `current_task` to the named next cycle.
- Preserve `passed`, `failed`, `blocked`, `not_run`, `unknown`, and `stale` as distinct states.
- Never call a section “资料不足” because `human_learning_status=not_started`. `not_started` means learning has not happened; it is not a source defect.
- Never call a chapter statically complete unless `sections=11`, `canonical_items=401`, `complete_sections=11`, `all_question_content_complete=true`, `all_visual_assets_present=true`, and `all_teacher_transcripts_ready=true` for the active first-two-chapter audit.

## Section Workflow

0. Run the context audit and stop if the relevant section is `partial` or `missing`.
1. Verify the source snapshot and hashes named by the assignment. Stop with `stale` if they changed.
2. Reconcile the section manifest, OCR pages, packet, learning packet, `student_learning_items`, `student_packet`, and visual assets bidirectionally.
3. Read the complete section layout before choosing courses. Reconstruct the actual block boundaries and example/variant parentage from the page instead of forcing a universal order.
4. Read every assigned course transcript's `full_text`. Extract the teacher's definition, recognition cue, method order, terminology, and common warning for each mapped cycle.
5. Build the section overview: first course, later new courses, already-learned dependencies, and exact item labels in order.
6. Build each cycle in source order. Write the item method fields required by the output schema without copying question text or answers.
7. Record course coverage gaps separately from missing source files. If an advanced item has no dedicated transcript, mark the gap and add a bridge requirement; do not claim full teacher coverage.
8. Run five rounds with five zero-base personas per round. Every persona must attempt every section item; freeze each attempt before judging it.
9. When any persona cannot recognize the entry, write the first line, continue, or self-correct, revise the route and increment its version. Re-run the affected item for all five personas in the next round.
10. Run `scripts/validate_section_delivery.py` against the delivery. It must reject inconsistent failure lists, generic copied attempts, missing repair mappings, and boolean-only evidence.
11. Write detailed machine evidence and a compact learner-facing section report. Shared guidance belongs at cycle/type level; individual items show only their label and real deviations.

## Chapter Workflow

1. Merge validated section routes in textbook order and deduplicate required courses.
2. Initialize or load `data/learner_progress/chapter<chapter>.json`; never reset the learner profile between sections.
3. Let `primary-user-proxy` consume required course transcripts before attempting dependent items. Record course completion evidence separately from coverage.
4. Freeze each attempt before evaluation. Update the profile version only when the evidence adds a confirmed strength, gap, uncertainty, hint dependency, or self-check gap.
5. At chapter close, list unfinished required courses and unresolved items. Mark simulated chapter completion only when both lists are empty and the chapter progress validator passes.
6. Report real-user course completion and 24-hour retest independently; do not infer them from the proxy.
7. Keep browser-local, cloud real-user, and repository proxy progress separate. The HTML page may store stars, listened cycles, passed items, and questions in `localStorage`; after explicit confirmation, use MCP write tools to synchronize real events. A copied snapshot alone is not a successful cloud write.

## Delivery Rules

- Write only under the assignment directory, normally `reports/luna_sections/<task_id>/`.
- Required files are `delivery.json`, `learning_path_without_questions.md`, `learning_path_without_questions.html`, and `evidence.md`.
- Keep internal IDs in `delivery.json` for machine reconciliation. Do not show internal IDs such as `K1`, `LI...`, or `Q-...` in learner-facing Markdown/HTML.
- Do not paste per-persona or per-attempt traces into learner-facing files. Keep full item evidence in JSON while grouping shared method guidance at the smallest truthful textbook unit.
- Use UTF-8 without BOM for JSON/HTML and UTF-8 for Markdown. Use MathJax-compatible `\(...\)` and `\[...\]`; do not emit unmatched `$`.
- Do not edit shared manifests, OCR, packets, catalogs, visual sidecars, or another task's output. Report a shared-source defect instead.
- Do not upload the whole repository or commit private 8.5 conversation history to the public repository. ChatGPT uses GitHub for repository facts; the 8.5 file is an optional private project reference.
- ChatGPT assistance is MCP-first: read system status, current task, section, no-answer item/image, teacher transcript, and live progress. Use the three handout tools when the paired course handout is relevant, and inspect the returned source page image before relying on formulas or diagrams. `@GitHub` and `chapter12_complete_audit.json` are the static fallback/audit path. A response saying “已读取” is not audit evidence.

## Validate

Run:

```powershell
python codex-skill\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py `
  --project-root . `
  --assignment reports\luna_dispatch\assignments.json `
  --task-id <task-id> `
  --delivery reports\luna_sections\<task-id>\delivery.json

python codex-skill\ybt-all-chapters-learning-path\scripts\validate_chapter_learning_progress.py `
  --project-root . `
  --progress data\learner_progress\chapter<chapter>.json

python codex-skill\ybt-all-chapters-learning-path\scripts\build_chatgpt_context_audit.py `
  --project-root .
```

Return `passed` only when the validators pass, the context audit complete flags are true, and the assignment's current hashes still match. A model's own statement that it finished is never acceptance evidence.

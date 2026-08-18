---
name: ybt-all-chapters-learning-path
description: Build, audit, simulate, and iteratively refine full-book Chinese high-school mathematics 一本通 learning routes from Luna Max vision, PaddleOCR cross-checks, verified textbook sources, and the allowed local course corpus. Use for 一本通章节学习路径、1.1母版流程、课程覆盖、知识点到例题/变式/类型题/A-B-C顺序、逐题零基础学生模拟、缺题漏题审计、视觉与OCR交叉核验、无答案 Markdown/HTML 导出、多轮学习路径打磨，或 C:\开发\小工具\一本通学习系统_v7 的分节任务。
---

# 一本通全书学习路径

## Start

1. Treat current user words as authority. Treat old chats, reports, generated HTML, and claimed completion as untrusted until live files verify them.
2. Use `C:\开发\小工具\一本通学习系统_v7` as the default project root unless the task gives another root.
3. Read [workflow-contract.md](references/workflow-contract.md) before changing or judging a section.
4. Read [output-schema.md](references/output-schema.md) before writing a delivery.
5. Read [simulation-gates.md](references/simulation-gates.md) before running learner simulation.
6. Read [ocr-vision-crosscheck.md](references/ocr-vision-crosscheck.md) before consuming OCR or diagrams.
7. Stay inside the assignment's exact sections and write scope. Other tasks share the same filesystem.

## Non-Negotiable Invariants

- Allow only the ordered `Downloads\课程合集` corpus, mathematical `8.5` and `8.5课程` evidence, the real textbook, Luna Max image observations, and PaddleOCR AI Studio output.
- Exclude 老人版课程、`8.5g`、数学摄像头 and adjacent projects. A manifest reference is not proof that a course teaches the item.
- Preserve the textbook learning order: knowledge point -> adjacent worked example -> direct variant -> type example -> A/B/C exercise.
- Cover every canonical item exactly once. Never create, omit, merge, duplicate, renumber, or move an item across sections.
- Keep learner-facing artifacts answer-free. Never expose `answer_sidecar.json`, worked solutions for target attempts, correct options, or final results.
- For every numbered item, provide exact course calls, recognition cues, first written line, continuation actions, likely blockers, correction prompts, and independent self-checks.
- Mark a course as new only at its first use in the final global route. Within a cycle, still list every already-learned course the item calls.
- Treat section 1.1 as the golden workflow sample. Do not fan out to other sections until 1.1 passes the current schema and semantic validator.
- Prefer Luna/Paddle cross-check evidence. When a current capability probe proves the Luna host cannot consume images, use the READY-bound, exact-image-SHA GLM vision sidecar plus PaddleOCR and record Luna as `blocked`; never relabel fallback evidence as Luna. A visual item is unusable without one of these current immutable paths.
- Every simulated attempt must preserve the learner's actual course call, recognition statement, first line, continuation attempt, and self-check. Boolean-only simulation is invalid.
- Keep proxy simulation, independent verification, human learning, and 24-hour cold retest separate. Human and 24-hour gates remain `not_run` unless real evidence exists.
- Preserve `passed`, `failed`, `blocked`, `not_run`, `unknown`, and `stale` as distinct states.

## Section Workflow

1. Verify the source snapshot and hashes named by the assignment. Stop with `stale` if they changed.
2. Reconcile the section manifest, OCR pages, packet, learning packet, and visual sidecars bidirectionally.
3. Read the complete section layout before choosing courses. Identify left-column knowledge blocks, adjacent examples, direct variants, type blocks, then A/B/C groups.
4. Read the assigned course transcripts. Map specific transcript methods to cycles and items; do not rely on titles alone.
5. Build the section overview: first course, later new courses, already-learned dependencies, and exact item labels in order.
6. Build each cycle in source order. Write the item method fields required by the output schema without copying question text or answers.
7. Run five rounds with five zero-base personas per round. Every persona must attempt every section item; freeze each attempt before judging it.
8. When any persona cannot recognize the entry, write the first line, continue, or self-correct, revise the route and increment its version. Re-run the affected item for all five personas in the next round.
9. Run `scripts/validate_section_delivery.py` against the delivery. It must reject inconsistent failure lists, generic copied attempts, missing repair mappings, and boolean-only evidence.
10. Write a concise section report with exact hashes, coverage counts, route versions, simulation results, and unresolved evidence states.

## Delivery Rules

- Write only under the assignment directory, normally `reports/luna_sections/<task_id>/`.
- Required files are `delivery.json`, `learning_path_without_questions.md`, `learning_path_without_questions.html`, and `evidence.md`.
- Keep internal IDs in `delivery.json` for machine reconciliation. Do not show internal IDs such as `K1`, `LI...`, or `Q-...` in learner-facing Markdown/HTML.
- Use UTF-8 without BOM for JSON/HTML and UTF-8 for Markdown. Use MathJax-compatible `\(...\)` and `\[...\]`; do not emit unmatched `$`.
- Do not edit shared manifests, OCR, packets, catalogs, visual sidecars, or another task's output. Report a shared-source defect instead.

## Validate

Run:

```powershell
python C:\Users\poyi\.codex\skills\ybt-all-chapters-learning-path\scripts\validate_section_delivery.py `
  --project-root C:\开发\小工具\一本通学习系统_v7 `
  --assignment reports\luna_dispatch\assignments.json `
  --task-id <task-id> `
  --delivery reports\luna_sections\<task-id>\delivery.json
```

Return `passed` only when the validator passes and the assignment's current hashes still match. A model's own statement that it finished is never acceptance evidence.

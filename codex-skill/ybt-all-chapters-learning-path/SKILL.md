---
name: ybt-all-chapters-learning-path
description: Build, audit, simulate, and refine Chinese high-school mathematics 一本通 learning routes from verified textbook/OCR evidence and the approved course transcripts. Use for 一本通第一、二章优先打磨、按真实版面重建知识点/例题/变式/强化训练、课程覆盖与完成账本、持续成长零基础用户模拟、固定人格压力测试、缺题漏题审计、视觉交叉核验和紧凑无答案 Markdown/HTML 交付。
---

# 一本通学习路径

## Start

1. Treat current user words as authority. Treat old chats, reports, generated HTML, and claimed completion as untrusted until live files verify them.
2. Resolve the project root from the current repository or the task's explicit path. Do not depend on an old device path.
3. Read [workflow-contract.md](references/workflow-contract.md) before changing or judging a section.
4. Read [output-schema.md](references/output-schema.md) before writing a delivery.
5. Read [simulation-gates.md](references/simulation-gates.md) before running learner simulation.
6. Read [ocr-vision-crosscheck.md](references/ocr-vision-crosscheck.md) before consuming OCR or diagrams.
7. Read [product requirements](../../docs/PRODUCT-REQUIREMENTS.md) when it exists. Chapters 1 and 2 are the default active scope unless the user explicitly expands it.
8. Stay inside the assignment's exact sections and write scope. Other tasks may share the same filesystem.

## Non-Negotiable Invariants

- Allow only the ordered `Downloads\课程合集` corpus, mathematical `8.5` and `8.5课程` evidence, the real textbook, Luna Max image observations, and PaddleOCR AI Studio output.
- Exclude 老人版课程、`8.5g`、数学摄像头 and adjacent projects. A manifest reference is not proof that a course teaches the item.
- Reconstruct the actual textbook structure before naming blocks. Knowledge with adjacent examples, type examples with their variants, and reinforcement exercises are common patterns, not a template that may overrule the page.
- Cover every canonical item exactly once. Never create, omit, merge, duplicate, renumber, or move an item across sections.
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
- Preserve `passed`, `failed`, `blocked`, `not_run`, `unknown`, and `stale` as distinct states.

## Section Workflow

1. Verify the source snapshot and hashes named by the assignment. Stop with `stale` if they changed.
2. Reconcile the section manifest, OCR pages, packet, learning packet, and visual sidecars bidirectionally.
3. Read the complete section layout before choosing courses. Reconstruct the actual block boundaries and example/variant parentage from the page instead of forcing a universal order.
4. Read the assigned course transcripts. Map specific transcript methods to cycles and items; do not rely on titles alone.
5. Build the section overview: first course, later new courses, already-learned dependencies, and exact item labels in order.
6. Build each cycle in source order. Write the item method fields required by the output schema without copying question text or answers.
7. Run five rounds with five zero-base personas per round. Every persona must attempt every section item; freeze each attempt before judging it.
8. When any persona cannot recognize the entry, write the first line, continue, or self-correct, revise the route and increment its version. Re-run the affected item for all five personas in the next round.
9. Run `scripts/validate_section_delivery.py` against the delivery. It must reject inconsistent failure lists, generic copied attempts, missing repair mappings, and boolean-only evidence.
10. Write detailed machine evidence and a compact learner-facing section report. Shared guidance belongs at cycle/type level; individual items show only their label and real deviations.

## Chapter Workflow

1. Merge validated section routes in textbook order and deduplicate required courses.
2. Initialize or load `data/learner_progress/chapter<chapter>.json`; never reset the learner profile between sections.
3. Let `primary-user-proxy` consume required course transcripts before attempting dependent items. Record course completion evidence separately from coverage.
4. Freeze each attempt before evaluation. Update the profile version only when the evidence adds a confirmed strength, gap, uncertainty, hint dependency, or self-check gap.
5. At chapter close, list unfinished required courses and unresolved items. Mark simulated chapter completion only when both lists are empty and the chapter progress validator passes.
6. Report real-user course completion and 24-hour retest independently; do not infer them from the proxy.

## Delivery Rules

- Write only under the assignment directory, normally `reports/luna_sections/<task_id>/`.
- Required files are `delivery.json`, `learning_path_without_questions.md`, `learning_path_without_questions.html`, and `evidence.md`.
- Keep internal IDs in `delivery.json` for machine reconciliation. Do not show internal IDs such as `K1`, `LI...`, or `Q-...` in learner-facing Markdown/HTML.
- Do not paste per-persona or per-attempt traces into learner-facing files. Keep full item evidence in JSON while grouping shared method guidance at the smallest truthful textbook unit.
- Use UTF-8 without BOM for JSON/HTML and UTF-8 for Markdown. Use MathJax-compatible `\(...\)` and `\[...\]`; do not emit unmatched `$`.
- Do not edit shared manifests, OCR, packets, catalogs, visual sidecars, or another task's output. Report a shared-source defect instead.

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
```

Return `passed` only when the validator passes and the assignment's current hashes still match. A model's own statement that it finished is never acceptance evidence.

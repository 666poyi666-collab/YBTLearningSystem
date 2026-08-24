# Context Audit Contract

This reference governs whether the first two chapters can be described as fully readable by a learner assistant or ChatGPT.

## Source map

For each active section:

- Section structure and knowledge labels: `chapter<chapter>_manifest.json`.
- Teaching examples and direct variants: `data/packets/<section>/student_learning_items.json`.
- A/B/C exercise question text: `data/packets/<section>/student_packet.json`.
- Cycle/course assignment: validated section delivery plus manifest learning cycles.
- Teacher method: every `course_refs` entry mapped through `data/all_chapters_course_catalog.json` to `data/course_transcripts/<video stem>.json`, then read `full_text`.
- Diagrams: `image_refs[*].ref` basename resolved under `data/ocr_live_current/first_chapter_69/imgs` for chapter 1 and `data/ocr_live_current/second_chapter_109/imgs` for chapter 2.
- Repository learner ledger: `data/learner_progress/chapter<chapter>.json`.
- Browser live learner state: HTML `localStorage`, exported only by the page's `复制进度` action.
- Cloud real-learner state: remote math MCP `learner_state` and idempotent `learning_events`; this is authoritative after a successful write.
- Paired course handouts: `math_search_handout` for OCR location, `math_get_course_handout` for candidate page mapping, and `math_get_handout_page` for source-page visual verification. OCR alone is not formula or diagram authority.

## Required audit command

```powershell
python codex-skill\ybt-all-chapters-learning-path\scripts\build_chatgpt_context_audit.py --project-root .
```

The command writes:

- `data/chatgpt_context/chapter12_complete_audit.json`
- `data/chatgpt_context/chapter12_complete_audit.md`

For the current active scope, static completeness requires:

```text
sections = 11
canonical_items = 401
complete_sections = 11
partial_sections = 0
all_question_content_complete = true
all_visual_assets_present = true
all_teacher_transcripts_ready = true
catalog_courses = 170
transcript_files = 170
catalog_transcripts_present = 170
```

The audit also records SHA-256 values for the manifest, learning packet, student items, student packet, progress file, and every bound transcript. A hash mismatch is `stale`, not `complete`.

## ChatGPT retrieval contract

ChatGPT should use the remote math MCP first and the GitHub connection as a static fallback/audit source. It does not need the whole repository pasted into one prompt, and a one-shot answer cannot prove that all files were loaded into context.

Before teaching a current item, ChatGPT must:

1. Read MCP system status, current task, section overview, and live progress.
2. Read the current no-answer item and every referenced diagram.
3. Read every bound course transcript `full_text`.
4. When the paired handout is useful, search it and then read the exact source-page image; OCR text is location evidence only.
5. Explain using the teacher transcript's definitions, recognition cues, method order, and terminology.
6. After a confirmed error/blocker, write its diagnostic and type through `math_record_wrong_question`; on request, export the live report through `math_export_wrong_questions`.
7. If MCP is unavailable, read the audit JSON and use GitHub sources. Never infer live progress from initialized repository JSON or an unsynchronized browser snapshot.

If any required path is unreadable, ChatGPT must name the exact path and mark the current explanation `资料不足` or `课程覆盖缺口`. It must not silently use a title, stale summary, answer sidecar, or another persona's attempt.

## Completion vocabulary

- `static_complete`: source files, question text, diagrams, course transcripts, and hashes close.
- `route_complete`: every item has a source-derived cycle and course route.
- `human_not_started`: real learner has no attempt evidence yet.
- `proxy_complete`: primary-user-proxy completed its separate evidence contract.
- `cold_retest_not_run`: no 24-hour evidence exists.

`human_not_started` is not a source defect. `proxy_complete` is not human completion.

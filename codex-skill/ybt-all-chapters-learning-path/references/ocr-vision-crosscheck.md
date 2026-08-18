# OCR And Vision Cross-Check

## Purpose

Prefer Luna Max vision and PaddleOCR AI Studio as independent observations of the same immutable textbook image. The original image is the final authority. Never infer image access from a model name.

If a current Luna capability probe explicitly returns `image content omitted because you do not support image input` or an equivalent host error, use the READY-bound `glm-4.6v-flash` structured sidecar plus PaddleOCR as the transparent fallback. Record Luna as `blocked`; never rename GLM evidence as Luna.

## Evidence Sources

- Luna Max vision: reconstruct page layout, diagram objects, visible relations, labels, formula structure, and uncertainties.
- PaddleOCR AI Studio: preserve text blocks, question numbers, formula tokens, coordinates, and page ordering.
- Original image crop: resolve every disagreement.

Do not use stale GLM rows, answer-book OCR, or neighboring projects. A GLM fallback row is valid only when the global sidecar SHA equals the assignment source binding, the original image SHA matches, the row is `passed`, and its structured observation is answer-free.

## Capability Probe

Before accepting Luna evidence:

1. Submit one source-bound textbook image to the assigned Luna Max worker.
2. Require the returned observation to name visible labels and relations that are not present in the text-only task prompt.
3. Record the image SHA, runtime model, reasoning effort, observation hash, and timestamp.
4. Mark `luna_vision=blocked` when the worker cannot prove image consumption. Do not silently fall back while claiming Luna vision.

## Cross-Check Record

For every OCR page and visual item record:

```json
{
  "image": "absolute source path",
  "image_sha256": "...",
  "paddle": {
    "status": "passed|blocked|not_run|stale",
    "artifact": "...",
    "artifact_sha256": "...",
    "text": [],
    "coordinates": []
  },
  "luna": {
    "status": "passed|blocked|not_run|stale",
    "model": "combo/protect-luna",
    "reasoning_effort": "max",
    "objects": [],
    "relations": [],
    "coordinates": [],
    "ranges": [],
    "text": [],
    "uncertainties": []
  },
  "conflicts": [],
  "adjudication": [],
  "status": "passed|blocked|failed|stale"
}
```

## Decision Rules

- Accept text only when question labels and formulas reconcile with the original image.
- Accept a diagram only when Luna reports meaningful objects and relations from the actual image.
- Keep Paddle and Luna differences as explicit conflicts; never merge incompatible observations silently.
- Resolve a conflict by citing the original image region and the chosen literal reading.
- Block the item when a material label, formula, relation, range, or page boundary remains uncertain.
- Keep the evidence answer-free. Do not infer a correct option or final result from a diagram.
- Use `mode=luna_paddle_crosscheck` when Luna consumed the image.
- Use `mode=paddle_glm_crosscheck` only after a current Luna host capability failure and preserve `luna_status=blocked`, `visual_status=passed`, and `visual_model=glm-4.6v-flash`.

## Section Gate

Set `ocr_vision.status=passed` only when all images used by the section are current and all material conflicts are adjudicated. The primary path requires a passed Luna capability probe; the fallback path requires a recorded Luna capability failure plus current exact-SHA GLM/Paddle evidence. Text-only sections may use Paddle text plus a current page-layout sample.

Write the records to `ocr_vision_crosscheck.json` in the task output directory using schema `ybt-ocr-vision-crosscheck-v1`. Reference its project-relative path and SHA from every covered section. Every image SHA in a section delivery must appear exactly once for that section in the evidence file.

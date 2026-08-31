#!/usr/bin/env python3
"""Build immutable, answer-free visual sidecars for all chapter images."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ybt_learning.vision import (  # noqa: E402
    GLM_VISION_MODEL,
    VISION_PROMPT,
    describe_image,
    structured_answer_leaks,
    structured_visual_errors,
)


REQUIRED_ARRAY_FIELDS = (
    "objects",
    "relations",
    "coordinates",
    "ranges",
    "text",
    "uncertainties",
)

COMPACT_RECOVERY_PROMPT = VISION_PROMPT + (
    "\n\n难图恢复模式：必须输出完整JSON且六个数组均存在。"
    "objects最多2项，relations最多4项，coordinates最多2项，ranges最多2项，"
    "text最多2项，uncertainties最多2项。"
    "多个点名、黑点、顶点或坐标标签必须合并到一个逗号分隔字符串中，"
    "不得把每个点、每个网格节点、每条边分别列项。"
    "照片也必须按可见场景填写objects和relations，不得返回全空数组。"
    "仍然禁止解题、推导、选项判断和答案。"
)


@dataclass(frozen=True)
class VisionTarget:
    index: int
    section: str
    kind: str
    item_id: str
    label: str
    question_hint: str
    image: Path
    image_sha256: str
    source_docs: tuple[int, ...]

    @property
    def key(self) -> tuple[str, str]:
        return self.question_hint, self.image_sha256


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _is_answer_book_path(path: Path) -> bool:
    value = str(path).lower()
    return ("答案册" in value and "无答案册" not in value) or any(
        marker in value for marker in ("answer_book", "answer-book", "answerbook")
    )


def load_targets(inventory_path: Path) -> tuple[list[VisionTarget], str]:
    inventory = load_json(inventory_path)
    rows = inventory.get("items")
    if not isinstance(rows, list):
        raise ValueError("visual inventory has no items list")
    targets: list[VisionTarget] = []
    seen: set[tuple[str, str]] = set()
    for raw_index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"visual inventory row {raw_index} is not an object")
        hint = str(row.get("question_hint") or "").strip()
        image = Path(str(row.get("image") or ""))
        if not hint:
            raise ValueError(f"visual inventory row {raw_index} has no question_hint")
        if _is_answer_book_path(image):
            raise ValueError(f"answer-book image is forbidden: {image}")
        if not image.is_file():
            raise FileNotFoundError(f"visual inventory image is missing: {image}")
        digest = sha256_file(image)
        key = hint, digest
        if key in seen:
            raise ValueError(f"duplicate visual target: {hint} {digest}")
        seen.add(key)
        source_docs = tuple(
            int(value) for value in (row.get("source_docs") or []) if value is not None
        )
        targets.append(
            VisionTarget(
                index=raw_index,
                section=str(row.get("section") or ""),
                kind=str(row.get("kind") or ""),
                item_id=str(row.get("item_id") or ""),
                label=str(row.get("label") or ""),
                question_hint=hint,
                image=image,
                image_sha256=digest,
                source_docs=source_docs,
            )
        )
    declared_count = int(inventory.get("item_image_count", len(targets)))
    declared_unique = int(inventory.get("unique_image_count", len(targets)))
    if declared_count != len(targets):
        raise ValueError(
            f"visual inventory count drift: declared={declared_count}, actual={len(targets)}"
        )
    if declared_unique != len({target.image_sha256 for target in targets}):
        raise ValueError("visual inventory unique-image count drift")
    return targets, sha256_file(inventory_path)


def _meaningful(structured: dict[str, Any]) -> bool:
    return any(structured.get(key) not in (None, "", [], {}) for key in REQUIRED_ARRAY_FIELDS[:-1])


def row_errors(row: dict[str, Any], target: VisionTarget) -> list[str]:
    errors: list[str] = []
    if row.get("status") != "passed":
        errors.append("status_not_passed")
    if row.get("model") != GLM_VISION_MODEL:
        errors.append("model_mismatch")
    if row.get("confidence") not in {"E1", "E2"}:
        errors.append("confidence_not_release_grade")
    if row.get("question_hint") != target.question_hint:
        errors.append("question_hint_mismatch")
    if row.get("image_sha256") != target.image_sha256:
        errors.append("image_hash_mismatch")
    if Path(str(row.get("image") or "")) != target.image:
        errors.append("image_path_mismatch")
    structured = row.get("structured")
    if not isinstance(structured, dict):
        errors.append("structured_payload_missing")
        return errors
    for key in REQUIRED_ARRAY_FIELDS:
        if not isinstance(structured.get(key), list):
            errors.append(f"{key}_not_array")
        elif len(structured[key]) > 8:
            errors.append(f"{key}_too_many_items")
    if structured.get("confidence") != row.get("confidence"):
        errors.append("nested_confidence_mismatch")
    if not _meaningful(structured):
        errors.append("empty_structured_payload")
    if structured_answer_leaks(structured):
        errors.append("answer_language_in_visual_sidecar")
    errors.extend(structured_visual_errors(structured, item_id=target.item_id))
    return errors


def _result_row(target: VisionTarget, result: dict[str, Any], attempt: int) -> dict[str, Any]:
    structured = result.get("structured")
    confidence = result.get("confidence") or (
        structured.get("confidence") if isinstance(structured, dict) else "E0"
    )
    row: dict[str, Any] = {
        "status": result.get("status", "failed"),
        "section": target.section,
        "kind": target.kind,
        "item_id": target.item_id,
        "label": target.label,
        "question_hint": target.question_hint,
        "image": str(target.image),
        "image_sha256": target.image_sha256,
        "source_docs": list(target.source_docs),
        "confidence": confidence,
        "model": result.get("model"),
        "elapsed_ms": result.get("elapsed_ms"),
        "attempt": attempt,
    }
    if isinstance(structured, dict):
        row["structured"] = structured
    if result.get("error"):
        row["error"] = str(result["error"])[-2000:]
    if sha256_file(target.image) != target.image_sha256:
        row["status"] = "failed"
        row["error"] = "image_changed_during_visual_call"
    errors = row_errors(row, target)
    if errors:
        row["status"] = "failed" if result.get("status") == "failed" else "unverified"
        row["validation_errors"] = errors
    return row


def _retry_prompt(
    error: str | None,
    attempt: int,
    *,
    previous_prompt: str | None = None,
) -> str:
    """Tighten the next request without weakening any release gate."""
    error = (error or "unknown_visual_error").strip()
    array_error_field = next(
        (
            field
            for field in REQUIRED_ARRAY_FIELDS
            if error in {f"{field}_too_many_items", f"{field}_not_array"}
        ),
        None,
    )
    known_errors = {
        "empty_structured_vision",
        "empty_vision_caption",
        "answer_language_in_visual_sidecar",
        "malformed_structured_vision",
        "truncated_fenced_vision",
        "vision_payload_not_object",
        "confidence_template_not_a_result",
    }
    public_error = error if error in known_errors or array_error_field else "provider_or_transport_error"
    base_prompt = previous_prompt or VISION_PROMPT
    common = (
        f"\n\n这是第{attempt}次请求。上一轮未通过机器校验：{public_error}。"
        "仍须遵守上面的无答案规则，不得解题、推导、判断选项或给结论。"
    )
    compact = (
        "强制紧凑模式：每个数组最多4项，全部数组合计最多16项；"
        "多个点名合并为一个逗号分隔字符串，连续流程合并为一个带箭头的有序字符串。"
        if attempt >= 3
        else ""
    )
    if array_error_field and error.endswith("_too_many_items"):
        return base_prompt + common + (
            f"这次重点修正：{array_error_field}数组最多6项；六个数组都最多6项。"
            "同一对象的名称和位置合并为一个短字符串，流程图每个框算一项，"
            "只保留理解图形所需的关键元素。只输出JSON。"
        ) + compact
    if error in {"empty_structured_vision", "empty_vision_caption"}:
        return base_prompt + common + (
            "这次先逐字辨认坐标轴、点名、线段、框内短文或表格标题，再填JSON。"
            "若图片确实模糊，把看不清的内容写入uncertainties并设E0；"
            "只要能看见任一元素，就不得把全部内容数组留空。只输出JSON。"
        ) + compact
    if error == "answer_language_in_visual_sidecar":
        return base_prompt + common + (
            "上一轮含有答案或解法措辞；这次删除所有正确/错误、应选、所以、因此、"
            "可得、答案、结果、结论等判断，只保留图中可见对象和原样短文字。只输出JSON。"
        ) + compact
    if error in {
        "malformed_structured_vision",
        "truncated_fenced_vision",
        "vision_payload_not_object",
        "confidence_template_not_a_result",
    } or (array_error_field is not None and error.endswith("_not_array")):
        return base_prompt + common + (
            "这次必须输出一个完整、单行、无Markdown围栏的JSON对象；"
            "六个指定字段必须都是数组，confidence必须是E2、E1或E0中的一个。"
        ) + compact
    return (
        base_prompt
        + common
        + "重新观察图片后只输出符合固定字段的单行JSON。"
        + compact
    )


def _is_semantic_validation_error(error: str | None) -> bool:
    error = error or ""
    return (
        any(
            error in {f"{field}_too_many_items", f"{field}_not_array"}
            for field in REQUIRED_ARRAY_FIELDS
        )
        or error
        in {
            "empty_structured_vision",
            "empty_vision_caption",
            "answer_language_in_visual_sidecar",
            "malformed_structured_vision",
            "truncated_fenced_vision",
            "vision_payload_not_object",
            "confidence_template_not_a_result",
        }
    )


def _is_rate_limit_error(error: str | None) -> bool:
    value = (error or "").lower()
    return "429" in value or "限流" in value or "rate limit" in value


def _call_with_retries(
    target: VisionTarget,
    *,
    profile: str | None,
    max_tokens: int,
    rounds: int,
    base_backoff_sec: float,
    initial_prompt: str | None = None,
    describe: Callable[..., dict[str, Any]] = describe_image,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    attempts: list[dict[str, Any]] = []
    final: dict[str, Any] | None = None
    prompt = initial_prompt or VISION_PROMPT
    for attempt in range(1, rounds + 1):
        result = describe(
            target.image,
            profile=profile,
            prompt=prompt,
            max_tokens=max_tokens,
        )
        final = _result_row(target, result, attempt)
        attempts.append(
            {
                "attempt": attempt,
                "status": final.get("status"),
                "confidence": final.get("confidence"),
                "error": final.get("error"),
                "validation_errors": final.get("validation_errors", []),
                "elapsed_ms": final.get("elapsed_ms"),
            }
        )
        if not row_errors(final, target):
            break
        error = str(result.get("error") or "unknown_visual_error")
        prompt = _retry_prompt(error, attempt + 1, previous_prompt=prompt)
        if attempt < rounds and base_backoff_sec > 0:
            # Formatting/content corrections do not benefit from a long
            # exponential pause. Transport and provider failures still do.
            if _is_semantic_validation_error(error):
                delay = min(base_backoff_sec, 2.0)
            elif _is_rate_limit_error(error):
                # The free GLM endpoint already retries internally. A fixed
                # cooldown prevents all workers from sleeping for minutes.
                delay = max(base_backoff_sec, 15.0)
            else:
                delay = base_backoff_sec * (2 ** (attempt - 1))
            time.sleep(delay)
    assert final is not None
    return final, attempts


def _current_rows(path: Path, targets: list[VisionTarget]) -> dict[tuple[str, str], dict[str, Any]]:
    if not path.is_file():
        return {}
    payload = load_json(path)
    target_by_key = {target.key: target for target in targets}
    current: dict[tuple[str, str], dict[str, Any]] = {}
    for row in payload.get("results", []):
        if not isinstance(row, dict):
            continue
        key = str(row.get("question_hint") or ""), str(row.get("image_sha256") or "")
        target = target_by_key.get(key)
        if target is not None and not row_errors(row, target):
            current[key] = row
    return current


def _previous_attempted_keys(path: Path) -> set[tuple[str, str]]:
    if not path.is_file():
        return set()
    payload = load_json(path)
    attempted: set[tuple[str, str]] = set()
    for collection in (payload.get("results", []), payload.get("attempt_log", [])):
        if not isinstance(collection, list):
            continue
        for row in collection:
            if not isinstance(row, dict):
                continue
            key = str(row.get("question_hint") or ""), str(row.get("image_sha256") or "")
            if all(key):
                attempted.add(key)
    return attempted


def _prioritize_pending(
    pending: list[VisionTarget],
    attempted: set[tuple[str, str]],
) -> list[VisionTarget]:
    """Process unseen images before repeatedly difficult rows."""
    return sorted(pending, key=lambda target: (target.key in attempted, target.index))


def _payload(
    targets: list[VisionTarget],
    rows: dict[tuple[str, str], dict[str, Any]],
    attempts: list[dict[str, Any]],
    inventory_path: Path,
    inventory_sha256: str,
) -> dict[str, Any]:
    passed_count = sum(
        not row_errors(rows[target.key], target)
        for target in targets
        if target.key in rows
    )
    return {
        "schema_version": "7.2",
        "status": "passed" if passed_count == len(targets) else "unverified",
        "provider": "GLM-4.6V-Flash via deepseek-eyes",
        "model": GLM_VISION_MODEL,
        "inventory_path": str(inventory_path),
        "inventory_sha256": inventory_sha256,
        "target_count": len(targets),
        "passed_count": passed_count,
        "failed_count": len(targets) - passed_count,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "results": [rows[target.key] for target in targets if target.key in rows],
        "attempt_log": attempts,
        "consumer_guard": (
            "Only immutable-image, exact-model, answer-free E1/E2 structured rows may enter packets."
        ),
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def run_batch(
    inventory_path: Path,
    output_path: Path,
    *,
    workers: int = 3,
    rounds: int = 4,
    base_backoff_sec: float = 15,
    max_tokens: int = 1536,
    profile: str | None = None,
    start: int = 0,
    limit: int | None = None,
    initial_prompt: str | None = None,
    describe: Callable[..., dict[str, Any]] = describe_image,
) -> dict[str, Any]:
    all_targets, inventory_sha256 = load_targets(inventory_path)
    end = None if limit is None else start + limit
    targets = all_targets[start:end]
    if not targets:
        raise ValueError("no visual targets selected")
    attempted = _previous_attempted_keys(output_path)
    rows = _current_rows(output_path, targets)
    pending = _prioritize_pending(
        [target for target in targets if target.key not in rows],
        attempted,
    )
    attempt_log: list[dict[str, Any]] = []
    if output_path.is_file():
        previous = load_json(output_path)
        if isinstance(previous.get("attempt_log"), list):
            attempt_log.extend(previous["attempt_log"])
    atomic_write_json(
        output_path,
        _payload(targets, rows, attempt_log, inventory_path, inventory_sha256),
    )
    print(
        json.dumps(
            {
                "targets": len(targets),
                "resumed": len(targets) - len(pending),
                "pending": len(pending),
                "previously_attempted_pending": sum(target.key in attempted for target in pending),
                "workers": workers,
                "output": str(output_path),
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                _call_with_retries,
                target,
                profile=profile,
                max_tokens=max_tokens,
                rounds=rounds,
                base_backoff_sec=base_backoff_sec,
                initial_prompt=initial_prompt,
                describe=describe,
            ): target
            for target in pending
        }
        for future in as_completed(futures):
            target = futures[future]
            try:
                row, attempts = future.result()
            except Exception as exc:  # Fail closed while preserving resume state.
                row = {
                    "status": "failed",
                    "section": target.section,
                    "kind": target.kind,
                    "item_id": target.item_id,
                    "label": target.label,
                    "question_hint": target.question_hint,
                    "image": str(target.image),
                    "image_sha256": target.image_sha256,
                    "source_docs": list(target.source_docs),
                    "confidence": "E0",
                    "model": GLM_VISION_MODEL,
                    "error": f"unhandled_visual_error: {exc}",
                }
                attempts = [{"attempt": 0, "status": "failed", "error": str(exc)}]
            rows[target.key] = row
            attempt_log.append(
                {
                    "question_hint": target.question_hint,
                    "image_sha256": target.image_sha256,
                    "attempts": attempts,
                }
            )
            payload = _payload(
                targets,
                rows,
                attempt_log,
                inventory_path,
                inventory_sha256,
            )
            atomic_write_json(output_path, payload)
            print(
                json.dumps(
                    {
                        "index": target.index,
                        "question_hint": target.question_hint,
                        "image": target.image.name,
                        "status": row.get("status"),
                        "confidence": row.get("confidence"),
                        "passed_count": payload["passed_count"],
                        "target_count": payload["target_count"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    return _payload(targets, rows, attempt_log, inventory_path, inventory_sha256)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inventory",
        default=str(
            ROOT
            / "reports"
            / "all_chapters"
            / "visual-inventory-source-question-only.json"
        ),
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "data" / "vision_sidecar_all_chapters.json"),
    )
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--rounds", type=int, default=4)
    parser.add_argument("--base-backoff-sec", type=float, default=15)
    parser.add_argument("--max-tokens", type=int, default=1536)
    parser.add_argument("--profile", default=None)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--compact-recovery", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8:
        parser.error("--workers must be between 1 and 8")
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    report = run_batch(
        Path(args.inventory),
        Path(args.out),
        workers=args.workers,
        rounds=args.rounds,
        base_backoff_sec=args.base_backoff_sec,
        max_tokens=args.max_tokens,
        profile=args.profile,
        start=args.start,
        limit=args.limit,
        initial_prompt=COMPACT_RECOVERY_PROMPT if args.compact_recovery else None,
    )
    print(json.dumps({key: report[key] for key in ("status", "target_count", "passed_count", "failed_count")}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

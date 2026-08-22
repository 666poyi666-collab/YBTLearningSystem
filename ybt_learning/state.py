from __future__ import annotations

import copy
import hashlib
import json
from datetime import timedelta
from pathlib import Path
from typing import Any

from .common import now_iso, parse_time, save_json, stable_id


MASTERY_ORDER = {"U0": 0, "U1": 1, "CF": 2, "U2": 3, "U3": 3, "U4": 4, "U5": 5, "U6": 6, "U7": 7}
HINT_LEVELS = {"H0": 0, "H1": 1, "H2": 2, "H3": 3, "H4": 4}
VISUAL_STATUSES = {"READY_TEXT_ONLY", "VISION_VERIFIED", "NEEDS_VISION_SIDECAR", "UNVERIFIED"}


def target_key(target: dict[str, Any]) -> str:
    return json.dumps(target, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def new_main_state(target: dict[str, Any], *, now: str | None = None) -> dict[str, Any]:
    stamp = now or now_iso()
    return {
        "schema_version": "7.1",
        "main_state_id": "MAIN-0-" + stable_id(target_key(target), stamp, length=8),
        "route_revision": 0,
        "target_identity": copy.deepcopy(target),
        "active_batch": {"batch_id": None, "knowledge_unit": None, "item_ids": [], "completion_gate": None},
        "items": {},
        "blockers": [],
        "deferred": [],
        "contamination": [],
        "symbols": {},
        "open_loops": [],
        "course_local": {"merged_package_ids": [], "events": []},
        "rewards": {"points": 0, "badges": [], "grants": []},
        "audit": {"last_event_id": None, "last_updated": stamp},
    }


class StateError(ValueError):
    pass


class RewardLedger:
    """奖励与掌握轴分离；奖励事件带幂等键，防止重复刷分。"""

    RULES = {
        "full_pass": {"points": 10, "badge": "第一章·独立完整"},
        "near_transfer": {"points": 15, "badge": "第一章·近迁移"},
        "delayed_recall": {"points": 25, "badge": "第一章·冷复测"},
        "section_complete": {"points": 50, "badge": "第一章·小节通关"},
    }

    def __init__(self, state: dict[str, Any]):
        self.state = state
        self.state.setdefault("rewards", {"points": 0, "badges": [], "grants": []})

    def grant(self, *, scope: str, item_id: str | None, milestone: str, evidence: list[str], at: str | None = None) -> dict[str, Any] | None:
        if milestone not in self.RULES:
            raise StateError(f"unknown reward milestone: {milestone}")
        if not evidence:
            raise StateError("reward requires non-empty evidence")
        key = stable_id(scope, item_id or "", milestone)
        if any(g.get("idempotency_key") == key for g in self.state["rewards"]["grants"]):
            return None
        rule = self.RULES[milestone]
        grant = {
            "idempotency_key": key,
            "scope": scope,
            "item_id": item_id,
            "milestone": milestone,
            "points": rule["points"],
            "badge": rule["badge"],
            "evidence": list(evidence),
            "granted_at": at or now_iso(),
        }
        self.state["rewards"]["grants"].append(grant)
        self.state["rewards"]["points"] += rule["points"]
        if rule["badge"] not in self.state["rewards"]["badges"]:
            self.state["rewards"]["badges"].append(rule["badge"])
        return grant


class StateStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.events_path = self.path.with_name("events.jsonl")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.path.exists():
            self.state = json.loads(self.path.read_text(encoding="utf-8"))
        else:
            raise StateError(f"state file does not exist: {self.path}")

    @classmethod
    def create(cls, path: str | Path, target: dict[str, Any]) -> "StateStore":
        p = Path(path)
        save_json(p, new_main_state(target))
        return cls(p)

    def save(self) -> None:
        save_json(self.path, self.state)

    def _commit(self, event_type: str, payload: dict[str, Any], *, at: str | None = None) -> dict[str, Any]:
        stamp = at or now_iso()
        self.state["route_revision"] += 1
        self.state["main_state_id"] = "MAIN-" + str(self.state["route_revision"]) + "-" + stable_id(self.state["main_state_id"], event_type, stamp, length=8)
        event = {
            "event_id": "EVT-" + stable_id(self.state["main_state_id"], event_type, payload, stamp),
            "type": event_type,
            "at": stamp,
            "payload": copy.deepcopy(payload),
            "main_state_id": self.state["main_state_id"],
            "route_revision": self.state["route_revision"],
        }
        self.state["audit"] = {"last_event_id": event["event_id"], "last_updated": stamp}
        with self.events_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        self.save()
        return event

    def ensure_item(self, item_id: str, *, kind: str = "题目", section: str | None = None, source_anchor: dict | None = None) -> dict[str, Any]:
        if item_id not in self.state["items"]:
            self.state["items"][item_id] = {
                "item_id": item_id,
                "kind": kind,
                "section": section,
                "source_anchor": source_anchor or {},
                "parent_example_id": None,
                "stage": "L0",
                "batch_id": None,
                "progress_status": "NOT_TOUCHED",
                "mastery_status": "U0",
                "coverage_status": "NONE",
                "attempt": {
                    "independent": False,
                    "count": 0,
                    "first_break": None,
                    "process_verified": False,
                    "visual_status": "UNVERIFIED",
                },
                "exposure": {"hint_level_max": "H0", "answer_seen": False, "contaminated": False},
                "evidence": [],
                "release": {"entry_pass": False, "full_pass": False, "unlock_status": "LOCKED", "eligible_sets": []},
                "next_action": "独立尝试",
                "review_due": None,
                "review_history": [],
            }
        return self.state["items"][item_id]

    def set_batch(self, batch_id: str, knowledge_unit: str, item_ids: list[str], completion_gate: str) -> dict[str, Any]:
        if len(item_ids) > 5:
            raise StateError("one active batch may contain at most five items")
        self.state["active_batch"] = {
            "batch_id": batch_id,
            "knowledge_unit": knowledge_unit,
            "item_ids": list(item_ids),
            "completion_gate": completion_gate,
        }
        for item_id in item_ids:
            self.ensure_item(item_id)["batch_id"] = batch_id
        return self._commit("BATCH_SET", self.state["active_batch"])

    def record_attempt(
        self,
        item_id: str,
        *,
        independent: bool,
        result: str,
        hint_level: str = "H0",
        answer_seen: bool = False,
        process_verified: bool = False,
        first_break: str | None = None,
        section: str | None = None,
        source_anchor: dict | None = None,
        visual_status: str = "READY_TEXT_ONLY",
        at: str | None = None,
    ) -> dict[str, Any]:
        if hint_level not in HINT_LEVELS:
            raise StateError(f"invalid hint level: {hint_level}")
        if result not in {"correct", "incorrect", "partial", "guess"}:
            raise StateError(f"invalid result: {result}")
        if visual_status not in VISUAL_STATUSES:
            raise StateError(f"invalid visual status: {visual_status}")
        if visual_status == "VISION_VERIFIED":
            visual_evidence = (source_anchor or {}).get("visual_evidence")
            if visual_evidence not in {"E1", "E2"}:
                raise StateError("VISION_VERIFIED requires source_anchor.visual_evidence=E1 or E2")
        item = self.ensure_item(item_id, section=section, source_anchor=source_anchor)
        # Replaying an old attempt must not downgrade a later mastery state.
        # Keep an audit event, but do not mutate the verified item or grant again.
        if item.get("mastery_status") in {"U6", "U7"}:
            event = self._commit("ITEM_ATTEMPT_REPLAY_IGNORED", {"item_id": item_id, "result": result, "reason": "mastery_already_verified"}, at=at)
            return {"event": event, "item": copy.deepcopy(item), "granted": [], "idempotent": True}
        item["attempt"]["count"] += 1
        item["attempt"]["independent"] = bool(independent)
        item["attempt"]["process_verified"] = bool(process_verified)
        item["attempt"]["visual_status"] = visual_status
        if first_break:
            item["attempt"]["first_break"] = first_break
        item["exposure"]["hint_level_max"] = max(
            (hint_level, item["exposure"].get("hint_level_max", "H0")), key=lambda x: HINT_LEVELS[x]
        )
        item["exposure"]["answer_seen"] = bool(item["exposure"].get("answer_seen") or answer_seen)
        if HINT_LEVELS[hint_level] >= 1 or answer_seen or result == "guess":
            item["exposure"]["contaminated"] = True
            if item_id not in self.state["contamination"]:
                self.state["contamination"].append(item_id)
        visual_ok = visual_status in {"READY_TEXT_ONLY", "VISION_VERIFIED"}
        if result in {"partial", "incorrect"}:
            item["progress_status"] = "ATTEMPTED_PARTIAL"
        elif independent and result == "correct" and process_verified and visual_ok and not item["exposure"]["contaminated"]:
            item["progress_status"] = "INDEPENDENT_COMPLETE"
        elif independent and result == "correct" and process_verified and item["exposure"]["contaminated"]:
            item["progress_status"] = "ATTEMPTED_CONTAMINATED"
        elif independent and result == "correct" and process_verified and not visual_ok:
            item["progress_status"] = "ATTEMPTED_UNVERIFIED"
        else:
            item["progress_status"] = "ATTEMPTED_CONTAMINATED"
        item["stage"] = first_break or item.get("stage") or "L0"
        reward_ledger = RewardLedger(self.state)
        granted: list[dict] = []

        if result == "correct" and independent and process_verified and visual_ok and not item["exposure"]["contaminated"]:
            item["mastery_status"] = "U4"
            item["release"]["full_pass"] = True
            item["release"]["unlock_status"] = "FULL_PASS"
            evidence = ["independent_process", "uncontaminated"]
            if visual_status == "VISION_VERIFIED":
                evidence.append("visual_verified")
            grant = reward_ledger.grant(scope=section or item.get("section") or "chapter1", item_id=item_id, milestone="full_pass", evidence=evidence, at=at)
            if grant:
                granted.append(grant)
        elif result == "correct" and (not independent or not process_verified or not visual_ok or item["exposure"]["contaminated"]):
            item["mastery_status"] = "U3"
            item["release"]["unlock_status"] = "ENTRY_PASS"
            item["release"]["full_pass"] = False
        elif result == "partial":
            item["mastery_status"] = "CF" if independent else "U1"
        else:
            item["mastery_status"] = "CF" if independent else "U1"

        if item["mastery_status"] in {"U3", "U4", "U5"}:
            item["review_due"] = (parse_time(at) + timedelta(days=1)).isoformat()
            item["next_action"] = "到期后冷重做"

        event = self._commit("ITEM_ATTEMPT", {"item_id": item_id, "result": result, "granted": granted}, at=at)
        return {"event": event, "item": copy.deepcopy(item), "granted": granted}

    def record_near_variant(
        self,
        item_id: str,
        *,
        variant_item_id: str,
        independent: bool,
        result: str,
        process_verified: bool,
        visual_status: str = "READY_TEXT_ONLY",
        section: str | None = None,
        source_anchor: dict | None = None,
        at: str | None = None,
    ) -> dict[str, Any]:
        """Record a separate near-transfer attempt.

        A near-transfer reward cannot be asserted as a flag on the original
        attempt.  It requires a distinct item id, a separate event, and a
        clean, independently verified result.
        """
        if not variant_item_id or variant_item_id == item_id:
            raise StateError("near transfer requires a distinct variant_item_id")
        if result not in {"correct", "incorrect", "partial", "guess"}:
            raise StateError(f"invalid near variant result: {result}")
        if visual_status not in VISUAL_STATUSES:
            raise StateError(f"invalid visual status: {visual_status}")
        if visual_status == "VISION_VERIFIED" and (source_anchor or {}).get("visual_evidence") not in {"E1", "E2"}:
            raise StateError("VISION_VERIFIED requires source_anchor.visual_evidence=E1 or E2")
        original = self.ensure_item(item_id, section=section, source_anchor=source_anchor)
        variant = self.ensure_item(variant_item_id, section=section, source_anchor=source_anchor)
        if original.get("mastery_status") not in {"U4", "U5", "U6", "U7"} or not original.get("release", {}).get("full_pass"):
            raise StateError("near transfer requires original item full_pass")
        if variant.get("mastery_status") in {"U5", "U6", "U7"}:
            event = self._commit("NEAR_VARIANT_REPLAY_IGNORED", {"item_id": item_id, "variant_item_id": variant_item_id}, at=at)
            return {"event": event, "item": copy.deepcopy(original), "variant_item": copy.deepcopy(variant), "grant": None, "idempotent": True}
        variant["attempt"]["count"] += 1
        variant["attempt"]["independent"] = bool(independent)
        variant["attempt"]["process_verified"] = bool(process_verified)
        variant["attempt"]["visual_status"] = visual_status
        visual_ok = visual_status in {"READY_TEXT_ONLY", "VISION_VERIFIED"}
        clean = independent and process_verified and result == "correct" and visual_ok and not original["exposure"].get("contaminated")
        if clean:
            variant["mastery_status"] = "U5"
            variant["progress_status"] = "INDEPENDENT_COMPLETE"
            variant["release"]["full_pass"] = False
            variant["release"]["unlock_status"] = "ENTRY_PASS"
            variant["review_due"] = (parse_time(at) + timedelta(days=1)).isoformat()
            variant["next_action"] = "到期后冷重做"
            evidence = ["near_variant_independent", "distinct_variant_item", "original_full_pass", "uncontaminated"]
            if visual_status == "VISION_VERIFIED":
                evidence.append("visual_verified")
            grant = RewardLedger(self.state).grant(
                scope=section or original.get("section") or "chapter1",
                item_id=item_id,
                milestone="near_transfer",
                evidence=evidence,
                at=at,
            )
        else:
            variant["mastery_status"] = "CF" if independent else "U1"
            variant["progress_status"] = "ATTEMPTED_UNVERIFIED" if not visual_ok else "ATTEMPTED_CONTAMINATED"
            grant = None
        event = self._commit(
            "NEAR_VARIANT_ATTEMPT",
            {"item_id": item_id, "variant_item_id": variant_item_id, "result": result, "grant": grant},
            at=at,
        )
        return {"event": event, "item": copy.deepcopy(original), "variant_item": copy.deepcopy(variant), "grant": grant}

    def review_item(self, item_id: str, *, result: str, process_verified: bool, at: str | None = None) -> dict[str, Any]:
        item = self.ensure_item(item_id)
        if result not in {"correct", "incorrect", "partial", "guess"}:
            raise StateError(f"invalid review result: {result}")
        if not item.get("review_due"):
            raise StateError("review is not scheduled for this item")
        stamp = at or now_iso()
        if parse_time(stamp) < parse_time(item["review_due"]):
            raise StateError("review_due has not arrived")
        if result == "correct" and process_verified and item["mastery_status"] in {"U3", "U4", "U5"}:
            item["mastery_status"] = "U6"
            item["progress_status"] = "VERIFIED"
            item["review_due"] = None
            item["next_action"] = "混合复习或稳定性复测"
            evidence = ["due_review", "cold_recall", "process_verified", "contaminated_recall" if item["exposure"].get("contaminated") else "uncontaminated"]
            grant = RewardLedger(self.state).grant(scope=item.get("section") or "chapter1", item_id=item_id, milestone="delayed_recall", evidence=evidence, at=stamp)
        else:
            item["mastery_status"] = "CF"
            item["review_due"] = None
            item["next_action"] = "回听最小课程片段并做新题"
            grant = None
        item["review_history"].append({"at": stamp, "result": result, "process_verified": process_verified})
        event = self._commit("DELAYED_REVIEW", {"item_id": item_id, "result": result, "grant": grant}, at=stamp)
        return {"event": event, "item": copy.deepcopy(item), "grant": grant}

    def set_entry_pass(self, item_id: str, *, evidence: list[str], at: str | None = None) -> dict[str, Any]:
        item = self.ensure_item(item_id)
        if item["release"]["unlock_status"] == "LOCKED":
            item["release"]["unlock_status"] = "ENTRY_PASS"
        item["release"]["entry_pass"] = True
        item["evidence"] = sorted(set(item.get("evidence", []) + evidence))
        return self._commit("ENTRY_PASS", {"item_id": item_id, "evidence": evidence}, at=at)

    def merge_course_return(self, payload: dict[str, Any], *, at: str | None = None) -> dict[str, Any]:
        required = {"package_id", "base_state_id", "target_identity", "evidence"}
        missing = required - payload.keys()
        if missing:
            raise StateError(f"course return missing: {sorted(missing)}")
        package_id = payload["package_id"]
        if package_id in self.state["course_local"]["merged_package_ids"]:
            return {"status": "IDEMPOTENT_NOOP", "package_id": package_id}
        if target_key(payload["target_identity"]) != target_key(self.state["target_identity"]):
            return {"status": "REJECT_TARGET_MISMATCH", "package_id": package_id}
        if payload["base_state_id"] != self.state["main_state_id"]:
            return {"status": "REJECT_STALE_BASE", "package_id": package_id, "current_state_id": self.state["main_state_id"]}
        if payload.get("non_spoiler_signature") and payload.get("expected_non_spoiler_signature") and payload["non_spoiler_signature"] != payload["expected_non_spoiler_signature"]:
            return {"status": "REJECT_SIGNATURE", "package_id": package_id}
        self.state["course_local"]["merged_package_ids"].append(package_id)
        self.state["course_local"]["events"].append(copy.deepcopy(payload))
        self._commit("COURSE_RETURN_MERGED", {"package_id": package_id}, at=at)
        return {"status": "MERGED", "package_id": package_id}

    def pending_reviews(self, *, at: str | None = None) -> list[dict[str, Any]]:
        stamp = parse_time(at)
        return [copy.deepcopy(i) for i in self.state["items"].values() if i.get("review_due") and parse_time(i["review_due"]) <= stamp]

    def complete_section(
        self,
        section: str,
        item_ids: list[str],
        *,
        required_evidence: list[str],
        at: str | None = None,
    ) -> dict[str, Any]:
        """只有全部题目完成冷复测且无未闭环项，才发放一次小节奖励。"""
        if not item_ids:
            raise StateError("section completion requires item ids")
        if not required_evidence:
            raise StateError("section completion requires evidence")
        missing = [item_id for item_id in item_ids if item_id not in self.state["items"]]
        if missing:
            raise StateError(f"section items missing: {missing}")
        eligible = []
        blocked = []
        for item_id in item_ids:
            item = self.state["items"][item_id]
            if item.get("mastery_status") not in {"U6", "U7"}:
                blocked.append(f"{item_id}:mastery={item.get('mastery_status')}")
                continue
            if item.get("review_due") or item.get("next_action") == "回听最小课程片段并做新题":
                blocked.append(f"{item_id}:open_review")
                continue
            eligible.append(item_id)
        if blocked:
            raise StateError("section completion blocked: " + ", ".join(blocked))
        evidence = list(dict.fromkeys(required_evidence + ["all_items_u6_or_u7", "no_open_review"]))
        grant = RewardLedger(self.state).grant(scope=section, item_id=None, milestone="section_complete", evidence=evidence, at=at)
        event = self._commit("SECTION_COMPLETE", {"section": section, "item_ids": eligible, "grant": grant}, at=at)
        return {"event": event, "section": section, "item_ids": eligible, "grant": grant}

    def sync_summary(self) -> str:
        counts: dict[str, int] = {}
        for item in self.state["items"].values():
            value = item.get("mastery_status", "U0")
            counts[value] = counts.get(value, 0) + 1
        return "\n".join([
            "target_identity: " + json.dumps(self.state["target_identity"], ensure_ascii=False, sort_keys=True),
            f"main_state_id: {self.state['main_state_id']}    route_revision: {self.state['route_revision']}",
            f"active_batch: {self.state['active_batch']['batch_id']} + {self.state['active_batch']['knowledge_unit']} + {self.state['active_batch']['item_ids']}",
            "关键状态: " + json.dumps(counts, ensure_ascii=False, sort_keys=True),
            "contamination: " + json.dumps(self.state["contamination"], ensure_ascii=False),
            "open_loops: " + json.dumps(self.state["open_loops"], ensure_ascii=False),
            "唯一下一步: " + str(self.state["active_batch"].get("completion_gate") or "先核验目标身份并建立第一个知识点批次"),
        ])


def run_reward_test(path: str | Path) -> dict[str, Any]:
    """第一章奖励验收：覆盖、猜中、提示后不得给独立奖励；独立+近迁移+冷复测才按规则给分。"""
    target = {"module": "立体几何", "chapter": "第一章 空间向量与立体几何", "section": "1.1", "source_set": "2025-2025版选择性必修第1册"}
    store = StateStore.create(path, target)
    store.set_entry_pass("1.1-A1", evidence=["course_coverage"])
    watched = store.record_attempt("1.1-A1", independent=False, result="correct", section="1.1")
    guessed = store.record_attempt("1.1-A2", independent=True, result="guess", section="1.1")
    prompted = store.record_attempt("1.1-A3", independent=True, result="correct", hint_level="H1", process_verified=True, section="1.1", at="2026-08-10T09:00:00+00:00")
    clean = store.record_attempt("1.1-B4", independent=True, result="correct", process_verified=True, section="1.1", at="2026-08-10T09:00:00+00:00")
    near = store.record_near_variant("1.1-B4", variant_item_id="1.1-B4-near", independent=True, result="correct", process_verified=True, section="1.1", at="2026-08-10T09:30:00+00:00")
    review = store.review_item("1.1-A3", result="correct", process_verified=True, at="2026-08-11T09:00:00+00:00")
    grants = store.state["rewards"]["grants"]
    conditions = {
        "course_only_no_reward": watched["granted"] == [],
        "guess_no_reward": guessed["granted"] == [],
        "hinted_no_full_reward": prompted["granted"] == [],
        "clean_full_reward": len(clean["granted"]) == 1,
        "separate_near_reward": near["grant"] is not None,
        "delayed_review_reward": review["grant"] is not None,
        "points_expected": store.state["rewards"]["points"] == 50,
        "idempotent_grants": len({g["idempotency_key"] for g in grants}) == len(grants),
    }
    first_image_path = Path(path).with_name("first-image-reward-test-state.json")
    project_root = Path(__file__).resolve().parents[1]
    first_source_image = project_root / "data" / "ocr_live_current" / "first_chapter_69" / "imgs" / "img_in_image_box_523_429_694_610.jpg"
    # Bind the reward smoke test to the current answer-free packet rather than
    # to the old device-specific OCR path that produced the historical sidecar.
    # The packet keeps the original provenance for audit, while the executable
    # gate resolves the image through the repository's active OCR snapshot.
    first_image_sidecar_verified = False
    student_packet_path = project_root / "data" / "packets" / "1.1" / "student_packet.json"
    if student_packet_path.exists():
        try:
            student_packet = json.loads(student_packet_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            student_packet = {}
        first_question = next(
            (
                question
                for question in student_packet.get("questions", [])
                if question.get("group") == "A" and int(question.get("number", 0)) == 1
            ),
            None,
        )
        if first_question and first_question.get("visual_status") == "VISION_VERIFIED":
            image_refs = first_question.get("image_refs", [])
            image_bound = any(Path(str(ref.get("ref") or ref.get("path") or "")).name == first_source_image.name for ref in image_refs)
            sidecars = first_question.get("vision_sidecars", [])
            sidecar_bound = any(
                row.get("confidence") in {"E1", "E2"}
                for row in sidecars
                if isinstance(row, dict)
            )
            first_image_sidecar_verified = image_bound and sidecar_bound and bool(first_question.get("evidence"))
    first_image_store = StateStore.create(first_image_path, target)
    blocked_visual = first_image_store.record_attempt(
        "1.1-A1-blocked-visual",
        independent=True,
        result="correct",
        process_verified=True,
        visual_status="NEEDS_VISION_SIDECAR",
        source_anchor={"visual_evidence": "E0"},
        section="1.1",
        at="2026-08-10T10:00:00+00:00",
    )
    verified_visual = first_image_store.record_attempt(
        "1.1-A1",
        independent=True,
        result="correct",
        process_verified=True,
        visual_status="VISION_VERIFIED",
        source_anchor={"visual_evidence": "E2", "image": str(first_source_image), "question_hint": "1.1-A1"},
        section="1.1",
        at="2026-08-10T10:00:00+00:00",
    )
    first_image_grant = verified_visual["granted"][0] if verified_visual["granted"] else None
    first_image_conditions = {
        "missing_visual_no_reward": blocked_visual["granted"] == [],
        "verified_first_image_reward": first_image_grant is not None,
        "reward_records_visual_evidence": bool(first_image_grant and "visual_verified" in first_image_grant["evidence"]),
        "first_image_file_present": first_source_image.is_file(),
        "first_image_sidecar_verified": first_image_sidecar_verified,
    }
    conditions["first_image_visual_reward_gate"] = all(first_image_conditions.values())
    result = {
        "status": "passed" if all(conditions.values()) else "failed",
        "conditions": conditions,
        "first_image_conditions": first_image_conditions,
        "points": store.state["rewards"]["points"],
        "grants": grants,
        "first_image_grant": first_image_grant,
        "first_image_evidence": {"question_hint": "1.1-A1", "image": str(first_source_image), "exists": first_source_image.is_file(), "sidecar_verified": first_image_sidecar_verified, "visual_evidence": "E2"},
        "state_path": str(path),
        "first_image_state_path": str(first_image_path),
    }
    return result

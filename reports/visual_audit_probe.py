# -*- coding: utf-8 -*-
"""Read-only visual-chain audit probe for the 4 residual NEEDS_VISION_SIDECAR questions.

Run from project root:  python -X utf8 reports/visual_audit_probe.py
Writes nothing. Prints a compact per-question verdict.
"""
import hashlib, json
from pathlib import Path

ROOT = Path.cwd()
TARGETS = ["1.2+1.3-B13", "1.4-B4", "micro专题1-B1", "micro专题1-B4"]
PACKETS = {
    "1.2+1.3": "data/packets/1.2_1.3/student_packet.json",
    "1.4": "data/packets/1.4/student_packet.json",
    "micro专题1": "data/packets/micro专题1/student_packet.json",
}
PROBES = [
    "data/vision_live_probe.json",
    "data/vision_live_probe_2.json",
    "data/vision_probe_b4.json",
    "data/vision_probe_b5_retry.json",
    "data/vision_retry_b6.json",
    "data/vision_retry_botA.json",
    "data/vision_probe_remaining.json",
    "data/vision_probe_retry_all.json",
    "data/vision_retry_final.json",
    "data/vision_retry_final2.json",
]

def load(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__read_error__": repr(exc)}

def sha256_file(path):
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except Exception:
        return None

def short(item, keys):
    return {k: item.get(k) for k in keys if k in item}

full = load("data/vision_sidecar_full.json")
sample = load("data/vision_sidecar_sample.json")
live = load("data/vision_live_evidence.json")
print("== FILES ==")
for rel in ["data/vision_sidecar_full.json", "data/vision_sidecar_sample.json", "data/vision_live_evidence.json"]:
    p = ROOT / rel
    print(rel, "exists=", p.exists(), "mtime=", (p.stat().st_mtime if p.exists() else None))
print("sidecar_full.status=", (full or {}).get("status"), "results=", len((full or {}).get("results", [])))
print("live_evidence.status=", (live or {}).get("status"), "verified_count=", (live or {}).get("verified_count"))

print()
print("== PER-TARGET ==")
for t in TARGETS:
    print("###", t)
    sec = t.rsplit("-", 1)[0]
    pk = load(PACKETS.get(sec))
    q = None
    if pk:
        for item in pk.get("questions", []):
            if f"{item.get('section')}-{item.get('group')}{item.get('number')}" == t:
                q = item
                break
    if q is None:
        print("  PACKET: question NOT FOUND; packet questions=", [f"{x.get('group')}{x.get('number')}" for x in (pk or {}).get("questions", [])])
        q = {}
    else:
        print("  PACKET qid=", q.get("qid"), "visual_status=", q.get("visual_status"), "evidence=", q.get("evidence"))
        refs = q.get("image_refs", [])
        print("  image_refs=", json.dumps(refs, ensure_ascii=True))
        for ref in refs:
            p = Path(str(ref.get("path", "")))
            print("    ref_path_exists=", p.exists(), "size=", (p.stat().st_size if p.exists() else None), "sha16=", (sha256_file(p) or "")[:16], "declared_exists=", ref.get("exists"))
    all_results = []
    for name, data in [("full", full), ("sample", sample), ("live", live)]:
        for item in (data or {}).get("results", []):
            if item.get("question_hint") == t:
                all_results.append((name, item))
    if not all_results:
        print("  SIDECAR RESULTS: NONE for hint", t)
    for name, item in all_results:
        img = item.get("image", "")
        img_p = Path(img) if img else None
        img_ok = bool(img_p and img_p.is_file())
        actual = sha256_file(img) if img else None
        declared = item.get("image_sha256")
        hash_ok = bool(declared and actual and declared == actual)
        print("  sidecar[" + name + "] status=", item.get("status"), "confidence=", item.get("confidence"), "error=", item.get("error"), "elapsed_ms=", item.get("elapsed_ms"))
        print("    image=", img, "exists=", img_ok, "declared_sha_matches_actual=", hash_ok)
        if item.get("structured"):
            st = item["structured"]
            print("    structured: confidence=", st.get("confidence"), "objects=", len(st.get("objects") or []), "relations=", len(st.get("relations") or []), "text=", len(st.get("text") or []), "uncertainties=", st.get("uncertainties"))
        ref_paths = [str(r.get("path", "")) for r in q.get("image_refs", [])]
        match_path = any(Path(rp).resolve() == img_p.resolve() for rp in ref_paths) if img_p else False
        match_hash = False
        for rp in ref_paths:
            rp_p = Path(rp)
            if rp_p.is_file() and actual and sha256_file(rp_p) == actual:
                match_hash = True
        print("    match_vs_packet_refs: path=", match_path, "hash=", match_hash)
    print()

print("== PROBE HISTORY ==")
for rel in PROBES:
    data = load(rel)
    if data is None:
        print(rel, "MISSING")
        continue
    if isinstance(data, dict) and data.get("__read_error__"):
        print(rel, "READ_ERROR", data["__read_error__"])
        continue
    rows = data.get("results", [])
    print(rel, "status=", data.get("status"), "results=", len(rows))
    for item in rows:
        hint = item.get("question_hint")
        if hint in TARGETS:
            print("   TARGET", hint, json.dumps(short(item, ["status", "confidence", "error", "elapsed_ms", "image", "model"]), ensure_ascii=True))

print()
print("== CONFIG ==")
eyes_script = Path(r"C:\Users\poyi\.agents\skills\deepseek-eyes\scripts\describe.py")
eyes_cfg = Path(r"C:\Users\poyi\.agents\skills\deepseek-eyes\config.json")
print("describe.py exists=", eyes_script.exists())
if eyes_cfg.exists():
    try:
        cfg = json.loads(eyes_cfg.read_text(encoding="utf-8"))
        print("deepseek-eyes config.json keys=", sorted(cfg.keys()))
        print("has api_key=", bool(cfg.get("api_key")), "has profiles=", bool(cfg.get("profiles")), "model=", cfg.get("model"), "endpoint=", (cfg.get("endpoint") or "")[:60])
    except Exception as exc:
        print("config read error:", repr(exc))
else:
    print("deepseek-eyes config.json MISSING")

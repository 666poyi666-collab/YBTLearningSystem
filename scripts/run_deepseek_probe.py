from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ybt_learning.deepseek_context import verify_worker_probe


ROOT = Path(__file__).resolve().parents[1]
CONTEXT = ROOT / "data" / "contexts" / "1.1.json"
PROBE_DIR = ROOT / "data" / "deepseek_probe_workspace"
PROBE_CONTEXT = PROBE_DIR / "context.json"
PROBE_HELPER = PROBE_DIR / "probe_helper.py"
RAW_OUT = ROOT / "data" / "deepseek_probe_1.1.raw.jsonl"
REPORT_OUT = ROOT / "data" / "deepseek_probe_1.1.json"
MODEL = "opencode-go/deepseek-v4-flash"
VARIANT = "max"

PROMPT = """
You are consuming the only attached file (context.json) as a standalone text worker.
Do not open any other file, do not modify files,
do not solve any exercise, and do not output answers, explanations, or answer-book content.
Do not read project instructions, manifests, or protocol files. Do not ask which section to consume.
The attached context is already the complete section to consume.
Return exactly one JSON object, with no Markdown fence and no prose outside JSON. Do not use tools
after reading context.json; perform the required hashes from the values already in the attachment.
Required fields:
runtime: {model, reasoning_effort, context_window}
context_sha256: copy evidence.context_sha256 exactly
canary: copy evidence.canary exactly
qid_probes: for every qid in evidence.probe_qids, compute the lowercase first 8 characters of the
SHA-256 hex digest of the UTF-8 string canary + qid
question_echo: for every question in questions, keyed by qid, return
  {question_text_sha256: lowercase full SHA-256 of the UTF-8 question_text, visual_status: exact value}
understanding_summary: describe only the data structure, listening order, knowledge-point ->
example -> type-training -> A/B/C order, and current release/mastery distinction; do not include
any answer or solution.
You may run the read-only helper `probe_helper.py` in the isolated working directory to calculate
the exact full SHA-256 values required above. If the attachment cannot be read, return only {error: ...}.
""".strip()


def _opencode_command() -> str:
    found = shutil.which("opencode.cmd") or shutil.which("opencode")
    if found:
        return found
    return "opencode"


def _extract_final_json(events: list[dict], raw_stdout: str = "") -> tuple[dict | None, str | None]:
    texts = [str(event.get("part", {}).get("text", "")) for event in events if event.get("type") == "text"]
    if not texts:
        # Older opencode JSON mode can emit the final answer as plain text
        # after a stream of non-JSON terminal lines.  Parse the last fenced or
        # object-looking block from stdout, but keep the raw session unchanged.
        candidates = re.findall(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_stdout, flags=re.I)
        candidates.extend(re.findall(r"(?ms)^\s*(\{\s*\"runtime\"[\s\S]*?\n\})\s*$", raw_stdout))
        if not candidates:
            return None, "no_final_text_event"
        final_text = candidates[-1].strip()
    else:
        final_text = texts[-1].strip()
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", final_text, flags=re.I)
    candidate = fenced.group(1).strip() if fenced else final_text
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        value = None
        for index, char in enumerate(candidate):
            if char != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                value = parsed
                break
        if value is None:
            return None, "final_text_not_json"
    if not isinstance(value, dict):
        return None, "final_json_not_object"
    return value, None


def _extract_markdown_probe(raw_stdout: str) -> dict | None:
    """Recover the model's concise non-JSON probe when CLI emits plain text."""
    canary = re.search(r"Canary[^`]*`([0-9a-f]{16})`", raw_stdout, flags=re.I)
    if not canary:
        return None
    probes = dict(re.findall(r"`(Q-[0-9a-f]+)`\s*(?:→|->)\s*`?([0-9a-f]{8})`?", raw_stdout, flags=re.I))
    status = re.search(r"Status:\s*`([^`]+)`", raw_stdout, flags=re.I)
    section = re.search(r"section\s+([^,]+),\s*(\d+)\s*/\s*(\d+)\s*questions", raw_stdout, flags=re.I)
    qids = re.findall(r"\*\*(Q-[0-9a-f]+)\*\*", raw_stdout, flags=re.I)
    echoes: dict[str, dict[str, str]] = {}
    for qid in qids:
        block_match = re.search(rf"\*\*{re.escape(qid)}\*\*[\s\S]*?(?=\n\s*\*\*Q-|\Z)", raw_stdout)
        block = block_match.group(0) if block_match else ""
        visual = re.search(r"visual_status:\s*`([^`]+)`", block)
        text = re.search(r"- text:\s*(.+)", block)
        if visual and text:
            # The markdown output is not accepted as a substitute for a hash;
            # this branch only gives a deterministic fail reason for audits.
            echoes[qid] = {"question_text_sha256": "", "visual_status": visual.group(1)}
    return {
        "runtime": {"model": MODEL, "reasoning_effort": VARIANT, "context_window": 1000000},
        "context_sha256": "",
        "canary": canary.group(1),
        "qid_probes": probes,
        "question_echo": echoes,
        "understanding_summary": {"status": status.group(1) if status else None, "section": section.group(1).strip() if section else None, "question_count": int(section.group(3)) if section else None},
    }


def main() -> int:
    if not CONTEXT.is_file():
        raise SystemExit(f"missing context: {CONTEXT}")
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    PROBE_CONTEXT.write_text(CONTEXT.read_text(encoding="utf-8"), encoding="utf-8")
    PROBE_HELPER.write_text(
        "import hashlib, json\n"
        "from pathlib import Path\n"
        "c=json.loads(Path('context.json').read_text(encoding='utf-8'))\n"
        "canary=c['evidence']['canary']\n"
        "print(json.dumps({'context_sha256': c['evidence']['context_sha256'], 'canary': canary, 'qid_probes': {q: hashlib.sha256((canary+q).encode('utf-8')).hexdigest()[:8] for q in c['evidence']['probe_qids']}, 'question_echo': {q['qid']: {'question_text_sha256': hashlib.sha256(q['question_text'].encode('utf-8')).hexdigest(), 'visual_status': q['visual_status']} for q in c['questions']}}, ensure_ascii=False))\n",
        encoding="utf-8",
    )
    command = [
        _opencode_command(),
        "run",
        PROMPT,
        "--dir",
        str(PROBE_DIR),
        "--model",
        MODEL,
        "--variant",
        VARIANT,
        "--format",
        "json",
        "--file",
        str(PROBE_CONTEXT),
    ]
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600, check=False)
    RAW_OUT.write_text(proc.stdout, encoding="utf-8")
    events: list[dict] = []
    for line in proc.stdout.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    response, parse_error = _extract_final_json(events, proc.stdout)
    if response is None:
        response = _extract_markdown_probe(proc.stdout)
        if response is not None:
            parse_error = "plain_text_probe_recovered_but_not_release_grade_json"
    report = {
        "schema_version": "7.1",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "status": "failed",
        "standalone_route": {
            "requested_model": MODEL,
            "requested_variant": VARIANT,
            "requested_context_window": 1000000,
            "agent_role": "direct_model_route",
            "command_excludes_answer_sidecar": True,
        },
        "process": {
            "returncode": proc.returncode,
            "event_count": len(events),
            "session_id": next((item.get("sessionID") for item in events if item.get("sessionID")), None),
            "stderr_tail": proc.stderr[-2000:],
            "raw_path": str(RAW_OUT),
        },
        "response": response,
        "parse_error": parse_error,
    }
    if response is not None and proc.returncode == 0:
        # verify_worker_probe expects a response JSON file; keep the raw model
        # response in the report while using a short-lived canonical file for
        # the strict verifier.
        response_path = ROOT / "data" / ".deepseek_probe_response.tmp.json"
        response_path.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try:
            verification = verify_worker_probe(CONTEXT, response_path)
        finally:
            response_path.unlink(missing_ok=True)
        report["verification"] = verification
        report["status"] = verification["status"]
    else:
        report["verification"] = {"status": "failed", "errors": [parse_error or "opencode_failed"]}
    REPORT_OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # The isolated directory is disposable evidence staging, not an input
    # artifact.  Keep the canonical raw session/report only.
    for child in (PROBE_CONTEXT, PROBE_HELPER):
        child.unlink(missing_ok=True)
    try:
        PROBE_DIR.rmdir()
    except OSError:
        pass
    print(json.dumps({"path": str(REPORT_OUT), "status": report["status"], "session_id": report["process"]["session_id"], "errors": report["verification"].get("errors", [])}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

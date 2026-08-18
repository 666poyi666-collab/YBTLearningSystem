from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ybt_learning.deepseek_context import validate_context, verify_worker_understanding


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "deepseek_http_probe_1.1.json"
CONTEXT = ROOT / "data" / "contexts" / "1.1.json"


def main() -> int:
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    response = report.get("response")
    if not isinstance(response, dict):
        raise SystemExit("saved report has no model response")
    tmp = ROOT / "data" / ".deepseek_http_saved_response.tmp.json"
    tmp.write_text(json.dumps(response, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    try:
        verification = verify_worker_understanding(CONTEXT, tmp, transport={
            "requested_model": report.get("requested_model"),
            "returned_model": report.get("transport", {}).get("returned_model"),
            "status": report.get("transport", {}).get("status"),
        })
    finally:
        tmp.unlink(missing_ok=True)
    report["context"] = validate_context(CONTEXT)
    report["verification"] = verification
    report["status"] = verification["status"]
    report["verification_reused_saved_response"] = True
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"path": str(REPORT), "status": report["status"], "errors": verification["errors"]}, ensure_ascii=False))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())

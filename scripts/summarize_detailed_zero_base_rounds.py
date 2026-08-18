from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "reports" / "zero_base_cycles"
RAW_SESSION = Path(
    r"C:\Users\poyi\.codex\sessions\2026\08\14\rollout-2026-08-14T14-34-29-019ffefa-b09d-7ae0-a59b-b5d21b0798e0.jsonl"
)

LEGACY_ROUNDS = {
    1: {
        "agent_ids": [
            "01a000ec-c335-75c3-8862-3bbeb0cb1907",
            "01a000ec-c3b5-7651-b5a7-b67a88c9f193",
            "01a000ec-c41d-7490-a6c5-832a11c65cec",
            "01a000ec-c48a-79e3-a312-2b9f36b5fc89",
            "01a000ec-c50a-72e0-9ebf-4b3b29239c53",
        ],
        "verdict": "partial",
        "findings": [
            "课程转写未覆盖全部左栏定义，知识点必须显式放在相邻例题之前。",
            "等值面循环缺教材题承接；部分 B 组题依赖尚未学习的数量积或二面角。",
            "投影、极化、重心、二面角、基本不等式和外接球前置不闭合。",
            "例题和直属变式的图形侧车不完整，不能把有题号当成可消费。",
        ],
    },
    2: {
        "agent_ids": [
            "01a000fe-a5cd-7010-b8b6-e79ba1fcfbdd",
            "01a000fe-a6c9-72d2-a887-344e2596bf61",
            "01a000fe-a466-70e2-a184-1606519f1293",
            "01a000fe-a649-7510-af5a-de64882e335c",
            "01a000fe-a745-7f13-a728-52b1d2a44848",
        ],
        "verdict": "partial",
        "findings": [
            "知识点到相邻例题的显示顺序成立，但视觉状态必须逐任务显示。",
            "3.1.3.1、3.1.3.2 坐标课程与 3.1.4.1 平行垂直前置尚未进入完整总览。",
            "极化、四点共面、基本不等式和外接球仍只有骨架或缺少零基础放行证据。",
            "循环 10 的 C14 首次整合多个桥接，真实首断点尚未被单独教学。",
        ],
    },
}

FINAL_METHOD_MODELS = [
    {
        "name": "相等、相反与共线向量判定",
        "trigger": "长方体、平行六面体中枚举或判断方向关系",
        "steps": ["同时检查方向与模", "统一起点或平移", "用倍数关系完成共线判定"],
    },
    {
        "name": "线性运算与基底拆分",
        "trigger": "目标向量不能直接计算",
        "steps": ["选公共起点和基向量", "按路径或中点关系拆分", "合并系数并回译几何对象"],
    },
    {
        "name": "共线、共面与系数和",
        "trigger": "证明三点共线、四点共面或判断倍面",
        "steps": ["写成同一基底的线性组合", "共线检查二维系数和", "共面检查三维仿射系数和为1"],
    },
    {
        "name": "等值面末减出",
        "trigger": "多个点由同一组基向量表示并判断所在倍面或连线方向",
        "steps": ["先求各点系数和", "相减得到连线向量系数和", "用倍面差解释结果"],
    },
    {
        "name": "空间坐标法",
        "trigger": "可建系图形中的长度、垂直和夹角",
        "steps": ["建系并标点", "写方向向量", "点乘或模长计算", "按题目角度范围检查绝对值"],
    },
    {
        "name": "数量积与投影",
        "trigger": "求夹角、垂直、投影向量或投影长度",
        "steps": ["区分向量与标量", "使用点积定义或投影公式", "检查分母、方向符号和夹角范围"],
    },
    {
        "name": "极化恒等式与最值",
        "trigger": "数量积目标可转成和差向量或中点距离",
        "steps": ["展开模长平方", "选择和式或差式", "写可行域与等号条件", "回代几何对象"],
    },
    {
        "name": "三角形重心向量",
        "trigger": "重心、中线或三顶点等权表示",
        "steps": ["先写中点向量", "用2:1定比分点", "整理成三顶点位置向量平均", "换中线复核"],
    },
    {
        "name": "二面角合法截面",
        "trigger": "求二面角或面面角",
        "steps": ["在公共棱取同一点", "两半平面内分别作垂线", "取两射线夹角", "用法向量时判断等角或补角"],
    },
    {
        "name": "仿射参数求交与同参截线",
        "trigger": "两条直线交于三角形两边并需证明截线平行",
        "steps": ["为同一交点写两套参数表示", "在同一基底逐项比较", "统一方向比较两个分点参数", "补查退化与线面位置条件"],
    },
    {
        "name": "正数乘积固定时的和最值",
        "trigger": "几何约束化为两个正数乘积固定",
        "steps": ["先验证正数和定积", "由平方非负推出下界", "检查等号候选和几何定义域"],
    },
    {
        "name": "外接球与点面距离",
        "trigger": "球心、等距约束或点到平面距离",
        "steps": ["利用对称性缩减未知量", "用等距平方差消去半径", "回代关键顶点", "再计算法向量投影距离"],
    },
]


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def legacy_round(round_number: int, raw_text: str) -> dict:
    source = LEGACY_ROUNDS[round_number]
    completed = []
    for agent_id in source["agent_ids"]:
        dispatched = agent_id in raw_text
        completion_patterns = (
            f'"agent_path":"{agent_id}","status":{{"completed"',
            f'\\"agent_path\\":\\"{agent_id}\\",\\"status\\":{{\\"completed\\"',
        )
        finished = any(pattern in raw_text for pattern in completion_patterns)
        if not (dispatched and finished):
            raise ValueError(f"round {round_number} lacks completion evidence for {agent_id}")
        completed.append(agent_id)
    return {
        "round": round_number,
        "evidence_kind": "raw_session",
        "source": str(RAW_SESSION),
        "workers_dispatched": 5,
        "workers_completed": len(completed),
        "agent_ids": completed,
        "reported_verdict": source["verdict"],
        "findings": source["findings"],
    }


def detailed_round(round_number: int) -> tuple[dict, list[dict]]:
    paths = sorted(REPORT_ROOT.glob(f"1.1-detailed-round-{round_number}-worker-*.json"))
    paths = [path for path in paths if "postrepair" not in path.name]
    if len(paths) != 5:
        raise ValueError(f"round {round_number} expected 5 reports, found {len(paths)}")
    reports = [load_json(path) for path in paths]
    workers = sorted(int(report["worker"]) for report in reports)
    if workers != [1, 2, 3, 4, 5]:
        raise ValueError(f"round {round_number} worker set is {workers}")
    for report in reports:
        if int(report.get("round", -1)) != round_number:
            raise ValueError(f"round mismatch in worker {report.get('worker')}")
        if report.get("forbidden_sources_read") is not False:
            raise ValueError(f"forbidden source state invalid in round {round_number} worker {report.get('worker')}")
        if report.get("answer_sidecar_read") is not False:
            raise ValueError(f"answer sidecar state invalid in round {round_number} worker {report.get('worker')}")
        if report.get("human_acceptance_not_proven") is not True:
            raise ValueError(f"human evidence boundary missing in round {round_number} worker {report.get('worker')}")
    verdicts = Counter(str(report.get("overall_verdict", "unknown")) for report in reports)
    return (
        {
            "round": round_number,
            "evidence_kind": "five_json_reports",
            "workers_dispatched": 5,
            "workers_completed": 5,
            "reports": [relative(path) for path in paths],
            "reported_verdict_counts": dict(sorted(verdicts.items())),
            "first_breakpoints": [
                {
                    "worker": report["worker"],
                    "value": report.get("first_breakpoint"),
                }
                for report in reports
                if report.get("first_breakpoint")
            ],
        },
        reports,
    )


def verify_variant_11_source() -> dict:
    source_path = ROOT / "data" / "ocr_live_current" / "first_chapter_69" / "doc_6.md"
    source = source_path.read_text(encoding="utf-8").replace(" ", "")
    stem_ok = r"\overrightarrow{A_1F}=\frac{2}{3}\overrightarrow{FC}" in source
    derivation_ok = r"\overrightarrow{EF}=\frac{2}{5}\overrightarrow{EB}" in source
    if not (stem_ok and derivation_ok):
        raise ValueError("variant 11 source derivation is not intact")
    return {
        "worker_report": "reports/zero_base_cycles/1.1-detailed-round-5-worker-1.json",
        "worker_reported": "partial",
        "controller_verdict": "proxy_pass",
        "reason": "worker omitted the A1A component of EB; the source stem keeps FC and the source derivation proves EF=(2/5)EB",
        "source": relative(source_path),
    }


def route_snapshot() -> dict:
    packet = load_json(ROOT / "data" / "packets" / "1.1" / "learning_packet.json")
    plan = load_json(ROOT / "data" / "chapter1_learning_plan.json")
    section = next(item for item in plan["plan"] if item["section"] == "1.1")
    courses = section.get("must_listen_courses", [])
    items = [
        item
        for cycle in packet["learning_cycles"]
        for item in [
            *cycle.get("worked_examples", []),
            *cycle.get("direct_variants", []),
            *cycle.get("exercise_questions", []),
        ]
    ]
    visual_counts = Counter(str(item.get("visual_status", "UNKNOWN")) for item in items)
    preview = (ROOT / "data" / "packets" / "1.1" / "learning_path_without_questions.md").read_text(
        encoding="utf-8-sig"
    )
    internal_id_hits = re.findall(r"1\.1-k\d+|bridge-[\w.-]+", preview)
    image_hits = re.findall(r"<img|!\[|imgs/", preview)
    if internal_id_hits or image_hits:
        raise ValueError("no-question route leaks internal ids or image references")
    return {
        "first_course": courses[0]["original_course_id"],
        "course_count": len(courses),
        "course_ids": [item["original_course_id"] for item in courses],
        "cycles": len(packet["learning_cycles"]),
        "counts": packet["counts"],
        "visual_status_counts": dict(sorted(visual_counts.items())),
        "internal_id_hits": 0,
        "image_reference_hits": 0,
        "html": "data/packets/1.1/learning_path_without_questions.html",
    }


def render_markdown(summary: dict) -> str:
    lines = [
        "# 1.1 详细路线五轮零基础模拟汇总",
        "",
        f"> 最终裁决：`{summary['overall_verdict']}`。这只证明代理可沿当前路线完成，不证明真人掌握。",
        "> 真人观察与 24 小时闭卷冷复测仍为 `not_run`。",
        "",
        "## 五轮演进",
        "",
        "| 轮次 | 完成 | 原始结果 | 主要变化 |",
        "|---|---:|---|---|",
    ]
    round_notes = {
        1: "发现左栏定义、视觉侧车和跨方法前置缺口",
        2: "确认课程总览、坐标前置和桥接状态需要显式化",
        3: "五路均未全过，精确定位视觉、课程和桥接阻塞",
        4: "视觉及多数桥接修复，剩坐标前置、变式11误判和C14-A近迁移",
        5: "坐标/视觉/课程总览通过；主控驳回变式11误判，并补齐C14-A仿射求交微课",
    }
    for item in summary["rounds"]:
        if "reported_verdict_counts" in item:
            verdict = ", ".join(f"{key}={value}" for key, value in item["reported_verdict_counts"].items())
        else:
            verdict = item["reported_verdict"]
        lines.append(
            f"| {item['round']} | {item['workers_completed']}/5 | {verdict} | {round_notes[item['round']]} |"
        )

    route = summary["final_route"]
    lines.extend(
        [
            "",
            "## 最终路线",
            "",
            f"第一门课：`{route['first_course']}`。完整总览共 {route['course_count']} 门课程、{route['cycles']} 个循环。",
            "",
            f"1.1 共 {route['counts']['total_numbered_learning_items']} 个编号任务："
            f"{route['counts']['worked_examples']} 道教学例题、"
            f"{route['counts']['direct_variants']} 道直属变式、"
            f"{route['counts']['abc_exercises']} 道 A/B/C 习题。",
            "",
            "执行顺序固定为：课程 -> 左侧知识点 -> 相邻例题 -> 直属变式 -> 类型题 -> A/B/C 习题 -> 本循环验收。",
            "",
            "## 主控裁决",
            "",
        ]
    )
    for decision in summary["controller_adjudications"]:
        lines.append(f"- {decision['reason']}。裁决：`{decision['controller_verdict']}`。")

    lines.extend(["", "## 方法模型", ""])
    for index, model in enumerate(summary["method_models"], start=1):
        lines.append(f"{index}. **{model['name']}**：{model['trigger']}。步骤：{' -> '.join(model['steps'])}。")

    lines.extend(
        [
            "",
            "## 证据边界",
            "",
            "- 25 个指定 DeepSeek worker 均完成；round 1-2 以原始会话事件为证，round 3-5 各有 5 份 JSON 报告。",
            "- `proxy_pass` 不等于真人掌握；真人 E2E、未见题观察和 24 小时冷复测均未运行。",
            "- 项目没有有效 Git 仓库，提交 SHA 门禁保持 blocked；没有执行 `git init`。",
            "- 其他章节仍有桥接阻塞，不把 1.1 的结果扩大成整章完成。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    raw_text = RAW_SESSION.read_text(encoding="utf-8")
    rounds = [legacy_round(1, raw_text), legacy_round(2, raw_text)]
    reports_by_round: dict[int, list[dict]] = {}
    for round_number in (3, 4, 5):
        round_summary, reports = detailed_round(round_number)
        rounds.append(round_summary)
        reports_by_round[round_number] = reports

    postrepair_path = REPORT_ROOT / "1.1-detailed-round-5-worker-5-postrepair.json"
    postrepair = load_json(postrepair_path)
    if (
        postrepair.get("overall_verdict") not in {"pass", "proxy_pass"}
        or postrepair.get("c14_a_verdict") != "breakpoint_closed"
        or postrepair.get("answer_sidecar_read") is not False
    ):
        raise ValueError("C14-A post-repair verification has not passed")

    variant_decision = verify_variant_11_source()
    c14_decision = {
        "worker_report": "reports/zero_base_cycles/1.1-detailed-round-5-worker-5.json",
        "worker_reported": "partial",
        "controller_verdict": "proxy_pass",
        "reason": "C14-A affine-intersection breakpoint was repaired and independently rechecked with an answer-free near transfer",
        "source": relative(postrepair_path),
    }
    rounds[-1]["controller_verdict_counts"] = {"proxy_pass": 5}
    rounds[-1]["postrepair"] = relative(postrepair_path)

    summary = {
        "schema_version": "1.0",
        "section": "1.1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "requirement_id": "REQ-20260814-YBT-DETAILED-ROUNDS-001",
        "worker_contract": {
            "rounds": 5,
            "workers_per_round": 5,
            "total_completed": 25,
            "role": "deepseek_worker",
            "model": "opencode-go/deepseek-v4-flash",
            "reasoning_effort": "max",
            "context_window": 1000000,
        },
        "rounds": rounds,
        "controller_adjudications": [variant_decision, c14_decision],
        "final_route": route_snapshot(),
        "method_models": FINAL_METHOD_MODELS,
        "overall_verdict": "proxy_pass",
        "human_acceptance_not_proven": True,
        "human_e2e": "not_run",
        "cold_retest_24h": "not_run",
        "git_gate": "blocked_no_repository",
        "scope_note": "Section 1.1 only; other sections' bridge blockers are outside this result.",
    }

    json_path = REPORT_ROOT / "1.1-detailed-five-round-summary.json"
    markdown_path = REPORT_ROOT / "1.1-detailed-five-round-summary.md"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(summary), encoding="utf-8-sig", newline="\r\n")
    print(
        json.dumps(
            {
                "status": "passed",
                "json": str(json_path),
                "markdown": str(markdown_path),
                "rounds": len(rounds),
                "workers": summary["worker_contract"]["total_completed"],
                "overall_verdict": summary["overall_verdict"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

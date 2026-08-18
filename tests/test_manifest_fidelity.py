from __future__ import annotations

import json
import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_markdown_exporter():
    path = ROOT / "scripts" / "export_learning_packet_markdown.py"
    spec = importlib.util.spec_from_file_location("ybt_markdown_exporter_test", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ManifestFidelityTests(unittest.TestCase):
    def test_learning_cycles_cover_every_item_exactly_once(self) -> None:
        for path in (ROOT / "data" / "packets").glob("*/learning_packet.json"):
            packet = json.loads(path.read_text(encoding="utf-8"))
            cycles = packet.get("learning_cycles", [])
            self.assertTrue(cycles, path)
            knowledge_blocks = {item["id"]: item for item in packet.get("knowledge_blocks", [])}

            cycle_examples = [
                item["example_number"]
                for cycle in cycles
                for item in cycle.get("worked_examples", [])
            ]
            cycle_variants = [
                item["item_id"]
                for cycle in cycles
                for item in cycle.get("direct_variants", [])
            ]
            cycle_exercises = [
                f"{item['group']}{item['number']}"
                for cycle in cycles
                for item in cycle.get("exercise_questions", [])
            ]
            expected_examples = [item["example_number"] for item in packet["worked_examples"]]
            expected_variants = [item["item_id"] for item in packet["direct_variants"]]
            expected_exercises = [f"{item['group']}{item['number']}" for item in packet["exercise_questions"]]

            self.assertCountEqual(cycle_examples, expected_examples, path)
            self.assertCountEqual(cycle_variants, expected_variants, path)
            self.assertCountEqual(cycle_exercises, expected_exercises, path)
            self.assertEqual(len(cycle_examples), len(set(cycle_examples)), path)
            self.assertEqual(len(cycle_variants), len(set(cycle_variants)), path)
            self.assertEqual(len(cycle_exercises), len(set(cycle_exercises)), path)

            for cycle in cycles:
                self.assertEqual(
                    [item["id"] for item in cycle.get("knowledge_blocks", [])],
                    cycle.get("knowledge_refs", []),
                    path,
                )
                for ref in cycle.get("knowledge_refs", []):
                    self.assertTrue(knowledge_blocks[ref]["text"].strip(), (path, ref))
                parents = {item["example_number"] for item in cycle.get("worked_examples", [])}
                for variant in cycle.get("direct_variants", []):
                    self.assertIn(variant["parent_example_number"], parents, path)

    def test_learning_cycle_course_and_bridge_references_resolve(self) -> None:
        manifest = json.loads((ROOT / "chapter1_manifest.json").read_text(encoding="utf-8"))
        plan = json.loads((ROOT / "data" / "chapter1_learning_plan.json").read_text(encoding="utf-8"))
        bridges = json.loads((ROOT / "data" / "bridge_micro_lessons.json").read_text(encoding="utf-8"))
        plan_by_section = {item["section"]: item for item in plan["plan"]}
        bridge_ids = {item["id"] for item in bridges["units"]}

        for section in manifest["sections"]:
            plan_section = plan_by_section[section["id"]]
            knowledge_ids = {item["id"] for item in section.get("knowledge_points", [])}
            courses = plan_section.get("must_listen_courses") or [
                *plan_section.get("required_courses", []),
                *plan_section.get("support_courses", []),
            ]
            course_keys = {item["course_key"] for item in courses}
            for cycle in section.get("learning_cycles", []):
                referenced_courses = set(cycle.get("course_keys", [])) | set(cycle.get("prerequisite_course_keys", []))
                self.assertFalse(referenced_courses - course_keys, (section["id"], cycle["id"]))
                self.assertFalse(set(cycle.get("bridge_unit_ids", [])) - bridge_ids, (section["id"], cycle["id"]))
                referenced_knowledge = set(cycle.get("knowledge_refs", [])) | set(cycle.get("prerequisite_knowledge_refs", []))
                self.assertFalse(referenced_knowledge - knowledge_ids, (section["id"], cycle["id"]))
                for checkpoint in cycle.get("method_checkpoints", []):
                    self.assertTrue(checkpoint.get("id"), (section["id"], cycle["id"]))
                    self.assertTrue(str(checkpoint.get("question_text", "")).strip(), checkpoint.get("id"))
                    self.assertNotRegex(checkpoint["question_text"], r"答案\s*[：:]|解析\s*[：:]|解答\s*[：:]")

        section_11 = next(item for item in manifest["sections"] if item["id"] == "1.1")
        cycle_by_id = {item["id"]: item for item in section_11["learning_cycles"]}
        self.assertEqual(cycle_by_id["1.1-cycle-8"]["course_keys"], ["plane_plane_angle"])
        self.assertIn("parallel_perpendicular", cycle_by_id["1.1-cycle-8"]["prerequisite_course_keys"])
        self.assertEqual(cycle_by_id["1.1-cycle-8"]["exercise_keys"], ["B6", "B7"])
        self.assertEqual(cycle_by_id["1.1-cycle-10"]["exercise_keys"], ["C14"])
        self.assertIn("parallel_perpendicular", cycle_by_id["1.1-cycle-10"]["prerequisite_course_keys"])
        self.assertIn("bridge-1.1-affine-intersection-ratio", cycle_by_id["1.1-cycle-10"]["bridge_unit_ids"])
        self.assertIn("bridge-1.1-positive-product-sum", cycle_by_id["1.1-cycle-10"]["bridge_unit_ids"])
        self.assertIn(
            "1.1-affine-intersection-check-1",
            [item["id"] for item in cycle_by_id["1.1-cycle-10"]["method_checkpoints"]],
        )
        bridge_by_id = {item["id"]: item for item in bridges["units"]}
        self.assertEqual(bridge_by_id["bridge-1.1-affine-intersection-ratio"].get("zero_base_status"), None)
        self.assertEqual(bridge_by_id["bridge-1.1-positive-product-sum"]["zero_base_status"], "NOT_CLOSED")
        self.assertEqual(
            cycle_by_id["1.1-cycle-10"]["course_keys"],
            ["plane_equation_upper", "plane_equation_lower", "distance"],
        )

        packet_11 = json.loads((ROOT / "data" / "packets" / "1.1" / "learning_packet.json").read_text(encoding="utf-8"))
        k4 = next(item for item in packet_11["knowledge_blocks"] if item["id"] == "1.1-k4")["text"]
        self.assertIn("空间向量数量积的性质", k4)
        self.assertIn("投影向量", k4)

    def test_markdown_export_is_cycle_ordered_answer_safe_and_deterministic(self) -> None:
        exporter = _load_markdown_exporter()
        plan = exporter.load_json(ROOT / "data" / "chapter1_learning_plan.json")
        bridges = exporter.load_json(ROOT / "data" / "bridge_micro_lessons.json")
        answer_leak = re.compile(r"答案\s*[：:]|解法\s*[一二两12]?\s*[：:]|解析\s*[：:]|解答\s*[：:]|最终答案|故答案")

        plan_sections = {str(item["section"]) for item in plan["plan"]}
        packet_paths = [
            path
            for path in (ROOT / "data" / "packets").glob("*/learning_packet.json")
            if str(exporter.load_json(path).get("section")) in plan_sections
        ]
        self.assertEqual(
            {str(exporter.load_json(path).get("section")) for path in packet_paths},
            plan_sections,
        )
        for path in packet_paths:
            packet = exporter.load_json(path)
            rendered = exporter.export_markdown(packet, plan, bridges)
            self.assertEqual(rendered, exporter.export_markdown(packet, plan, bridges), path)
            markdown_path = path.with_suffix(".md")
            self.assertEqual(rendered, markdown_path.read_text(encoding="utf-8-sig"), path)
            self.assertTrue(markdown_path.read_bytes().startswith(b"\xef\xbb\xbf"), path)

            task_numbers = [int(value) for value in re.findall(r"^#{4,5} 任务 (\d+)｜", rendered, flags=re.MULTILINE)]
            expected_total = packet["counts"]["total_numbered_learning_items"]
            self.assertEqual(task_numbers, list(range(1, expected_total + 1)), path)
            self.assertIsNone(re.search(r"^#{1,3}\s+\d+[.．、]", rendered, flags=re.MULTILINE), path)
            for block in packet.get("knowledge_blocks", []):
                marker = f"左侧知识点｜`{block['id']}`"
                self.assertEqual(rendered.count(marker), 1, (path, block["id"]))

            cursor = 0
            for cycle in packet["learning_cycles"]:
                headings = [
                    f"## 循环 {cycle['sequence']}/{len(packet['learning_cycles'])}",
                    "### 当前动作 1：看本批视频",
                    "### 当前动作 2：按本批做题路径推进",
                    "### 当前动作 3：做本批对应 A/B/C 习题（无答案）",
                    "### 当前动作 4：本批验收",
                ]
                positions = []
                for heading in headings:
                    position = rendered.find(heading, cursor)
                    self.assertGreaterEqual(position, 0, (path, heading))
                    positions.append(position)
                    cursor = position + len(heading)
                self.assertEqual(positions, sorted(positions), path)
                exercise_work = rendered[positions[3] + len(headings[3]):positions[4]]
                self.assertIsNone(answer_leak.search(exercise_work), path)
                self.assertIn("未满足推进门时停在本循环", rendered[positions[4]:], path)

                cycle_text = rendered[positions[0]:positions[4]]
                examples = {item["example_number"]: item for item in cycle.get("worked_examples", [])}
                for variant in cycle.get("direct_variants", []):
                    parent = variant["parent_example_number"]
                    parent_label = examples[parent]["label"]
                    variant_heading = f"（对应例{variant['parent_example_number']}，无解答）"
                    self.assertGreater(cycle_text.find(variant_heading), cycle_text.find(f"｜{parent_label}"), path)

    def test_without_questions_export_keeps_route_and_omits_question_content(self) -> None:
        exporter = _load_markdown_exporter()
        packet = exporter.load_json(ROOT / "data" / "packets" / "1.1" / "learning_packet.json")
        plan = exporter.load_json(ROOT / "data" / "chapter1_learning_plan.json")
        bridges = exporter.load_json(ROOT / "data" / "bridge_micro_lessons.json")
        coverage = exporter.load_json(ROOT / "data" / "question_coverage.json")
        rendered = exporter.export_without_questions(packet, plan, bridges, coverage)

        self.assertEqual(rendered.count("## 循环 "), 10)
        self.assertIn("## 一眼总览", rendered)
        self.assertIn("## 每道题怎么写", rendered)
        self.assertIn("课后按顺序写这些", rendered)
        self.assertIn("A1、A2、A3", rendered)
        self.assertIn("任务 01—任务 08", rendered)
        self.assertLess(rendered.index("## 一眼总览"), rendered.index("## 先听哪一节课"))
        self.assertLess(rendered.index("## 每道题怎么写"), rendered.index("## 先听哪一节课"))
        self.assertLess(rendered.index("## 使用顺序"), rendered.index("## 循环 1/10"))
        self.assertIn("3.1.1.1 空间向量的运算", rendered)
        self.assertIn("第一节先听：`3.1.1.1` 空间向量的运算", rendered)
        self.assertIn("`3.1.3.1` 空间直角坐标系", rendered)
        self.assertIn("`3.1.3.2` 空间向量运算的坐标表示", rendered)
        self.assertIn("`3.1.4.1` 平行垂直证明", rendered)
        self.assertLess(rendered.index("`3.1.3.2` 空间向量运算的坐标表示"), rendered.index("`3.1.4.3` 向量夹角与直线夹角"))
        self.assertLess(rendered.index("`3.1.4.1` 平行垂直证明"), rendered.index("`3.1.4.5` 平面与平面的夹角"))
        self.assertIn("## 课程之外的补充前置", rendered)
        self.assertIn("## 教材书面题号与学习循环对应表", rendered)
        self.assertIn("教材书面题号：B12", rendered)
        self.assertIn("教材书面题号：B6、B7", rendered)
        self.assertIn("正数乘积固定时的和最值", rendered)
        self.assertIn("零基础放行未闭合", rendered)
        self.assertNotIn("1.2+1.3-C14", rendered)
        self.assertNotIn("micro专题1-C5", rendered)
        self.assertIn("B6、B7 首次使用二面角平面角", rendered)
        self.assertIn("课程计划里的“必听主课/补充课程”只是分组字段", rendered)
        self.assertNotRegex(rendered, r"\\n(?![A-Za-z])")
        self.assertIn(r"\neq", rendered)
        self.assertIn("A, P, B", rendered)
        self.assertIn("P, A, B, C", rendered)
        self.assertIn("本循环没有单独分配教材 A/B/C 题；本循环只完成上面的前置方法检查", rendered)
        self.assertIn("循环 5 前置", rendered)
        self.assertIn("左侧知识点｜知识点 4：数量积、夹角与投影向量", rendered)
        self.assertIn("投影向量定义、方向与标量长度", rendered)
        self.assertIn("仿射参数求交与同比分点截线", rendered)
        self.assertIn("教材例1", rendered)
        self.assertIn("变式1(11)", rendered)
        self.assertIn("`任务 38` C14", rendered)
        self.assertIn("A 组 夯实基础", rendered)
        self.assertIn("图形状态：视觉已核验", rendered)
        self.assertIn("图形状态：纯文字可作答", rendered)
        self.assertNotIn("图形状态：未完成视觉核验", rendered)
        self.assertNotIn("1.1-k1", rendered)
        self.assertNotIn("decomposition", rendered)
        self.assertNotIn("bridge-", rendered)
        self.assertNotIn("<img", rendered)
        self.assertNotIn("![", rendered)
        self.assertNotIn("imgs/", rendered)
        self.assertNotRegex(rendered, r"答案\s*[：:]|解析\s*[：:]|解答\s*[：:]|^解：")
        task_numbers = [int(value) for value in re.findall(r"`任务 (\d+)`", rendered)]
        self.assertEqual(task_numbers, list(range(1, packet["counts"]["total_numbered_learning_items"] + 1)))
        checkpoint_count = sum(
            len(cycle.get("method_checkpoints", [])) for cycle in packet["learning_cycles"]
        )
        guidance_count = len(re.findall(r"^  - \*\*思考入口：\*\*", rendered, flags=re.MULTILINE))
        self.assertEqual(
            guidance_count,
            packet["counts"]["total_numbered_learning_items"] + checkpoint_count,
        )
        self.assertEqual(
            len(re.findall(r"^  - \*\*书写骨架：\*\*", rendered, flags=re.MULTILINE)),
            guidance_count,
        )
        self.assertEqual(
            len(re.findall(r"^  - \*\*检查点：\*\*", rendered, flags=re.MULTILINE)),
            guidance_count,
        )
        self.assertIn("第一行写目标量和已知关系", rendered)
        self.assertIn("听完课程", rendered)

        cycle_one = rendered[rendered.index("## 循环 1/10"):rendered.index("## 循环 2/10")]
        self.assertLess(cycle_one.index("知识点 1：空间向量的相关概念"), cycle_one.index("任务 01"))
        self.assertLess(cycle_one.index("任务 03"), cycle_one.index("类型Ⅰ 线性运算"))
        self.assertLess(cycle_one.index("类型Ⅰ 线性运算"), cycle_one.index("任务 06"))
        self.assertIn("### 2. 本循环补充桥接", cycle_one)
        a_group = cycle_one[cycle_one.index("`任务 06` A1"):]
        self.assertIn("先问自己：是否需要统一起点、方向和基向量", a_group)
        self.assertIn("第二行用同一起点或基向量表示每一项", a_group)
        self.assertNotIn("设其中一个等于另一个的实数倍", a_group)

        for cycle in packet["learning_cycles"]:
            for item in cycle.get("worked_examples", []):
                body = exporter.clean_body_text(str(item.get("question_text", "")))
                if len(body) >= 20:
                    self.assertNotIn(body[:20], rendered)
            for item in [*cycle.get("direct_variants", []), *cycle.get("exercise_questions", [])]:
                body = exporter.clean_body_text(str(item.get("question_text", "")))
                if len(body) >= 20:
                    self.assertNotIn(body[:20], rendered)

    def test_section_14_knowledge_examples_follow_source_order(self) -> None:
        manifest = json.loads((ROOT / "chapter1_manifest.json").read_text(encoding="utf-8"))
        section = next(item for item in manifest["sections"] if item["id"] == "1.4")
        points = {item["id"]: item["examples"] for item in section["knowledge_points"]}
        self.assertEqual(points["1.4-k1"], ["例1", "例2"])
        self.assertEqual(points["1.4-k2"], ["例3"])
        self.assertEqual(points["1.4-k3"], [f"例{i}" for i in range(4, 11)])
        type_examples = [number for item in section["type_training"] for number in item["example_numbers"]]
        self.assertEqual(type_examples, list(range(11, 23)))

    def test_direct_variants_and_micro_layout_follow_source(self) -> None:
        manifest = json.loads((ROOT / "chapter1_manifest.json").read_text(encoding="utf-8"))
        by_section = {item["id"]: item for item in manifest["sections"]}
        self.assertEqual(sum(len(item["variants"]) for item in by_section["1.1"]["direct_variants"]), 8)
        self.assertEqual(sum(len(item["variants"]) for item in by_section["1.2+1.3"]["direct_variants"]), 4)
        self.assertEqual(sum(len(item["variants"]) for item in by_section["1.4"]["direct_variants"]), 3)
        self.assertEqual(sum(len(item["variants"]) for item in by_section["micro专题1"]["direct_variants"]), 1)
        self.assertEqual(by_section["micro专题1"]["knowledge_points"], [])
        self.assertEqual(by_section["micro专题1"]["layout_kind"], "content_outline_then_typical_examples")

    def test_chapter_learning_item_count_includes_examples_and_variants(self) -> None:
        manifest = json.loads((ROOT / "chapter1_manifest.json").read_text(encoding="utf-8"))
        counts = manifest["source_evidence"]["learning_item_counts"]
        self.assertEqual(counts, {"worked_examples": 58, "direct_variants": 16, "abc_exercises": 50, "total_numbered_learning_items": 124})
        generated = []
        for section in manifest["sections"]:
            folder = section["id"].replace("+", "_")
            packet = json.loads((ROOT / "data" / "packets" / folder / "learning_packet.json").read_text(encoding="utf-8"))
            generated.append(packet["counts"])
        self.assertEqual(sum(item["worked_examples"] for item in generated), 58)
        self.assertEqual(sum(item["direct_variants"] for item in generated), 16)
        self.assertEqual(sum(item["abc_exercises"] for item in generated), 50)
        self.assertEqual(sum(item["total_numbered_learning_items"] for item in generated), 124)

    def test_course_source_is_only_course_collection(self) -> None:
        catalog = json.loads((ROOT / "data" / "course_catalog.json").read_text(encoding="utf-8"))
        videos = [item for course in catalog["courses"] for item in course["videos"]]
        self.assertEqual(len(videos), 15)
        self.assertTrue(all("\\课程合集\\3.1 空间向量与立体几何\\" in item["file"] for item in videos))
        self.assertTrue(all(item["variant"] == "course_collection" for item in videos))

    def test_section_package_gate_wording_separates_packet_from_mastery(self) -> None:
        manifest = json.loads((ROOT / "chapter1_manifest.json").read_text(encoding="utf-8"))
        for section in manifest["sections"]:
            gate = section["coverage_gate"]
            self.assertIn("已通过", gate)
            self.assertNotIn("当前未达到", gate)
            self.assertIn("学生掌握度", gate)

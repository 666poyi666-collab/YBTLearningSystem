# 第 2 章题包骨架：2.3 第3节 直线的交点坐标与距离公式

状态：PENDING_OCR（骨架占位，**不含任何题目内容**）。

- 页范围：PDF 第 27–44 页（来自第 2 章无答案册书签目录，已确认）。
- 缺题门禁：题号/例题/变式/A-B-C 分组均未确认 → 全部页 needs_manual。
- 阻断原因：本构建会话无 PADDLE_OCR_TOKEN；教材为扫描件（无文本层）。
- 后续动作（主控）：配置 token 后运行

  ```
  python "C:\开发\ocr本地\paddleocr_ai_studio.py" "C:\Users\poyi\Downloads\【2025-2025版】选择性必修第1册\按章节合并（无答案册）\第2章 直线和圆的方程（无答案册）.pdf" --out "C:\开发\小工具\一本通学习系统_v7\data\ocr_live_current\second_chapter_109"
  ```

  再按 1.1 流程生成 packet/learning_packet/student_packet/answer_sidecar 并 verify-packet。
- 纪律：不得用答案册（习题册+答案册 PDF）填充本题包；OCR 完成前不得标注 VERIFIED。

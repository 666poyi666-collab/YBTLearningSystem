from __future__ import annotations

import unittest

from ybt_learning.common import delimiter_errors
from ybt_learning.packet import _apply_derived_formula_corrections


class AllChaptersFormulaCorrectionTests(unittest.TestCase):
    CASES = (
        (
            "ch3.s1",
            0,
            r"把平面内与两个定点\(F_1\)，\(F_2\)的距离的和等于常数（该常数一般记作\(2a\)，且\(2a > |F_1F_2|\)）的点的轨迹叫做椭圆。这两个定点叫做椭圆的焦点，两焦点间的距离（即\)|F_1F_2|$）叫做椭圆的焦距，焦距的一半称为半焦距。",
            r"（即\(|F_1F_2|\)）",
        ),
        (
            "4.4",
            53,
            r"②下标和性质：若  \(m+n=p+q\)， \((m,n,p,q \in \mathbb{N}^*\) \(，则\) a_m a_n = a_p a_q $；",
            r"\(a_m a_n = a_p a_q\)",
        ),
        (
            "4.5",
            73,
            r"C. 若数列 \(\{S_n\}\) 是等差比数列，则数列 \(\{a_{n+1}\)}$ 是等比数列",
            r"\(\{a_{n+1}\}\)",
        ),
        (
            "5.5",
            67,
            r"=2(x_{1}-x_{2})-a\ln\frac{x_{1}}{x_{2}}=\left(2-\frac{a}{x_{1}-x_{2}}\ln\frac{x_{1}}{x_{2}}\right)(x_{1}-x_{2}), 所以\frac{f(x_{1})-f(x_{2})}{x_{1}-x_{2}}=2-\frac{a}{x_{1}-x_{2}}\ln\frac{x_{1}}{x_{2}} $，",
            "所以 ",
        ),
    )

    def test_current_source_anchored_corrections_balance_math(self) -> None:
        for section, doc, text, expected in self.CASES:
            with self.subTest(section=section, doc=doc):
                page = {
                    "ocr_doc": doc,
                    "text": text,
                    "math_errors": delimiter_errors(text),
                }
                corrected = _apply_derived_formula_corrections(section, page)
                self.assertEqual(corrected["math_errors"], [])
                self.assertIn(expected, corrected["text"])
                self.assertEqual(len(corrected.get("derived_corrections", [])), 1)

    def test_corrections_are_idempotent(self) -> None:
        for section, doc, text, _ in self.CASES:
            with self.subTest(section=section, doc=doc):
                first = _apply_derived_formula_corrections(
                    section,
                    {"ocr_doc": doc, "text": text, "math_errors": delimiter_errors(text)},
                )
                second = _apply_derived_formula_corrections(section, first)
                self.assertEqual(second["text"], first["text"])
                self.assertEqual(second["math_errors"], [])


if __name__ == "__main__":
    unittest.main()

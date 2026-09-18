# -*- coding: utf-8 -*-
"""R62 任务2 探针：无 ANTLR 依赖直接驱动 UnifiedCodeGenerator，验证 builtin_map 映射。

背景：本机与 0.82 都缺 ANTLR **生成产物**（LightLangLexer.py / LightLangParser.py），
`cli/light_unified.py --backend antlr` 跑不起来（ModuleNotFoundError: LightLangLexer）。
但 UnifiedCodeGenerator 本身是「AST → Python」的纯代码生成器，不依赖 ANTLR，
可手工构造 antlrparser.light_ast 的节点直接驱动，从而验证 builtin_map 缺口。

用法： python light-merge/_probe_R62_unified_builtin.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, str(ROOT / "antlrparser"))
sys.path.insert(0, str(ROOT / "src"))

from light_ast import (  # noqa: E402
    ExpressionStatement, FunctionCall, Identifier, Module,
    SegmentDefinition, StringLiteral,
)
from code_generator_unified import UnifiedCodeGenerator  # noqa: E402

# R61 修的 4 个 stdlib 模块用到的裸名（hook 腿已修，unified 待修）
PROBE_NAMES = [
    "去除空格",     # 中文数字转换:54,167 / 参数解析:35,37 / 格式化:207 / 颜色:198,225,228
    "去除空白",
    "转整数",
    "转浮点",
    "转字符串",
]


def gen_call(name: str) -> str:
    mod = Module(
        name="probe",
        segments=[SegmentDefinition(
            name="主",
            parameters=[],
            body=[ExpressionStatement(
                expression=FunctionCall(
                    name=Identifier(name=name),
                    arguments=[StringLiteral(value=" x ")],
                )
            )],
        )],
    )
    return UnifiedCodeGenerator().generate(mod)


def main() -> None:
    g = UnifiedCodeGenerator()
    print("=" * 74)
    print("R62 任务2：UnifiedCodeGenerator builtin_map 裸名映射核查")
    print("=" * 74)
    print(f"builtin_map 键数 = {len(g.builtin_map)}")
    for n in PROBE_NAMES:
        in_map = n in g.builtin_map
        try:
            code = gen_call(n)
        except Exception as e:                     # noqa: BLE001
            print(f"  {n:<8} map={'有' if in_map else '无'}  生成异常 {type(e).__name__}: {e}")
            continue
        # 只看函数体（跳过文件头）
        body = [l for l in code.splitlines() if n in l]
        bare = [l for l in body if "_light_builtin." + n not in l and f"{n}(" in l]
        status = "裸名(风险)" if bare else ("已映射" if in_map else "映射无此键/但产物无裸名")
        print(f"  {n:<8} map={'有' if in_map else '无'}  -> {g.builtin_map.get(n, '-')}")
        print(f"           产物: {body[:1]}   [{status}]")

    print()
    print("=" * 74)
    print("核心判据：去除空格 必须映射为 _light_builtin.去除空白")
    print("=" * 74)
    ok = g.builtin_map.get("去除空格") == "_light_builtin.去除空白"
    print(f"  去除空格 -> {g.builtin_map.get('去除空格', '(缺失)')}   "
          f"{'PASS' if ok else 'FAIL'}")


if __name__ == "__main__":
    main()

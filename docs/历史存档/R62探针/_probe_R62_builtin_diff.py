# -*- coding: utf-8 -*-
"""R62 任务2 探针：对比 src/code_generator.py 与 src/code_generator_unified.py
两份 builtin_map 的键差集（只对比顶层 dict 字面量）。

用法： python light-merge/_probe_R62_builtin_diff.py
"""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(r"G:\dswork\duan-light-merge\light-merge")
HOOK = ROOT / "src" / "code_generator.py"
UNI = ROOT / "src" / "code_generator_unified.py"


def extract(path: Path) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if (isinstance(t, ast.Attribute) and t.attr == "builtin_map"
                        and isinstance(node.value, ast.Dict)):
                    out = {}
                    for k, v in zip(node.value.keys, node.value.values):
                        if isinstance(k, ast.Constant) and isinstance(k.value, str):
                            try:
                                out[k.value] = ast.unparse(v)
                            except Exception:
                                out[k.value] = "<unparse-fail>"
                    return out
    raise SystemExit(f"未找到 builtin_map：{path}")


def main() -> None:
    a = extract(HOOK)     # hook 腿（R61 已修 去除空格）
    b = extract(UNI)      # unified / ANTLR 腿
    print(f"hook 腿键数 = {len(a)}   unified 键数 = {len(b)}")
    print("=" * 74)
    print("【A】hook 有 / unified 缺（unified 缺口候选）")
    print("=" * 74)
    missing = [k for k in a if k not in b]
    for k in missing:
        print(f"  {k:<16} -> hook: {a[k]}")
    print(f"\n缺失键总数 = {len(missing)}")

    print()
    print("【B】unified 有 / hook 缺")
    print("=" * 74)
    extra = [k for k in b if k not in a]
    for k in extra:
        print(f"  {k:<16} -> unified: {b[k]}")
    print(f"\n独有键总数 = {len(extra)}")

    print()
    print("【C】同键不同值（行为差异）")
    print("=" * 74)
    diff = [(k, a[k], b[k]) for k in a if k in b and a[k] != b[k]]
    for k, va, vb in diff:
        print(f"  {k:<16}\n      hook   : {va}\n      unified: {vb}")
    print(f"\n同键不同值总数 = {len(diff)}")

    print()
    print("【D】关键点名核查")
    for k in ("去除空格", "去除空白", "截取", "格式化", "参数解析", "中文数字转换"):
        print(f"  {k:<12} hook={'有' if k in a else '无'}  unified={'有' if k in b else '无'}")


if __name__ == "__main__":
    main()

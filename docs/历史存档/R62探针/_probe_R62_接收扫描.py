# -*- coding: utf-8 -*-
"""R62 任务3 探针：扫描 tests/**/*.py 中旧式「段落/函数/段 名 接收 参数」写法并分类。

分类（据 parser_stmt.py:3641-3696 括号分支 vs 3697-3856 接收分支的等价性确认）：
  SAFE    —— 纯参数（可带 `参数: 类型` 内嵌类型标注），两分支产出一致 → 可机械替换
  STAR    —— 含 *args / **kwargs：括号分支无 STAR 处理 → 不可替换
  DEFAULT —— 含 默认值（等于 / =）：括号分支会把 `等于` 当参数名吞掉 → 不可替换
  SPTYPE  —— 含「参数名 类型名」空格式类型标注：括号分支会把类型名当第二个参数 → 不可替换
  ANON    —— 匿名闭包 `段落 接收 参数:`（L-022 形态，无段名）→ 禁改

用法： python light-merge/_probe_R62_接收扫描.py [--apply]
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(r"G:\dswork\duan-light-merge\light-merge")
TESTS = ROOT / "tests"

# 形态 A：`段落/函数/段` + 段名 + `接收`（⚠️ 关键字与段名之间有空格，段名自身
#          可由多个 token 拼接，但这里只取紧跟的第一个非空格 token 作段名）。
# 形态 B：裸段名（如 `构造` / `初始化`）+ `接收` —— 类方法/构造器走
#          _parse_paragraph_v2(name=...)（parser_stmt.py:676/740），同样发废弃警告。
HEAD_RE = re.compile(r"(?:^|(?<=[\s'\"（(、，,]))(段落|函数|段)\s+([^\s（(「」\n:：,，]+)\s+接收\b")
BARE_RE = re.compile(r"(?:^|(?<=[\s'\"（(、，,]))([^\s（(「」\n:：,，.。0-9]+)\s+接收\b")
ANON_RE = re.compile(r"(段落|函数|段)\s+接收\b")

# 形态 B 的前导 token 若是这些（语句/表达式上下文），不算段名
BARE_STOP = {
    '设', '定义', '当', '如果', '若', '遍历', '返回', '返', '打印', '导入', '导',
    '导出', '出', '跳出', '跳过', '尝试', '抛出', '匹配', '类', '接口', '接', '推迟',
    '断言', '为', '是', '等于', '不', '且', '或', '结果', '否则', '结束', '异步',
    '等待', '在', '之', '将', '把', '让', '使',
}


def classify(tail: str) -> str:
    """tail = `接收` 之后到行尾（或到 `:`）的参数片段。"""
    if "*" in tail:
        return "STAR"
    if re.search(r"等于|=(?!=)", tail):
        return "DEFAULT"
    # 空格式类型标注：参数名 后跟标识符/关键字 且不是 `:` 也不是 `,`
    # 形如 `接收 甲 整数:` / `接收 甲 整数, 乙 文本:`
    if re.search(r"[\u4e00-\u9fff\w]+\s+[\u4e00-\u9fff\w]+\s*[,:]", tail) \
            and not re.search(r"[\u4e00-\u9fff\w]+\s*:\s*[\u4e00-\u9fff\w]", tail):
        return "SPTYPE"
    return "SAFE"


def scan():
    rows = []
    for p in sorted(TESTS.rglob("*.py")):
        if "archive" in p.parts or "__pycache__" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for ln, line in enumerate(text.splitlines(), 1):
            if "接收" not in line:
                continue
            m = HEAD_RE.search(line)
            if m:
                kind = classify(line[m.end():])
            elif ANON_RE.search(line):
                kind = "ANON"
            else:
                mb = BARE_RE.search(line)
                if not mb or mb.group(1) in BARE_STOP:
                    continue
                kind = "BARE-" + classify(line[mb.end():])
            rows.append((p.relative_to(ROOT).as_posix(), ln, kind, line.strip()[:110]))
    return rows


def main() -> None:
    rows = scan()
    from collections import Counter, defaultdict
    c = Counter(k for _, _, k, _ in rows)
    print("=" * 78)
    print("R62 任务3：tests/ 旧式「接收」写法扫描")
    print("=" * 78)
    print(f"总命中 {len(rows)} 处 / {len({r[0] for r in rows})} 文件")
    for k in ("SAFE", "STAR", "DEFAULT", "SPTYPE", "ANON",
              "BARE-SAFE", "BARE-STAR", "BARE-DEFAULT", "BARE-SPTYPE"):
        print(f"  {k:<14} {c.get(k, 0):>4}")
    print()
    per_file = defaultdict(Counter)
    for f, _, k, _ in rows:
        per_file[f][k] += 1
    print("=" * 78)
    print("按文件（可改数 / 不可改数）")
    print("=" * 78)
    for f in sorted(per_file):
        cc = per_file[f]
        safe = sum(v for k, v in cc.items() if k.endswith("SAFE"))
        other = sum(v for k, v in cc.items() if not k.endswith("SAFE"))
        print(f"  {safe:>4} 可改 / {other:>3} 不可改   {f}")
    print()
    for k in ("STAR", "DEFAULT", "SPTYPE", "ANON",
              "BARE-STAR", "BARE-DEFAULT", "BARE-SPTYPE"):
        sub = [r for r in rows if r[2] == k]
        if not sub:
            continue
        print("=" * 78)
        print(f"【{k}】{len(sub)} 处（不可机械替换，逐条人工处置）")
        print("=" * 78)
        for f, ln, _, s in sub[:40]:
            print(f"  {f}:{ln}  {s}")


if __name__ == "__main__":
    main()

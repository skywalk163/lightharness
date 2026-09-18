# -*- coding: utf-8 -*-
"""R62 任务3：把 tests/**/*.py 里旧式「段落/函数/段 名 接收 参数:」批量现代化为「名(参数):」。

═══ 等价性确认（先做，依据 light-merge/src/parser_stmt.py:3587-3864）═══
两条分支共用同一段尾部（3827-3864：返回类型 `返回 X` / `-> X` → 冒号 → 体），
故「返回类型」与「体」两分支完全一致；差异只在 params 解析：

| 能力                     | 括号分支 L3641-3696 | 接收分支 L3697-3825 | 可机械替换 |
|--------------------------|--------------------|--------------------|-----------|
| 纯参数 `a, b`            | ✅                  | ✅                  | ✅ SAFE   |
| 内嵌类型 `a: 整数`        | ✅                  | ✅                  | ✅ SAFE   |
| 括号外类型 `(a):整数`     | ✅（独有）           | ❌                  | —         |
| *args / **kwargs         | ❌（遇 * 直接 break） | ✅                  | ⛔ STAR   |
| 默认值 `a 等于 5` / `a=5` | ❌（`等于` 被当参数名吞）| ✅                 | ⛔ DEFAULT|
| 空格式类型 `a 整数`       | ❌（类型名当第 2 参） | ✅（需 BUILTIN_TYPES）| ⛔ SPTYPE |
| FFI `a 为 整数`           | ❌                  | ✅                  | ⛔ SPTYPE |
| 匿名闭包 `段落 接收 x:`   | —（另一条路 L-022）  | —                   | ⛔ ANON   |

结论：**只替换 SAFE**（纯参数 + 可选内嵌 `:` 类型标注）。其余逐条人工处置/保留。

═══ 禁改项 ═══
1. 匿名闭包 `段落 接收 参数:`（无段名）；
2. 作为**断言/期望输出文本**的旧式串（如 `assert "段落 X 接收 a:" in content`）；
3. Python 注释里的旧式示例。

用法：
    python light-merge/_任务3_R62_应用.py --dry-run   # 只列改动
    python light-merge/_任务3_R62_应用.py             # 落盘
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(r"G:\dswork\duan-light-merge\light-merge")
TESTS = ROOT / "tests"

KW = r"(?:段落|函数|段)"
NAME = r"[^\s（(「」\n:：,，、。]+"
# 段名允许多个 token 拼接（parser 会把连续 IDENTIFIER/KEYWORD 拼成段名），非贪婪取到 `接收`
# 前导边界用**捕获组**而非 lookbehind：.light 源串里大量 `\n` 换行转义，
# 紧邻 `段落` 的前一个字符是 `n`（`\n` 的第二字符），lookbehind 无法表达
# 「前两字符是 \n」这类成对条件 → 改用捕获组，允许 `\n`/`\t`/`\r` 转义对。
PRE = r"(^|[\s'\"（(、，,。]|\\n|\\t|\\r)"
HEAD_RE = re.compile(rf"{PRE}({KW})\s+((?:{NAME}\s+)*?{NAME})\s+接收\b")
BARE_RE = re.compile(rf"{PRE}({NAME})\s+接收\b")
ANON_RE = re.compile(rf"{KW}\s+接收\b")

BARE_STOP = {
    '设', '定义', '当', '如果', '若', '遍历', '遍', '返回', '返', '打印', '导入', '导',
    '导出', '出', '跳出', '跳', '跳过', '过', '断', '跃', '尝试', '试', '抛出', '抛',
    '掷', '匹配', '配', '类', '接口', '接', '推迟', '断言', '为', '是', '等于', '不',
    '且', '或', '结果', '否则', '结束', '异步', '等待', '在', '之', '将', '把', '让',
    '使', '外部', '静态', '严格', '异', '构造', '初始化',
}
# `构造` 是类构造器段名，允许改；上面 BARE_STOP 里不应含它 —— 单独白名单覆盖
BARE_ALLOW = {'构造', '构'}

SEP = r"(?:,|，|、)"
# SAFE 参数文法：name [: type]，分隔符 , / ，/ 、
# ⚠️ 两者都必须把 `'` `"` `\` 排除在字符集外：这些 .light 源码是嵌在 Python
# 字符串字面量里的，若参数名把结尾的 `"` 吞进去，写出的是**语法错误的 .py**
# （R62 首轮实测：tests/test_migration.py:98 变成 `source = "段 添加(a, b")`）。
PNAME = r"[^\s（(「」\n:：,，、。）)\]\['\"\\]+"
PTYPE = r"[^\s（(「」\n,，、。）)'\"\\]+"
PARAM = rf"{PNAME}(?:\s*[:：]\s*{PTYPE})?"
# 允许**空参数**（`段落 主 接收:` → `段落 主():`）——括号分支遇 RPAREN 直接退出
# 循环得 params=[]，与接收分支的 params=[] 完全一致，可安全替换。
PARAMS_SAFE = re.compile(rf"^\s*(?:{PARAM}(?:\s*{SEP}\s*{PARAM})*)?\s*$")


# 定义冒号后可直接跟段体首条语句（同一行的紧凑写法，如
# `'段 计算 接收：返回 甲 加 乙。结束。'`）
BODY_HEAD = ('返回', '返', '设', '定义', '打印', '印', '如果', '若', '当', '遍历', '遍',
             '尝试', '抛出', '匹配', '导入', '导出', '跳出', '跳过', '结束', '断言',
             '等待', '异步', '延迟')


def def_colon_pos(tail: str) -> int:
    """返回「定义冒号」在 tail 中的下标；找不到则返回 len(tail)。

    定义冒号判定（三选一，命中即止）：
      1. 其后紧跟 行尾 / `\\n` / `。` / Python 串终止符 `'"`）)；
      2. 其后紧跟段体首条语句关键字（紧凑写法 `接收：返回 …`）；
    内嵌类型冒号（`a: 整数`，后面跟的是类型名）不算。
    """
    for i, ch in enumerate(tail):
        if ch in ":：":
            rest = tail[i + 1:]
            if rest == "" or rest[:2] == "\\n" or rest[:1] in "。'\"）)":
                return i
            if rest.startswith(BODY_HEAD):
                return i
    return len(tail)


# 返回类型子句（两分支共用尾部解析，不属 params，验证前先剥离）：
# `段落 加法 接收 a: 整数, b: 整数 返回 整数：` / `-> 整数`
RET_RE = re.compile(r"\s*(?:返回|->|→)\s+.*$")


def classify(tail: str) -> tuple[str, str]:
    """返回 (类别, 参数片段)。类别 ∈ SAFE / STAR / DEFAULT / SPTYPE。"""
    if "*" in tail:
        return "STAR", ""
    end = def_colon_pos(tail)
    params = RET_RE.sub("", tail[:end])
    if re.search(r"等于|=(?!=)", params):
        return "DEFAULT", params
    if PARAMS_SAFE.match(params):
        return "SAFE", params
    return "SPTYPE", params


# ⛔ FFI 声明走**另一条解析链**（parser_stmt.py:5989+ _parse_external →
#    _parse_ffi_function_decl / _parse_ffi_callback_def），既不发本轮要清的
#    DeprecationWarning，也不支持括号式参数 → 一律不碰。
FFI_RE = re.compile(r"外部|@C|变长参数|函数指针|结构体|联合体|类型别名|位域")


def is_forbidden_line(line: str, mpos: int) -> bool:
    """禁改上下文判定。"""
    if FFI_RE.search(line):              # FFI 声明（另一条解析链，且不支持括号式）
        return True
    head = line[:mpos]
    if "#" in head:                      # Python 注释里的示例
        return True
    if re.search(r"\bassert\b", head):   # 断言/期望输出文本
        return True
    if re.search(r"(?<!\w)in\s+['\"]", head):
        return True
    if "期望" in head or "expected" in head.lower():
        return True
    return False


def convert_params(params: str) -> str:
    """`a, b: 整数` → `a, b: 整数`（分隔符归一为 `, `）。"""
    parts = [p.strip() for p in re.split(SEP, params) if p.strip()]
    return ", ".join(parts)


def transform_line(line: str) -> tuple[str, str]:
    """返回 (新行, 类别)。类别 NOTouch 表示未改动。"""
    if "接收" not in line:
        return line, "NOTouch"
    m = HEAD_RE.search(line)
    if m:
        kw, seg = m.group(2), m.group(3).strip()
        mpos = m.start(2)                 # 前导边界组不计入「改动起点」
        if is_forbidden_line(line, mpos):
            return line, "SKIP-CTX"
        kind, params = classify(line[m.end():])
        if kind != "SAFE":
            return line, "SKIP-" + kind
        new = f"{line[:mpos]}{kw} {seg}({convert_params(params)}){line[m.end() + len(params):]}"
        return new, "SAFE"
    if ANON_RE.search(line):
        return line, "SKIP-ANON"
    mb = BARE_RE.search(line)
    if mb:
        seg = mb.group(2)
        mpos = mb.start(2)
        if seg not in BARE_ALLOW or is_forbidden_line(line, mpos):
            return line, "SKIP-CTX"
        kind, params = classify(line[mb.end():])
        if kind != "SAFE":
            return line, "SKIP-" + kind
        new = f"{line[:mpos]}{seg}({convert_params(params)}){line[mb.end() + len(params):]}"
        return new, "BARE-SAFE"
    return line, "NOTouch"


def main() -> None:
    dry = "--dry-run" in sys.argv
    from collections import Counter
    stat = Counter()
    changed_files = []
    for p in sorted(TESTS.rglob("*.py")):
        if "archive" in p.parts or "__pycache__" in p.parts:
            continue
        # ⚠️ 必须 newline="" 读：core.autocrlf=true（blob=LF / 工作树=CRLF），
        # 用 read_text() 会把 CRLF 统一成 LF，写回后整个文件变成 LF → 巨大假 diff。
        import io
        with io.open(p, encoding="utf-8", newline="") as f:
            text = f.read()
        lines = text.splitlines(keepends=True)
        out = []
        n_change = 0
        for ln in lines:
            body = ln.rstrip("\r\n")
            eol = ln[len(body):]
            new_body, kind = transform_line(body)
            stat[kind] += 1
            if new_body != body:
                n_change += 1
                if dry:
                    print(f"  [{kind}] {p.relative_to(ROOT).as_posix()}\n"
                          f"    - {body.strip()[:100]}\n"
                          f"    + {new_body.strip()[:100]}")
            out.append(new_body + eol)
        if n_change:
            new_text = "".join(out)
            # 语法自证：改写后的 .py 必须仍是合法 Python，否则整文件放弃改写
            # （首轮正是靠这道闸发现参数名吞掉结尾引号的 bug）。
            try:
                compile(new_text, str(p), "exec")
            except SyntaxError as e:
                print(f"  ⛔ 放弃改写（Python 语法自证失败）：{p.relative_to(ROOT).as_posix()} "
                      f"line {e.lineno}: {e.msg}")
                stat["ABORT-SYNTAX"] += 1
                continue
            changed_files.append((p, n_change))
            if not dry:
                with io.open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(new_text)
    print("=" * 70)
    print(f"{'DRY-RUN' if dry else 'APPLIED'}  改动行合计 {sum(v for k, v in stat.items() if k in ('SAFE', 'BARE-SAFE'))}"
          f"  涉及文件 {len(changed_files)}")
    print("=" * 70)
    for k, v in sorted(stat.items()):
        print(f"  {k:<14} {v:>4}")


if __name__ == "__main__":
    main()

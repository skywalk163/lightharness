#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 安全替换.py —— 词法感知的批量文本替换工具（光明工程层）
# ==========================================================================
# 背景（L-009）：对 .light 源码做「文本级批量替换」（如 PowerShell 的
#   (Get-Content x.light -Raw) -replace '导入 builtins', "导入 builtins`n从 JSON 导入 序列化JSON"
# 会命中注释行内嵌的「导入 X」字样，把注释拦腰劈成代码行 → 伪语法错误。
# 注释本应被词法忽略，文本工具却误伤。
#
# 本工具做「词法感知替换」：
#   1. 整行注释（行首非空白为 #）整行跳过；行内 # 之后也视为注释（光明语义）。
#   2. 字符串字面量（双引号串 / 单引号串 / 三引号串（三个连续同号引号，可跨行）、
#      含 f/r/b 前缀）内的目标串跳过，不被替换。
#   3. 仅对「真实代码区域」的目标串做替换。
#   4. 输出替换前后差异统计（命中/跳过/受影响行）。
#   5. 支持 --dry-run 只报告不落盘；支持 --out 写回副本。
#   6. 严禁覆盖输入源码：当 --out 与输入同路径时直接拒绝。
#
# 用法：
#   python scripts/安全替换.py 输入.light "目标串" "替换串" --out 输出.light
#   python scripts/安全替换.py 输入.light "目标串" "替换串" --dry-run
#   python scripts/安全替换.py --self-test        # 内置确定性自测（不依赖文件）
#
# 注意：替换串可含换行（CI/脚本里用 PowerShell 的 `n 或 Bash 的 $'...\n...' 传入），
#       工具按字面串替换，不解释正则。
# ==========================================================================
import argparse
import os
import sys

# 词法状态：光明注释为行作用域（# 到行尾）；字符串可跨行（尤其三引号）。
# 跨行时需在逐行扫描间保持「是否在字符串内」的状态。
TRIPLES = ('"""', "'''")


def _split_term(line):
    """拆分行尾换行符，保留原样（避免意外改写换行风格）。"""
    if line.endswith('\r\n'):
        return line[:-2], '\r\n'
    if line.endswith('\n'):
        return line[:-1], '\n'
    if line.endswith('\r'):
        return line[:-1], '\r'
    return line, ''


def _scan_line(body, target, repl, st, stats, changed_set):
    """扫描单行 body，返回替换后的新 body。st 为跨行持久状态字典。

    st 结构：
        st['str']    : 普通字符串的引号字符（' 或 "），None 表示不在字符串内
        st['triple'] : 三引号分隔符（三个连续同号引号），None 表示不在三引号串内
    changed_set 用于收集发生变化的原始行（供 diff 展示）。
    """
    if not target:
        return body

    res = []
    comment_active = False  # 注释为行作用域，每行重置
    i = 0
    n = len(body)
    line_changed = False
    orig = body

    while i < n:
        c = body[i]

        # ① 行内注释（# 到行尾）——整段跳过替换
        if comment_active:
            if body.startswith(target, i):
                stats['skipped'] += 1
            res.append(c)
            i += 1
            continue

        # ② 三引号字符串（可跨行）——整段跳过替换
        if st['triple'] is not None:
            if body.startswith(st['triple'], i):
                res.append(st['triple'])
                i += 3
                st['triple'] = None
                continue
            if body.startswith(target, i):
                stats['skipped'] += 1
            res.append(c)
            i += 1
            continue

        # ③ 普通字符串（单行，含反斜杠转义）——整段跳过替换
        if st['str'] is not None:
            if body.startswith(target, i):
                stats['skipped'] += 1
            res.append(c)
            if c == '\\' and i + 1 < n:
                res.append(body[i + 1])
                i += 2
                continue
            if c == st['str']:
                st['str'] = None
            i += 1
            continue

        # ④ 代码区域
        if c == '#':
            comment_active = True
            res.append(c)
            i += 1
            continue
        if c == '"' or c == "'":
            # 先判断是否三引号
            if body[i:i + 3] in TRIPLES:
                st['triple'] = body[i:i + 3]
                res.append(st['triple'])
                i += 3
                continue
            st['str'] = c
            res.append(c)
            i += 1
            continue
        # 目标串匹配（仅代码区域才替换）
        if body.startswith(target, i):
            # 保留行首缩进：多行替换时，续行对齐到本行缩进，避免破坏代码块层级
            if '\n' in repl:
                indent = body[:len(body) - len(body.lstrip())]
                repl_lines = repl.split('\n')
                inserted = repl_lines[0]
                for extra in repl_lines[1:]:
                    inserted += '\n' + indent + extra
                res.append(inserted)
            else:
                res.append(repl)
            i += len(target)
            stats['replaced'] += 1
            line_changed = True
            continue
        res.append(c)
        i += 1

    new_body = ''.join(res)
    if line_changed or new_body != orig:
        changed_set.add(orig)
    return new_body


def safe_replace(text, target, repl, stats):
    """对整段文本做词法感知替换，返回新文本，并累计 stats。"""
    st = {'str': None, 'triple': None}
    changed_lines = []  # 保存 (orig, new) 供 diff
    out = []
    for line in text.splitlines(keepends=True):
        body, term = _split_term(line)
        orig_body = body
        new_body = _scan_line(body, target, repl, st, stats, set())
        if new_body != orig_body:
            # 记录该行原始与替换后内容（仅取首行，避免多行替换把差异淹没）
            changed_lines.append((orig_body, new_body))
        out.append(new_body + term)
    stats['changed_lines'] = changed_lines
    return ''.join(out)


def _print_stats(input_path, target, stats, out_mode):
    print("安全替换 统计:")
    print(f"  输入文件 : {input_path}")
    print(f"  目标串   : {target!r}")
    print(f"  总行数   : {stats['total_lines']}")
    print(f"  命中替换 : {stats['replaced']} 处")
    print(f"  跳过     : {stats['skipped']} 处（位于注释/字符串字面量内，未动）")
    print(f"  受影响行 : {len(stats['changed_lines'])} 行（行内容发生变化）")
    print(f"  写回模式 : {out_mode}")
    if stats['changed_lines']:
        print("  变更行预览:")
        for orig, new in stats['changed_lines'][:50]:
            for ol in orig.split('\n'):
                print(f"    - {ol}")
            for nl in new.split('\n'):
                print(f"    + {nl}")


def _self_test():
    """内置确定性自测：不依赖任何文件，覆盖注释/字符串/代码/三引号/行内注释。"""
    cases = [
        # (描述, 源文本, 期望包含, 期望不包含)
        ("整行注释应跳过", "# 导入 builtins 其他\n段落 主:\n主()\n",
         "# 导入 builtins 其他", "导入 builtins\n从 JSON"),
        ("字符串内应跳过", '打印 "注释 导入 builtins 演示"\n',
         '打印 "注释 导入 builtins 演示"', "从 JSON 导入 序列化JSON"),
        ("真实代码行应替换", "导入 builtins\n",
         "导入 builtins\n从 JSON 导入 序列化JSON", None),
        ("行内注释应跳过", '设 X 为 1  # 导入 builtins 尾巴\n',
         '设 X 为 1  # 导入 builtins 尾巴', "从 JSON 导入 序列化JSON"),
        ("三引号串应跳过", '打印 """块内 导入 builtins 也跳过"""\n',
         '打印 """块内 导入 builtins 也跳过"""', "从 JSON 导入 序列化JSON"),
    ]
    target = "导入 builtins"
    repl = "导入 builtins\n从 JSON 导入 序列化JSON"
    ok = True
    for desc, src, must_have, must_not in cases:
        stats = {'replaced': 0, 'skipped': 0, 'total_lines': 0, 'changed_lines': []}
        out = safe_replace(src, target, repl, stats)
        good = (must_have in out) and (must_not is None or must_not not in out)
        # 真实代码行那条应 replaced>=1；其余应 skipped>=1 且 replaced==0
        if desc.startswith("真实代码"):
            good = good and stats['replaced'] >= 1
        else:
            good = good and stats['replaced'] == 0 and stats['skipped'] >= 1
        status = "通过" if good else "失败"
        if not good:
            ok = False
        print(f"  [{status}] {desc}  (replaced={stats['replaced']}, skipped={stats['skipped']})")
    print("自测结果:", "全部通过" if ok else "存在失败")
    return 0 if ok else 1


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if '--self-test' in argv:
        return _self_test()

    p = argparse.ArgumentParser(
        description="词法感知批量替换：跳过 .light 注释与字符串内的目标串，避免误伤源码。")
    p.add_argument("input", help="输入 .light 源码路径（只读，不会被修改）")
    p.add_argument("target", help="要替换的目标子串（字面匹配，非正则）")
    p.add_argument("repl", help="替换串（可含换行）")
    p.add_argument("--out", help="写回路径（副本）。必须不同于输入，避免覆盖源码。")
    p.add_argument("--dry-run", action="store_true", help="只报告差异统计，不写任何文件")
    p.add_argument("--encoding", default="utf-8", help="文件编码（默认 utf-8）")
    args = p.parse_args(argv)

    if not os.path.isfile(args.input):
        print(f"错误: 找不到输入文件 {args.input}", file=sys.stderr)
        return 1

    # 安全护栏：禁止 --out 覆盖输入源码
    if args.out:
        abs_in = os.path.abspath(args.input)
        abs_out = os.path.abspath(args.out)
        if abs_in == abs_out:
            print("错误: --out 与输入文件相同，拒绝覆盖源码（请输出到副本）。",
                  file=sys.stderr)
            return 1

    with open(args.input, 'r', encoding=args.encoding) as f:
        text = f.read()

    stats = {'replaced': 0, 'skipped': 0,
             'total_lines': len(text.splitlines()), 'changed_lines': []}
    new_text = safe_replace(text, args.target, args.repl, stats)

    if args.dry_run:
        out_mode = "dry-run（未写回）"
        _print_stats(args.input, args.target, stats, out_mode)
        return 0

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, 'w', encoding=args.encoding) as f:
            f.write(new_text)
        out_mode = args.out
    else:
        out_mode = "stdout（未写文件）"
        sys.stdout.write(new_text)
        if not new_text.endswith('\n'):
            sys.stdout.write('\n')

    _print_stats(args.input, args.target, stats, out_mode)
    return 0


if __name__ == '__main__':
    sys.exit(main())

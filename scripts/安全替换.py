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
# 编辑日志（T-0336）：成功写盘后默认记一条「编辑前后」日志；加 --check 时编辑前后
#   各跑一次 `light ai check --run --json --no-corpus`（--no-corpus 不污染报错归档），
#   outcome 由两次 check 推导。不传 --check 时 check_* 写 null、outcome=unknown。
#   python scripts/安全替换.py 输入.light "甲[9]" "甲[0]" --out 输出.light --check
#   --no-edit-log 关闭日志；--edit-kind auto|FR|RW|PATCH 可显式声明编辑方式。
#
# 注意：替换串可含换行（CI/脚本里用 PowerShell 的 `n 或 Bash 的 $'...\n...' 传入），
#       工具按字面串替换，不解释正则。
# ==========================================================================
import argparse
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

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


# --------------------------------------------------------------------------
# 编辑日志钩子（T-0336）
#   * 只在「成功写盘」后追加记录；干跑 / 输出到 stdout 不产生日志。
#   * check 跑不出真实结果 → None → check_* 落 null、outcome=unknown，绝不猜。
#   * 下面这些函数不参与替换语义，_self_test() 也完全不碰它们。
# --------------------------------------------------------------------------
_IDENT_RE = re.compile(r"^[^\W\d]\w*$", re.UNICODE)


def _load_edit_log():
    """动态加载同目录的 `编辑日志.py`（中文模块名，不动 sys.path）。"""
    try:
        path = Path(__file__).resolve().parent / "编辑日志.py"
        spec = importlib.util.spec_from_file_location("_lh_edit_log", path)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except (OSError, ImportError, AttributeError, SyntaxError):
        return None


def _find_light_cli(explicit=None):
    """定位 light CLI；找不到返回 None（check 结果不猜）。"""
    cands = []
    if explicit:
        cands.append(Path(explicit))
    if os.environ.get("LIGHT_CLI"):
        cands.append(Path(os.environ["LIGHT_CLI"]))
    for parent in Path(__file__).resolve().parents[:4]:
        cands.append(parent / "light" / "cli" / "light.py")
        cands.append(parent / "cli" / "light.py")
    cands.append(Path("/home/skywalk/dswork/light/cli/light.py"))
    for c in cands:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def _run_check(mod, cli, path):
    """跑一次 `light ai check --run --json --no-corpus`，返回 schema 的 check 对象。"""
    cmd = [sys.executable, str(cli), "ai", "check", str(path),
           "--run", "--json", "--no-corpus"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=180)
    except (OSError, subprocess.SubprocessError) as exc:
        print(f"警告: check 执行失败（check_* 记 null）: {exc}", file=sys.stderr)
        return None
    return mod.parse_check_json(r.stdout, r.returncode)


def _light_meta(cli):
    """复现所需的版本 / 后端；拿不到就留空字符串，不编造。"""
    version = os.environ.get("LIGHT_VERSION", "")
    backend = os.environ.get("LIGHT_BACKEND", "")
    if not version and cli:
        try:
            r = subprocess.run([sys.executable, str(cli), "--version"],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=30)
            if r.returncode == 0 and r.stdout.strip():
                version = r.stdout.strip().splitlines()[0][:80]
        except (OSError, subprocess.SubprocessError):
            pass
    return version, backend


def _choose_edit_kind(target, repl, text, explicit=None):
    """按**实际行为**选 FR / RW / PATCH，不许乱标。

    RW    —— 目标串就是整份文件（整份内容被换掉，等价于全文件重写）；
    FR    —— 目标串与替换串都是单个标识符（词法感知地逐个标识符替换）；
    PATCH —— 其余：对文件里的目标子串做整串替换（本工具默认行为）。
    """
    if explicit and explicit != "auto":
        return explicit
    if target and text and target.strip() == text.strip():
        return "RW"
    if _IDENT_RE.match(target or "") and _IDENT_RE.match(repl or ""):
        return "FR"
    return "PATCH"


def _emit_edit_log(mod, args, text, new_text, stats,
                   check_before, check_after, cli):
    """成功写盘后 append 一条记录；失败只告警，不改变替换本身的退出码。"""
    repo_root = (Path(args.repo_root).resolve() if args.repo_root
                 else Path(__file__).resolve().parents[1])
    version, backend = _light_meta(cli)
    kind = _choose_edit_kind(args.target, args.repl, text, args.edit_kind)
    try:
        rec = mod.build_record(
            repo=args.repo, file=mod.relative_file(args.out, repo_root=repo_root),
            edit_kind=kind, before_text=text, after_text=new_text,
            check_before=check_before, check_after=check_after,
            session_id=args.session_id or None, task_id=args.task_id or None,
            agent=args.agent or None, light_version=version, backend=backend,
            replaced=stats.get("replaced", 0),
            target=mod.mask_paths(args.target))
        written = mod.record(rec)
    except (OSError, ValueError, TypeError) as exc:
        print(f"警告: 编辑日志写入失败: {exc}", file=sys.stderr)
        return
    p = mod.log_path(rec["ts"])
    if written is None:
        print(f"编辑日志: 去重跳过（未重复写入）: {p}")
    else:
        print(f"编辑日志: {p}  ← edit_kind={kind} outcome={rec['outcome']}")


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
    # --- 编辑日志钩子（T-0336）---
    p.add_argument("--edit-log", dest="edit_log", action="store_true", default=True,
                   help="成功写盘后记一条「编辑前后」日志（默认开）")
    p.add_argument("--no-edit-log", dest="edit_log", action="store_false",
                   help="关闭编辑日志")
    p.add_argument("--check", action="store_true",
                   help="编辑前后各跑一次 light ai check --run --json --no-corpus")
    p.add_argument("--light-cli", help="light/cli/light.py 路径（默认自动探测）")
    p.add_argument("--edit-kind", choices=["auto", "FR", "RW", "PATCH"], default="auto",
                   help="edit_kind；auto 按实际替换行为判定（默认）")
    p.add_argument("--repo", default="lightharness", help="日志里的 repo 名")
    p.add_argument("--repo-root", help="repo 根目录，用于把 file 收敛成相对路径")
    p.add_argument("--session-id", default="")
    p.add_argument("--task-id", default="")
    p.add_argument("--agent", default="")
    args = p.parse_args(argv)

    if args.check and (not args.out or args.dry_run):
        print("提示: --check 需要 --out 且非 --dry-run；本次不跑 check、不记日志",
              file=sys.stderr)

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

    # 编辑日志模块与 checker 都是可选的：缺任何一个都不伪造结果。
    mod = _load_edit_log() if (args.edit_log or args.check) else None
    cli = _find_light_cli(args.light_cli) if args.check else None
    will_write = bool(args.out) and not args.dry_run
    check_before = check_after = None
    if args.check and will_write and mod and cli:
        check_before = _run_check(mod, cli, args.input)  # 对「改之前」的文件跑
    elif args.check and will_write and cli is None:
        print("警告: 找不到 light CLI，check_* 记 null（outcome=unknown）", file=sys.stderr)

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
        if args.check and mod and cli:
            check_after = _run_check(mod, cli, args.out)  # 对「改之后」的文件跑
        if args.edit_log and mod:
            _emit_edit_log(mod, args, text, new_text, stats,
                           check_before, check_after, cli)
        elif args.edit_log:
            print("警告: 未找到 scripts/编辑日志.py，跳过编辑日志", file=sys.stderr)
    else:
        out_mode = "stdout（未写文件）"
        sys.stdout.write(new_text)
        if not new_text.endswith('\n'):
            sys.stdout.write('\n')

    _print_stats(args.input, args.target, stats, out_mode)
    return 0


if __name__ == '__main__':
    sys.exit(main())

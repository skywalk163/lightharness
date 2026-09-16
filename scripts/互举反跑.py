#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""互举反跑 `互举反跑.py` —— lightharness 全树 .light 的「light 编译器可解析性」回归门。

背景（互举闭环）
----------------
lightharness（用光明语言复刻的 DeepSeek Harness）的**全部源码就是光明源码**，
因此「light-merge 的编译器能不能 tokenize + parse lightharness 全树」是互举闭环的
第一条硬约束：编译器一退化，框架就整体不可编译。

R25~R39 每轮都是靠临时探针（`_antirun_r2x_*.py`）手工跑这件事，没有正式件。
本脚本把它正式化：**扫描 → tokenize+parse → 与基线对比 → 只拦「新增解析失败」**。

判据
----
* `0 新增解析失败` = 绿（退出码 0）；有新增 = 红（退出码 1，`--warn` 只警告）
* 基线里失败、本次通过 → 报「已修复」（提示刷新基线）
* 基线里失败、本次仍失败 → 基线内，不拦（存量欠账）

用法
----
    # 常规：对比基线（首次会提示用 --update-baseline 生成）
    python scripts/互举反跑.py

    # 首次接入 / 收口时刷新基线
    python scripts/互举反跑.py --update-baseline

    # 只跑部分根目录（省时）
    python scripts/互举反跑.py --roots src examples

    # 产出报告（JSON + 文本）
    python scripts/互举反跑.py --json reports/反跑.json --report reports/反跑.txt

    # 只警告不阻断；并打印全部失败文件的错误摘要
    python scripts/互举反跑.py --warn --detail

退出码
------
    0   0 新增解析失败（绿）
    1   有新增解析失败（红）——`--warn` 时恒 0
    2   环境错误（找不到 light-merge 编译器 / 基线不可读）

依赖：仅 Python 标准库；编译器来自 light-merge（`LIGHT_MERGE` 环境变量可覆盖）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # lightharness/
# 与 运行.py 同口径：光明编译器来自 light-merge，可用环境变量覆盖
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
DEFAULT_ROOTS = ('src', 'stdlib', 'examples', 'tests')
DEFAULT_BASELINE = os.path.join(ROOT, 'scripts', '互举反跑基线.json')
SKIP_DIRS = {'.git', '__pycache__', '.venv', 'build', 'dist', '.light_cache',
             '.pytest_cache', 'node_modules'}


def _utf8_stdout():
    """Windows 控制台默认 GBK，print 中文/⚠️ 会 UnicodeEncodeError 把整步堵死。"""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            try:
                stream.reconfigure(encoding='utf-8')
            except Exception:                                   # noqa: BLE001
                pass


def load_compiler():
    """载入 light-merge 的 Lexer / LightParser（SRC 后端，与 cli `light run` 同一条链）。"""
    src = os.path.join(LIGHT_MERGE, 'src')
    if not os.path.isdir(src):
        raise RuntimeError('找不到光明编译器（LIGHT_MERGE=%s）' % LIGHT_MERGE)
    if src not in sys.path:
        sys.path.insert(0, src)
    if LIGHT_MERGE not in sys.path:
        sys.path.insert(0, LIGHT_MERGE)
    from lexer import Lexer                    # noqa: E402
    from light_parser_v3 import LightParser    # noqa: E402
    try:
        from src.version import VERSION as LIGHT_VERSION   # noqa: E402
    except Exception:                                       # noqa: BLE001
        try:
            from version import VERSION as LIGHT_VERSION   # noqa: E402
        except Exception:                                   # noqa: BLE001
            LIGHT_VERSION = 'unknown'
    return Lexer, LightParser, str(LIGHT_VERSION)


def light_merge_rev():
    """light-merge 当前提交（基线可追溯：记录「在哪版编译器下标定」）。"""
    try:
        out = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                             cwd=LIGHT_MERGE, capture_output=True, timeout=20)
        rev = out.stdout.decode('utf-8', 'replace').strip()
        dirty = subprocess.run(['git', 'status', '--porcelain', '--', 'src'],
                               cwd=LIGHT_MERGE, capture_output=True, timeout=20)
        if dirty.stdout.strip():
            rev += '+dirty(src)'
        return rev or 'unknown'
    except Exception:                                       # noqa: BLE001
        return 'unknown'


def collect(roots):
    """收集待检 .light 文件（相对 lightharness 的 POSIX 相对路径）。"""
    files = []
    for r in roots:
        base = r if os.path.isabs(r) else os.path.join(ROOT, r)
        if os.path.isfile(base) and base.endswith('.light'):
            files.append(base)
            continue
        if not os.path.isdir(base):
            continue
        for dp, dn, fn in os.walk(base):
            dn[:] = [d for d in dn if d not in SKIP_DIRS]
            for f in fn:
                if f.endswith('.light'):
                    files.append(os.path.join(dp, f))
    return sorted(set(files))


def digest_of(msg):
    return hashlib.sha1((msg or '').encode('utf-8', 'replace')).hexdigest()[:12]


def brief(msg, limit=200):
    """把错误信息压成单行摘要。"""
    if not msg:
        return ''
    s = re.sub(r'\s+', ' ', str(msg)).strip()
    return s[:limit]


def check_one(path, Lexer, LightParser):
    """对单个文件做 tokenize + parse，返回 (状态, 摘要)。

    状态：OK / LEX（词法失败）/ PARSE（语法失败）/ READ（读文件失败）
    """
    try:
        with open(path, encoding='utf-8-sig', errors='replace') as fh:
            text = fh.read()
    except Exception as exc:                                # noqa: BLE001
        return 'READ', brief(exc)
    try:
        Lexer(deterministic=True).tokenize(text)
    except Exception as exc:                                # noqa: BLE001
        return 'LEX', brief('%s: %s' % (type(exc).__name__, exc))
    try:
        parser = LightParser()
        ast = parser.parse(text)
        errs = getattr(parser, 'errors', None) or []
        if ast is None:
            return 'PARSE', brief(errs[0] if errs else 'parse 返回 None')
        if errs:
            return 'PARSE', brief(errs[0])
        return 'OK', ''
    except Exception as exc:                                # noqa: BLE001
        return 'PARSE', brief('%s: %s' % (type(exc).__name__, exc))


def load_baseline(path):
    try:
        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return None
    except Exception as exc:                                # noqa: BLE001
        raise RuntimeError('基线不可读 %s：%s' % (path, exc))


def main(argv=None):
    _utf8_stdout()
    ap = argparse.ArgumentParser(
        description='互举反跑：lightharness 全树 .light 的 light 编译器可解析性回归门',
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--roots', nargs='*', default=list(DEFAULT_ROOTS),
                    help='扫描根（相对 lightharness；默认 src stdlib examples tests）')
    ap.add_argument('--baseline', default=DEFAULT_BASELINE, help='基线 JSON 路径')
    ap.add_argument('--update-baseline', action='store_true',
                    help='把本次结果写为新基线（首次接入 / 收口刷基线）')
    ap.add_argument('--json', default='', help='输出 JSON 报告到该路径')
    ap.add_argument('--report', default='', help='输出文本报告到该路径')
    ap.add_argument('--detail', action='store_true', help='打印全部失败文件的错误摘要')
    ap.add_argument('--warn', action='store_true', help='只警告不阻断（退出码恒 0）')
    ap.add_argument('--quiet', action='store_true', help='只打印汇总')
    args = ap.parse_args(argv)

    baseline_path = args.baseline if os.path.isabs(args.baseline) \
        else os.path.join(ROOT, args.baseline)

    try:
        Lexer, LightParser, light_ver = load_compiler()
    except Exception as exc:                                # noqa: BLE001
        print('⚠️  编译器加载失败：%s' % exc)
        return 2

    files = collect(args.roots)
    if not files:
        print('⚠️  未收集到任何 .light 文件（roots=%s）' % ' '.join(args.roots))
        return 2

    rev = light_merge_rev()
    print('=' * 78)
    print('互举反跑：lightharness 全树 .light × light 编译器可解析性')
    print('=' * 78)
    print('编译器：light-merge %s（光明 v%s）   roots: %s'
          % (rev, light_ver, ' '.join(args.roots)))
    print('待检：%d 个 .light 文件' % len(files))

    t0 = time.time()
    results = {}          # relpath -> {'status':..., 'message':...}
    counts = {'OK': 0, 'LEX': 0, 'PARSE': 0, 'READ': 0}
    for path in files:
        rel = os.path.relpath(path, ROOT).replace('\\', '/')
        status, msg = check_one(path, Lexer, LightParser)
        counts[status] = counts.get(status, 0) + 1
        if status != 'OK':
            results[rel] = {'status': status, 'message': msg,
                            'digest': digest_of(msg)}
    elapsed = time.time() - t0

    print('耗时 %.1fs ｜ 可解析 %d ｜ 词法失败 %d ｜ 语法失败 %d ｜ 读取失败 %d'
          % (elapsed, counts['OK'], counts['LEX'], counts['PARSE'], counts['READ']))

    # ── 基线对比 ────────────────────────────────────────────────────────
    base = load_baseline(baseline_path)
    if base is None and not args.update_baseline:
        print('\n⚠️  找不到基线 %s。首次接入请执行：' % baseline_path)
        print('      python scripts/互举反跑.py --update-baseline')
        return 2
    base_files = (base or {}).get('failures', {}) or {}

    new_fail = sorted(set(results) - set(base_files))
    still_fail = sorted(set(results) & set(base_files))
    fixed = sorted(set(base_files) - set(results))
    changed = sorted(k for k in still_fail
                     if results[k].get('digest') and base_files[k].get('digest')
                     and results[k]['digest'] != base_files[k]['digest'])

    ok = not new_fail

    # ── 报告 ────────────────────────────────────────────────────────────
    lines = []
    lines.append('互举反跑报告  %s' % time.strftime('%Y-%m-%d %H:%M:%S'))
    lines.append('编译器：light-merge %s（光明 v%s）' % (rev, light_ver))
    lines.append('根目录：%s' % ' '.join(args.roots))
    lines.append('扫描 %d 个 .light；可解析 %d；失败 %d（词法 %d / 语法 %d / 读取 %d）；耗时 %.1fs'
                 % (len(files), counts['OK'], len(results), counts['LEX'],
                    counts['PARSE'], counts['READ'], elapsed))
    if base is not None:
        lines.append('基线：%s（%d 条，生成于 %s，标定编译器 %s）'
                     % (os.path.relpath(baseline_path, ROOT),
                        len(base_files), (base or {}).get('generated_at', '?'),
                        (base or {}).get('light_merge_rev', '?')))
        lines.append('对比：新增失败 %d ｜ 基线内仍失败 %d ｜ 已修复 %d ｜ 信息变化 %d'
                     % (len(new_fail), len(still_fail), len(fixed), len(changed)))
    else:
        lines.append('基线：本次生成（--update-baseline）')

    if new_fail:
        lines.append('')
        lines.append('【新增解析失败 %d 条 —— 视为互举回归】' % len(new_fail))
        for k in new_fail:
            lines.append('  ! %-52s [%s] %s' % (k, results[k]['status'], results[k]['message']))
    if changed:
        lines.append('')
        lines.append('【基线内但错误信息变化 %d 条（同文件、摘要不同，供关注）】' % len(changed))
        for k in changed:
            lines.append('  ~ %-52s [%s] %s' % (k, results[k]['status'], results[k]['message']))
    if fixed:
        lines.append('')
        lines.append('【已修复 %d 条（请刷新基线）】' % len(fixed))
        for k in fixed:
            lines.append('  + %s' % k)
    if args.detail and results:
        lines.append('')
        lines.append('【全部失败明细 %d 条】' % len(results))
        for k in sorted(results):
            lines.append('  - %-52s [%s] %s' % (k, results[k]['status'], results[k]['message']))

    text = '\n'.join(lines)
    if not args.quiet:
        print('\n' + text)
    else:
        print('\n' + '\n'.join(lines[:6]))
    if args.update_baseline:
        print('\n判据：本次为**基线生成**模式（未做对比）；已记录 %d 条失败为基线。' % len(results))
    else:
        print('\n判据：%s' % ('✅ 0 新增解析失败 —— 绿'
                             if ok else '❌ 新增解析失败 %d 条 —— %s'
                             % (len(new_fail), '仅警告（--warn）' if args.warn else '红（退出码 1）')))

    # ── 落盘 ────────────────────────────────────────────────────────────
    if args.update_baseline:
        payload = {'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                   'light_merge_rev': rev, 'light_version': light_ver,
                   'roots': list(args.roots),
                   'scanned': len(files), 'ok': counts['OK'],
                   'counts': counts, 'elapsed_sec': round(elapsed, 2),
                   'failures': {k: results[k] for k in sorted(results)}}
        os.makedirs(os.path.dirname(baseline_path), exist_ok=True)
        with open(baseline_path, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        print('✅ 已写入基线 %s（%d 条失败记录）'
              % (os.path.relpath(baseline_path, ROOT), len(results)))

    if args.json:
        out = args.json if os.path.isabs(args.json) else os.path.join(ROOT, args.json)
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        with open(out, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump({'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                       'light_merge_rev': rev, 'light_version': light_ver,
                       'roots': list(args.roots), 'scanned': len(files),
                       'counts': counts, 'elapsed_sec': round(elapsed, 2),
                       'failures': {k: results[k] for k in sorted(results)},
                       'new_failures': new_fail, 'fixed': fixed, 'changed': changed,
                       'ok': ok}, fh, ensure_ascii=False, indent=2)
        print('已输出 JSON：%s' % out)
    if args.report:
        out = args.report if os.path.isabs(args.report) else os.path.join(ROOT, args.report)
        os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
        with open(out, 'w', encoding='utf-8', newline='\n') as fh:
            fh.write(text + '\n')
        print('已输出文本报告：%s' % out)

    if args.update_baseline:
        return 0
    return 0 if (ok or args.warn) else 1


if __name__ == '__main__':
    sys.exit(main())

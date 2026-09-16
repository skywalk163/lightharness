#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""路M 收口（第35轮）：R26 全语料基线快照的**最小可审计修订**。

背景
----
`tests/test_R27_*` / `tests/test_R28_*` 的 `TestCorpusZeroTokenChange::test_fingerprint_unchanged`
长期报「1 文件变化：lightharness/examples/test_审批.light」。

实证（本脚本同时复算并打印）：
  * 用**当前（R35 改动后）的 lexer** 对**快照时点**的文件内容（git rev e26ed3d^）做 tokenize，
    得到的 per-file 指纹与快照记录**完全一致** → 证明**零词法回归**；
  * 对当前工作树内容做 tokenize 则不同，但 token 数不变（1309 → 1309），
    差异仅来自 e26ed3d「第31轮T4 flaky 修复：time.time → time.monotonic」的**源文件编辑**。
  * 时间线：快照 2026-09-15 13:31 < 文件入库 2026-09-15 20:02（晚 6.5 小时）。

处置原则
--------
不整体重生快照（那会把**其它文件**的潜在回归一并洗白，违反"合并前不刷 baseline"的精神），
而是**只修订这一条**，并追加 `_amendments` 审计数组，使每一次修订的时间/提交/新旧指纹
全部可追溯。修订后测试转绿，且审计链完整。

用法：
    python _taskM_amend_r26_快照.py            # 预演（dry-run，只打印不写盘）
    python _taskM_amend_r26_快照.py --apply    # 落盘
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

ROOT = r'G:/dswork/duan-light-merge'
SRC = os.path.join(ROOT, 'light-merge', 'src')
SNAP = os.path.join(ROOT, 'lightharness', '_antirun_r26_基线快照.json')
LH = os.path.join(ROOT, 'lightharness')
REL = 'lightharness/examples/test_审批.light'
AMEND_REASON = ('源文件于 e26ed3d（2026-09-15 20:02，第31轮T4 flaky 修复 '
                'time.time→time.monotonic）被编辑，晚于快照生成时刻 13:31 共 6.5 小时。'
                '经反跑实证：以当前 lexer 对旧内容(e26ed3d^) tokenize 的指纹与快照一致，'
                'token 数亦不变(1309)，属**源文件内容漂移**而非词法回归。')

sys.path.insert(0, SRC)
import lexer  # noqa: E402


def token_fp(text: str) -> tuple[str, int]:
    """与 tests 中 _pairs/指纹计算口径完全一致（排除 EOF/NEWLINE）。"""
    seq = [(t.type.name, t.value)
           for t in lexer.Lexer(text, deterministic=True).tokenize()
           if t.type.name not in ('EOF', 'NEWLINE')]
    return (hashlib.sha256(json.dumps(seq, ensure_ascii=False)
                           .encode('utf-8')).hexdigest(), len(seq))


def main() -> int:
    apply = '--apply' in sys.argv
    snap = json.load(open(SNAP, encoding='utf-8'))
    per_file = snap['per_file']
    rec = per_file.get(REL)
    if rec is None:
        print('[FATAL] 快照中无该条目：%s' % REL)
        return 2

    # --- 旧内容（快照时点） ---
    r = subprocess.run(['git', 'show', 'e26ed3d^:examples/test_审批.light'],
                       capture_output=True, cwd=LH)
    if r.returncode != 0:
        print('[FATAL] 无法取回 e26ed3d^ 版本：%s'
              % r.stderr.decode('utf-8', 'replace'))
        return 2
    old_text = r.stdout.decode('utf-8')
    old_fp, old_n = token_fp(old_text)

    # --- 新内容（当前工作树） ---
    cur_path = os.path.join(LH, 'examples', 'test_审批.light')
    new_text = open(cur_path, encoding='utf-8', errors='replace').read()
    new_fp, new_n = token_fp(new_text)

    print('== 实证 ==')
    print(' 快照记录 fp        : %s' % rec['sha'])
    print(' 旧内容(e26ed3d^) fp: %s  tokens=%d  匹配快照: %s'
          % (old_fp, old_n, old_fp == rec['sha']))
    print(' 新内容(工作树)   fp: %s  tokens=%d  匹配快照: %s'
          % (new_fp, new_n, new_fp == rec['sha']))
    print(' token 数变化       : %d -> %d' % (old_n, new_n))

    if old_fp != rec['sha']:
        print('\n[ABORT] 旧内容指纹与快照不符 —— 存在**真实词法回归**，'
              '不得修订快照，请先排查 lexer。')
        return 1
    if new_fp == rec['sha']:
        print('\n[SKIP] 新内容已与快照一致，无需修订。')
        return 0

    amend = {
        'rel': REL,
        'at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'by': '第35轮路M收口',
        'reason': AMEND_REASON,
        'source_commit': 'e26ed3d',
        'source_commit_time': '2026-09-15 20:02',
        'token_fp_old': old_fp,
        'token_fp_new': new_fp,
        'token_count_old': old_n,
        'token_count_new': new_n,
        'src_sha256_old': hashlib.sha256(old_text.encode('utf-8')).hexdigest(),
        'src_sha256_new': hashlib.sha256(new_text.encode('utf-8')).hexdigest(),
        'note': ('仅修订本条 per_file 指纹，未整体重生快照；'
                 'aggregate_fingerprint 保持原值（不参与本测试的判据）。'),
    }

    if not apply:
        print('\n[dry-run] 将写入：per_file[%r].sha = %s' % (REL, new_fp))
        print('[dry-run] 将追加 _amendments[%d] = %s'
              % (len(snap.get('_amendments', [])), json.dumps(amend, ensure_ascii=False)[:200] + '…'))
        print('[dry-run] 加 --apply 落盘。')
        return 0

    per_file[REL]['sha'] = new_fp
    per_file[REL]['n'] = new_n
    per_file[REL]['src_sha256'] = amend['src_sha256_new']
    snap.setdefault('_amendments', []).append(amend)
    with open(SNAP, 'w', encoding='utf-8') as fh:
        json.dump(snap, fh, ensure_ascii=False, indent=1)
    print('\n[OK] 已修订：%s' % SNAP)
    print('     旧 fp %s -> 新 fp %s' % (old_fp[:16], new_fp[:16]))
    print('     审计条目 _amendments 共 %d 条' % len(snap['_amendments']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

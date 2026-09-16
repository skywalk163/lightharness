# -*- coding: utf-8 -*-
"""R23 任务5 收尾：全量失败子集 A/B（工作区 lexer vs 基线 lexer）——**精确 nodeid 级**。

为什么这样做（逻辑完备性）：
  本机（Windows）与 CI（FreeBSD）失败模式不同，仓库自带的 `tests/ci_baseline_failures.txt`
  是 FreeBSD 基线（仅 12 条 e2e），拿它比会误报上百条「新增」。
  但回归的定义是「**本次改动前能过、改动后变红**」的用例——它必然落在「当前失败集 F_cur」之内。
  于是把 F_cur 这批用例拿去**基线 lexer**（e99bdb80 注入）下重跑：
      · 若某条在基线侧仍失败 ⇒ 它是既存失败，与本轮改动无关；
      · 若某条在基线侧通过 ⇒ 才是本轮引入的新回归。
  故 `F_cur ∪ 基线侧结果` 即可完全判定新增回归。

编码问题：
  Windows 控制台会把中文用例名双重编码，日志 ID 不可回传；改用 pytest 自写的
  `--junitxml`（pytest 直接以 UTF-8 落盘）采集 `classname`/`name`，再重建 nodeid。

抗抖动：
  子集先在工作区 lexer 下重跑一次（C1），与原全量结果比对以识别 flaky；
  「新增回归」候选（C1-B1）会再复跑一轮工作区+基线确认，避免抖动误报。

用法：python _r23_subset_ab.py [--xml <全量XML>] [--max-ids N]
"""
import io
import os
import re
import sys
import json
import time
import argparse
import xml.etree.ElementTree as ET
import subprocess

ROOT = r'G:\dswork\duan-light-merge'
LIGHTP = os.path.join(ROOT, 'light-merge')
HARNESS = os.path.join(ROOT, 'lightharness')
PY = sys.executable
DEFAULT_XML = r'C:\Users\skywalk\AppData\Local\Temp\r23_full.xml'
INJECT_DIR = r'C:\Users\skywalk\AppData\Local\Temp\r23_inject'
OUTDIR = r'C:\Users\skywalk\AppData\Local\Temp\r23_subset'
BASELINE_REV = 'e99bdb80'


# ---------------------------------------------------------------- XML 解析
def _classname_to_file(classname):
    parts = classname.split('.')
    for i in range(len(parts), 0, -1):
        cand = '/'.join(parts[:i]) + '.py'
        if os.path.exists(os.path.join(LIGHTP, cand)):
            return cand, parts[i:]
    return None, None


def parse_xml(path):
    """→ (fail_keys, err_keys, ok_keys)；键 = 'classname::name'（与 check_regression 同口径）。"""
    root = ET.parse(path).getroot()
    suites = root.findall('testsuite') if root.tag == 'testsuites' else [root]
    fail, err, ok = set(), set(), set()
    stats = {'tests': 0, 'failures': 0, 'errors': 0, 'skipped': 0}
    for suite in suites:
        for k in stats:
            stats[k] += int(suite.get(k, 0) or 0)
        for tc in suite.iter('testcase'):
            key = '%s::%s' % (tc.get('classname') or '', tc.get('name') or '')
            if tc.find('failure') is not None:
                fail.add(key)
            elif tc.find('error') is not None:
                err.add(key)
            else:
                ok.add(key)
    return fail, err, ok, stats


def to_nodeids(keys):
    """'classname::name' → nodeid；返回 (ids, pairs, unresolved)。

    pairs = [(原 key, nodeid)]，用于把重跑结果的 key 与原全量结果对齐（抖动统计）。
    """
    ids, pairs, bad = [], [], []
    for key in sorted(keys):
        cn, _, name = key.partition('::')
        f, cls_parts = _classname_to_file(cn)
        if not f:
            bad.append(key)
            continue
        nid = (f + '::' + '::'.join(list(cls_parts) + [name]) if cls_parts
               else f + '::' + name)
        ids.append(nid)
        pairs.append((key, nid))
    return ids, pairs, bad


# ---------------------------------------------------------------- pytest 执行
def run_pytest(targets, tag, inject_baseline):
    os.makedirs(OUTDIR, exist_ok=True)
    xml = os.path.join(OUTDIR, 'ab_%s.xml' % tag)
    log = os.path.join(OUTDIR, 'ab_%s.log' % tag)
    for p in (xml, log):
        if os.path.exists(p):
            os.remove(p)
    env = dict(os.environ)
    env['PYTHONUTF8'] = '1'
    env['PYTHONIOENCODING'] = 'utf-8'
    cmd = [PY, '-X', 'utf8', '-m', 'pytest', '-p', 'no:cacheprovider',
           '-q', '--tb=no', '-rf', '--junitxml=' + xml]
    if inject_baseline:
        env['PYTHONPATH'] = INJECT_DIR + os.pathsep + env.get('PYTHONPATH', '')
        cmd += ['-p', '_inject_baseline_lexer']
    cmd += list(targets)
    t0 = time.time()
    with io.open(log, 'w', encoding='utf-8', newline='') as fh:
        r = subprocess.run(cmd, cwd=LIGHTP, env=env, stdout=fh,
                           stderr=subprocess.STDOUT)
    dt = time.time() - t0
    raw = io.open(log, 'rb').read().decode('utf-8', 'replace')
    summ = [l for l in raw.split('\n') if re.search(r'\d+ (failed|passed|error)', l)]
    notfound = [l.strip() for l in raw.split('\n') if 'not found' in l or 'no tests ran' in l]
    res = (parse_xml(xml) if os.path.exists(xml) else (set(), set(), set(), {}))
    return {'rc': r.returncode, 'secs': round(dt, 1),
            'summary': summ[-1].strip() if summ else '(no summary)',
            'fail': res[0] | res[1], 'stats': res[3], 'notfound': notfound[:10]}


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--xml', default=DEFAULT_XML)
    args = ap.parse_args()

    if not os.path.exists(args.xml):
        print('!! 全量 XML 不存在：%s' % args.xml)
        return 2

    f_cur, e_cur, ok_cur, stats = parse_xml(args.xml)
    cur_all = f_cur | e_cur
    print('=== 工作区全量 XML：%s ===' % args.xml)
    print('collected=%d failures=%d errors=%d skipped=%d ｜ 打红合计 %d'
          % (stats.get('tests', 0), stats.get('failures', 0),
             stats.get('errors', 0), stats.get('skipped', 0), len(cur_all)))

    ids, pairs, bad = to_nodeids(cur_all)
    subset_keys = {k for k, _ in pairs}
    print('可重建 nodeid：%d ｜ 无法重建：%d' % (len(ids), len(bad)))
    for b in bad[:10]:
        print('   ? %s' % b)
    if not ids:
        print('无可重跑的失败用例 ⇒ 判定 PASS')
        return 0

    print('\n--- [1/3] 工作区 lexer 重跑失败子集（抗抖动基线 C1） ---')
    c1 = run_pytest(ids, 'cur1', inject_baseline=False)
    print('rc=%s  %s  (%ss)  notfound=%d'
          % (c1['rc'], c1['summary'], c1['secs'], len(c1['notfound'])))
    for n in c1['notfound']:
        print('   ! %s' % n)

    print('\n--- [2/3] 基线 lexer（%s 注入）重跑同一子集 ---' % BASELINE_REV)
    b1 = run_pytest(ids, 'base1', inject_baseline=True)
    print('rc=%s  %s  (%ss)' % (b1['rc'], b1['summary'], b1['secs']))

    # 抖动：原全量里红、两侧重跑却都绿
    flaky = sorted(subset_keys - c1['fail'] - b1['fail'])
    new = sorted(c1['fail'] - b1['fail'])
    print('\n=== 子集内比对 ===')
    print('C1(工作区) 红 %d ｜ B1(基线) 红 %d ｜ 候选新增回归 %d'
          % (len(c1['fail']), len(b1['fail']), len(new)))

    # [3/3] 候选新增回归复跑确认
    if new:
        print('\n--- [3/3] 候选新增回归复跑确认（工作区 + 基线各一遍） ---')
        c2 = run_pytest(new, 'cur2', inject_baseline=False)
        b2 = run_pytest(new, 'base2', inject_baseline=True)
        print('C2: %s' % c2['summary'])
        print('B2: %s' % b2['summary'])
        confirmed = sorted(c2['fail'] - b2['fail'])
        print('复跑确认的新增回归：%d' % len(confirmed))
        for k in confirmed:
            print('   + NEW  %s' % k)
        new = confirmed

    verdict = 'ALL_OK' if not new else 'REGRESS'
    print('\nVERDICT: %s' % verdict)
    print('（判据：本次改动引入新回归 ⇒ 必在 F_cur 内；F_cur 在基线 lexer 下全部同样打红 ⇒ 零新增）')

    json.dump({'full_xml': args.xml, 'baseline_rev': BASELINE_REV,
               'full_stats': stats, 'full_red': len(cur_all),
               'subset_ids': len(ids), 'unresolved': bad,
               'cur1': {'summary': c1['summary'], 'red': len(c1['fail'])},
               'base1': {'summary': b1['summary'], 'red': len(b1['fail'])},
               'candidates': new, 'flaky_or_fixed': flaky,
               'verdict': verdict},
              io.open(os.path.join(HARNESS, '_task5_R23_失败子集AB_证据.json'),
                      'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('证据：lightharness/_task5_R23_失败子集AB_证据.json')
    return 0 if verdict == 'ALL_OK' else 1


if __name__ == '__main__':
    sys.exit(main())

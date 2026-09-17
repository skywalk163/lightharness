# -*- coding: utf-8 -*-
"""L-172 形态模糊搜索（进程内，进度写日志文件，避免缓冲丢失）。"""
import itertools
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)
sys.path.insert(0, os.path.join(LM, 'cli'))

import cli.light as L  # noqa: E402

LOG = os.path.join(HERE, 'fuzz.log')
logf = open(LOG, 'w', encoding='utf-8')


def log(*a):
    logf.write(' '.join(str(x) for x in a) + '\n')
    logf.flush()


MOD = '''段落 校验正数 接收 值:
  如果 值 < 0: 抛出 "expected positive"
  返回 值
'''

IMPORTS = {
    '轻模块': '从 _l172mod2 导入 校验正数',
    'JSON': '从 JSON 导入 序列化JSON',
    '无': '',
}

CALL_FORMS = {
    '设丢弃': '设 丢弃 为 校验正数(值)',
    '打印内联': '打印(校验正数(值))',
    '裸调用': '校验正数(值)',
}

WRAP = {
    '裸段体': '{CALL}',
    '尝试捕获': '尝试:\n    {CALL}\n  捕获 抛了:\n    设 备忘 为 抛了.args[0]',
    '尝试仅': '尝试:\n    {CALL}',
    '如果包': '如果 值 >= 0:\n    {CALL}',
    '如果单行': '如果 值 >= 0: {CALL}',
}

SIG = {'带参': '接收 值', '带参标签': '接收 值, 标签', '无参': ''}
TAIL = {'自动入口': '', '显式主()': '\n主()\n'}
ORDER = ['helper_first', 'main_first']
NAME = {'探针': '探针', '校验': '校验抛正数', '辅助': '辅助'}


def build(imports_key, call_key, wrap_key, sig_key, tail_key, order_key, name_key):
    imp = IMPORTS[imports_key]
    sig_txt = (' ' + SIG[sig_key]) if SIG[sig_key] else ''
    body = WRAP[wrap_key].replace('{CALL}', CALL_FORMS[call_key])
    args = '(3)' if sig_key != '带参标签' else '(3, "L")'
    if sig_key == '无参':
        body = '设 值 为 3\n  ' + WRAP[wrap_key].replace('{CALL}', CALL_FORMS[call_key])
    helper = f'段落 {NAME[name_key]}{sig_txt}:\n  {body}\n'
    main = f'段落 主:\n  {NAME[name_key]}{args}\n  打印("MAIN-OK")\n'
    parts = [imp, helper, main] if order_key == 'helper_first' else [imp, main, helper]
    return '\n'.join(p for p in parts if p) + '\n' + TAIL[tail_key]


def main():
    with open(os.path.join(HERE, '_l172mod2.light'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(MOD)
    p = os.path.join(HERE, '_fuzz_tmp.light')
    silent = []
    total = 0
    t0 = time.time()
    for combo in itertools.product(IMPORTS, CALL_FORMS, WRAP, SIG, TAIL, ORDER, NAME):
        src = build(*combo)
        total += 1
        label = '/'.join(combo)
        log(f'[{total}] {label} t={time.time()-t0:.1f}s')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(src)
        try:
            out = L._run_src(src, p)
        except Exception:  # noqa: BLE001
            continue
        if 'MAIN-OK' not in (out or ''):
            silent.append((label, src, out))
            log(f'   >>> 静默! out={out!r}')
    log(f'=== 组合 {total} 组；静默 {len(silent)} 组；耗时 {time.time()-t0:.1f}s')
    for label, src, out in silent[:10]:
        log('=' * 60)
        log('### ' + label)
        for line in src.split('\n'):
            log('   |' + line)
    logf.close()


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""L-172 形态模糊搜索：组合多种「段落体按名调用被导入函数」的写法，
在**进程内**走 cli._run_src（与 `light run` 同路径），找「有 主 但无 MAIN-OK 输出」的形态。
"""
import itertools
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)
sys.path.insert(0, os.path.join(LM, 'cli'))

import cli.light as L  # noqa: E402

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
    '返回调用': '返回 校验正数(值)',
    '裸调用': '校验正数(值)',
    '双层赋值': '设 甲 为 校验正数(值)\n  设 乙 为 甲',
}

WRAP = {
    '裸段体': '{CALL}',
    '尝试捕获': '尝试:\n    {CALL}\n  捕获 抛了:\n    设 备忘 为 抛了.args[0]',
    '尝试仅': '尝试:\n    {CALL}',
    '如果包': '如果 值 >= 0:\n    {CALL}',
    '如果单行': '如果 值 >= 0: {CALL}',
}

SIG = {
    '带参': '接收 值',
    '带参标签': '接收 值, 标签',
    '无参': '',
}

TAIL = {'自动入口': '', '显式主()': '\n主()\n'}

ORDER = {'主最后': 'helper_first', '主最前': 'main_first'}

HELPER_NAME = {'探针': '探针', '校验': '校验抛正数', '辅助': '辅助'}


def build(imports_key, call_key, wrap_key, sig_key, tail_key, order_key, name_key):
    imp = IMPORTS[imports_key]
    sig = (' ' + SIG[sig_key]) if SIG[sig_key] else ''
    body = WRAP[wrap_key].replace('{CALL}', CALL_FORMS[call_key])
    args = '(3)' if not SIG[sig_key] else ('(3)' if sig_key == '带参' else '(3, "L")')
    helper = f'段落 {HELPER_NAME[name_key]}{(" " + SIG[sig_key]) if SIG[sig_key] else ""}:\n  {body}\n'
    if call_key == '返回调用' and sig_key == '无参':
        helper = f'段落 {HELPER_NAME[name_key]}:\n  设 值 为 3\n  {body}\n'
    main = f'段落 主:\n  {HELPER_NAME[name_key]}{args}\n  打印("MAIN-OK")\n'
    parts = [imp, helper, main] if order_key == 'helper_first' else [imp, main, helper]
    src = '\n'.join(p for p in parts if p)
    return src + '\n' + TAIL[tail_key]


def run_one(src, label):
    p = os.path.join(HERE, '_fuzz_tmp.light')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(src)
    try:
        out = L._run_src(src, p)
    except Exception as e:  # noqa: BLE001
        # 运行期异常不是「静默」症状，跳过
        return None
    return out


def main():
    with open(os.path.join(HERE, '_l172mod2.light'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(MOD)
    silent = []
    total = 0
    for combo in itertools.product(IMPORTS, CALL_FORMS, WRAP, SIG, TAIL, ORDER, HELPER_NAME):
        imports_key, call_key, wrap_key, sig_key, tail_key, order_key, name_key = combo
        if call_key == '返回调用' and wrap_key in ('尝试捕获', '尝试仅'):
            continue
        src = build(*combo)
        label = '/'.join(combo)
        total += 1
        try:
            out = run_one(src, label)
        except Exception:  # noqa: BLE001
            out = None
        if out is None:
            continue
        if 'MAIN-OK' not in out:
            silent.append((label, src, out))
    print(f'组合 {total} 组；静默（无 MAIN-OK 输出）{len(silent)} 组')
    for label, src, out in silent[:6]:
        print('=' * 70)
        print('### ' + label)
        print('  out=' + repr(out)[:120])
        print('  src:')
        for line in src.split('\n'):
            print('    |' + line)


if __name__ == '__main__':
    main()

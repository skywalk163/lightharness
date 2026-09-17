# -*- coding: utf-8 -*-
"""在真实 R52 ssh协议 用例上做「反向工作绕行」突变，再 dump/运行，观察是否复现 L-172。

突变文件写到 lightharness/examples/ 下（让 `从 ssh协议 导入` 能解析到 src/），
运行后请删除。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')
LH = r'G:\dswork\duan-light-merge\lightharness'
OUT = os.path.join(LH, 'examples')
SRC = os.path.join(OUT, 'test_R52_ssh协议.light')

base = open(SRC, encoding='utf-8').read()

MUTS = {}
MUTS['_l172mut_m1'] = base.replace(
    '段落 校验抛远程 接收 校验器, 值, 期望含, 标签:',
    '段落 校验抛远程 接收 值, 期望含, 标签:'
).replace('设 丢弃 为 校验器(值)', '设 丢弃 为 校验远程路径(值)')

MUTS['_l172mut_m2'] = base.replace(
    '    设 丢弃 为 校验器(值)',
    '    设 丢弃 为 校验远程路径(值)\n    设 丢弃乙 为 校验器(值)'
)

MUTS['_l172mut_m3'] = base.replace(
    '段落 主:',
    '段落 探针 接收 值, 标签:\n'
    '  设 捕获名 为 空\n'
    '  尝试:\n'
    '    设 丢弃 为 校验远程路径(值)\n'
    '    断言相等(假, 真, 标签 + "_应抛未抛")\n'
    '  捕获 抛了:\n'
    '    设 捕获名 为 "X"\n'
    '  断言相等(捕获名, "X", 标签)\n\n'
    '段落 主:'
).replace(
    '  断言相等(校验远程路径("/a/b"), "/a/b", "3a_合法")',
    '  断言相等(校验远程路径("/a/b"), "/a/b", "3a_合法")\n  探针("", "3x_探针")'
)


def run(name, text):
    p = os.path.join(OUT, name + '.light')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)
    print('=' * 72)
    print('### ' + name)
    d = subprocess.run([PY, os.path.join(HERE, 'dump.py'), p], cwd=LH,
                       capture_output=True, text=True, encoding='utf-8')
    for ln in (d.stdout or '').split('\n'):
        s = ln.strip()
        if s.startswith(('entry =', 'arity =', 'module_invokes_entry', '_entry_call',
                         '末尾是否含入口调用块')) or s.startswith('[4]') or s.startswith('[3]'):
            print('  ' + s)
    if d.stderr.strip():
        print('  dump-stderr: ' + d.stderr.strip().split('\n')[0][:150])
    r = subprocess.run([PY, os.path.join(LH, '运行.py'), p], cwd=LH,
                       capture_output=True, text=True, encoding='utf-8', timeout=300)
    out = [x for x in (r.stdout or '').strip().split('\n') if x.strip()]
    print(f'  rc={r.returncode}  stdout 行数={len(out)}  首行={out[0][:70] if out else "<无>"}')
    if r.stderr.strip():
        print('  stderr: ' + r.stderr.strip().split('\n')[0][:150])


if __name__ == '__main__':
    for n, t in MUTS.items():
        run(n, t)

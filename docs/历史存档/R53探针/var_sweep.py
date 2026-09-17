# -*- coding: utf-8 -*-
"""在 pre-fix 重构文件上做「空格/连写」变体扫描，找静默丢语句/静默阻断。"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')
LH = r'G:\dswork\duan-light-merge\lightharness'
PRE = os.path.join(LH, 'examples', '_l172pre_ssh协议.light')

base = open(PRE, encoding='utf-8').read()

VARIANTS = {
    'v0_原样': base,
    'v1_为后无空格': base.replace('设 丢弃 为 校验远程路径(值)', '设 丢弃 为校验远程路径(值)'),
    'v2_为前无空格': base.replace('设 丢弃 为 校验远程路径(值)', '设 丢弃为 校验远程路径(值)'),
    'v3_设后无空格': base.replace('设 丢弃 为 校验远程路径(值)', '设丢弃 为 校验远程路径(值)'),
    'v4_尝试连写': base.replace('  尝试:\n', '  尝试：\n'),
    'v5_丢弃改名': base.replace('丢弃', '结果占位'),
}


def main():
    for name, text in VARIANTS.items():
        p = os.path.join(LH, 'examples', '_l172var.light')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        d = subprocess.run([PY, os.path.join(HERE, 'dump.py'), p], cwd=LH,
                           capture_output=True, text=True, encoding='utf-8')
        info = {}
        for ln in (d.stdout or '').split('\n'):
            s = ln.strip()
            for k in ('entry =', 'arity =', 'module_invokes_entry', '末尾是否含入口调用块'):
                if s.startswith(k):
                    info[k] = s
        nmain = (d.stdout or '').count("name='主'")
        r = subprocess.run([PY, os.path.join(LH, '运行.py'), p], cwd=LH,
                           capture_output=True, text=True, encoding='utf-8', timeout=300)
        out = [x for x in (r.stdout or '').split('\n') if x.strip()]
        ok = '通过' in (r.stdout or '')
        print(f'{name:14s} rc={r.returncode} 输出行={len(out)} 通过={ok} 主段落数={nmain} '
              f'| {info.get("entry =", "")} {info.get("arity =", "")} '
              f'{info.get("末尾是否含入口调用块", "")}')
        if d.stderr.strip():
            print('    dump-err:', d.stderr.strip().split('\n')[0][:120])
        if r.stderr.strip():
            print('    run-err :', r.stderr.strip().split('\n')[0][:120])


if __name__ == '__main__':
    main()

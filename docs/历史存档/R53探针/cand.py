# -*- coding: utf-8 -*-
"""候选静默阻断形态（入口判定三闸门）逐个实测。"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')

CASES = {
    'A_主带形参': '段落 主 接收 参数:\n  打印("MAIN-OK")\n',
    'B_顶层导入主': '从 总入口 导入 主\n\n段落 主:\n  打印("MAIN-OK")\n',
    'C_条件内定义主': '如果 真:\n  段落 主:\n    打印("MAIN-OK")\n',
    'D_主带接收体内': '段落 主:\n  接收 参数\n  打印("MAIN-OK")\n',
    'E_入口名main': '段落 main 接收 参数:\n  打印("MAIN-OK")\n',
    'F_仅顶层引用主': '设 回调 为 主\n\n段落 主:\n  打印("MAIN-OK")\n',
    'G_基线': '段落 主:\n  打印("MAIN-OK")\n',
}


def main():
    p = os.path.join(HERE, '_cand.light')
    for name, text in CASES.items():
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        d = subprocess.run([PY, os.path.join(HERE, 'dump.py'), p], cwd=LM,
                           capture_output=True, text=True, encoding='utf-8')
        info = []
        for ln in (d.stdout or '').split('\n'):
            s = ln.strip()
            if s.startswith(('entry =', 'arity =', 'module_invokes_entry', '_entry_call',
                             '末尾是否含入口调用块')):
                info.append(s)
        r = subprocess.run([PY, '-m', 'cli.light', 'run', p], cwd=LM,
                           capture_output=True, text=True, encoding='utf-8', timeout=120)
        silent = r.returncode == 0 and 'MAIN-OK' not in (r.stdout or '')
        print(f'{name:16s} rc={r.returncode} MAIN-OK={"MAIN-OK" in (r.stdout or ""):5} '
              f'{"**静默**" if silent else ""}')
        print('      ', ' | '.join(info))


if __name__ == '__main__':
    main()

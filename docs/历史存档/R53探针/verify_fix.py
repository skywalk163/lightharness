# -*- coding: utf-8 -*-
"""L-172 修复的「红前/绿后」双向取证：
  1) 旧闸门口径（裸引用也算已启动入口）→ test_L172.light 应 rc=0 且**无任何输出**（复现）；
  2) 新闸门口径 → 两行哨兵输出（修复生效）；
  3) 入口带形参 → 编译期告警（不再是纯静默）。
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')
EXAMPLE = os.path.join(LM, 'examples', 'test_L172.light')

OLD_GATE = '''
import sys, os
sys.path.insert(0, r'{src}')
sys.path.insert(0, r'{lm}')
sys.path.insert(0, r'{lm}\\cli')
from code_generator import PythonCodeGenerator, Paragraph, ParagraphCall, Identifier


def old_module_invokes_entry(self, module, entry):
    """修复前的口径：裸引用（Identifier）也算「已启动入口」。"""
    name = entry.name
    for stmt in getattr(module, 'statements', None) or []:
        if stmt is entry or isinstance(stmt, Paragraph):
            continue
        if self._node_calls_name(stmt, name, calls_only=False):
            return True
    return False


PythonCodeGenerator._module_invokes_entry = old_module_invokes_entry

sys.argv = ['light', 'run', r'{example}']
from cli.light import main
main()
'''.format(src=os.path.join(LM, 'src'), lm=LM, example=EXAMPLE)

ARITY_CASE = '段落 主 接收 参数:\n  打印("MAIN-OK")\n'


def main():
    # 1) 旧闸门
    p = os.path.join(HERE, '_oldgate.py')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(OLD_GATE)
    r = subprocess.run([PY, p], cwd=LM,
                       capture_output=True, text=True, encoding='utf-8', timeout=180)
    out = [x for x in (r.stdout or '').split('\n') if x.strip()]
    print('[1] 旧闸门（修复前口径）:')
    print('    rc =', r.returncode, ' stdout 行数 =', len(out), ' →', out)
    print('    stderr =', repr((r.stderr or '').strip()[:120]))
    print('    → 复现判定:', '是（rc=0 且无输出=静默阻断）' if (r.returncode == 0 and not out) else '否')

    # 2) 新闸门（当前源码）
    r2 = subprocess.run([PY, '-m', 'cli.light', 'run', EXAMPLE], cwd=LM,
                        capture_output=True, text=True, encoding='utf-8', timeout=180)
    out2 = [x for x in (r2.stdout or '').split('\n') if x.strip()]
    print('[2] 新闸门（修复后）：')
    print('    rc =', r2.returncode, ' stdout =', out2)
    print('    → 修复生效判定:', '是' if (r2.returncode == 0 and 'L172_主已执行' in out2) else '否')

    # 3) 入口带形参 → 编译期告警
    ap = os.path.join(HERE, '_arity.light')
    with open(ap, 'w', encoding='utf-8', newline='\n') as f:
        f.write(ARITY_CASE)
    r3 = subprocess.run([PY, '-m', 'cli.light', 'run', ap], cwd=LM,
                        capture_output=True, text=True, encoding='utf-8', timeout=180)
    print('[3] 入口带形参：')
    print('    rc =', r3.returncode, ' stdout =', repr((r3.stdout or '').strip()))
    print('    stderr =', repr((r3.stderr or '').strip()[:200]))
    print('    → 不再静默判定:', '是' if 'L-172' in (r3.stderr or '') else '否')


if __name__ == '__main__':
    main()

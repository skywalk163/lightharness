# -*- coding: utf-8 -*-
"""对比任务1 修复态 vs 断裂态在 L152 用例上的 definitions 差异。"""
import os, sys, json, subprocess

ROOT = r'G:/dswork/duan-light-merge/lightharness'
LIGHTP = r'G:/dswork/duan-light-merge/light-merge'
LEX = LIGHTP + r'/src/lexer.py'
F = ROOT + '/examples/test_R21_L152嵌套段落形参.light'
HELPER = ROOT + '/_defs_dump_helper.py'

T1 = (b'if _preceded_ok and (_a >= _header_end', b'if (_a >= _header_end')

HELPER_SRC = (
    "# -*- coding: utf-8 -*-\n"
    "import sys, json\n"
    "sys.path.insert(0, r'%s/src')\n"
    "from lexer import Lexer\n"
    "src = open(r'%s', encoding='utf-8').read()\n"
    "defs = sorted(Lexer()._scan_user_definitions(src))\n"
    "open(r'%s', 'w', encoding='utf-8').write(json.dumps(defs, ensure_ascii=False))\n"
) % (LIGHTP, F, ROOT + '/_defs_tmp.json')

with open(HELPER, 'w', encoding='utf-8') as fh:
    fh.write(HELPER_SRC)


def dump():
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    p = subprocess.run([sys.executable, HELPER], capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    if p.returncode != 0:
        print('HELPER STDERR:', p.stderr)
    return json.load(open(ROOT + '/_defs_tmp.json', encoding='utf-8'))


fix = dump()
data = open(LEX, 'rb').read()
assert data.count(T1[0]) == 1, 'anchors=%d' % data.count(T1[0])
open(LEX, 'wb').write(data.replace(T1[0], T1[1]))
try:
    brk = dump()
finally:
    data = open(LEX, 'rb').read()
    open(LEX, 'wb').write(data.replace(T1[1], T1[0]))
    os.remove(HELPER)

print('FIX  =', fix)
print('BRK  =', brk)
print('FIX-BRK =', sorted(set(fix) - set(brk)))
print('BRK-FIX =', sorted(set(brk) - set(fix)))

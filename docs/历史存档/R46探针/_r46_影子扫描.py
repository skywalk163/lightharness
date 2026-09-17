# R46 探针：全语料 L-166 影子变量扫描（ROOT 固定到两仓，不依赖脚本位置）
import os, sys, glob, io, json

BASE = r'G:\dswork\duan-light-merge'
LM = os.path.join(BASE, 'light-merge')
LH = os.path.join(LM.replace('light-merge', 'lightharness'))
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)

from light_parser_v3 import LightParser  # noqa: E402
from scope_shadow_check import check_global_shadow  # noqa: E402

targets = []
# lightharness: examples + src
for sub in ('examples', 'src', 'stdlib'):
    d = os.path.join(BASE, 'lightharness', sub)
    targets.extend(sorted(glob.glob(os.path.join(d, '*.light'))))
# light-merge: examples（含一层子目录）
_LM_EX = os.path.join(LM, 'examples')
targets.extend(sorted(glob.glob(os.path.join(_LM_EX, '*.light'))))
for sub in sorted(glob.glob(os.path.join(_LM_EX, '*'))):
    if os.path.isdir(sub):
        targets.extend(sorted(glob.glob(os.path.join(sub, '*.light'))))
        for sub2 in sorted(glob.glob(os.path.join(sub, '*'))):
            if os.path.isdir(sub2):
                targets.extend(sorted(glob.glob(os.path.join(sub2, '*.light'))))

rows = []
parse_err = 0
for f in targets:
    try:
        src = io.open(f, encoding='utf-8').read()
    except Exception:
        continue
    try:
        mod = LightParser().parse(src, filename=os.path.basename(f))
    except Exception:
        parse_err += 1
        continue
    try:
        ws = check_global_shadow(mod, os.path.basename(f), source=src)
    except Exception:
        continue
    for w in ws:
        rows.append({'file': os.path.relpath(f, BASE), 'warn': w})

by_file = {}
for r in rows:
    by_file.setdefault(r['file'], []).append(r['warn'])

print(f'扫描文件数={len(targets)} 解析失败={parse_err} 命中文件={len(by_file)} 命中条数={len(rows)}')
print('')
for f in sorted(by_file):
    print(f'## {f}  ({len(by_file[f])} 条)')
    for w in by_file[f]:
        print('   ' + w.replace('⚠ 编译警告（L-166 影子变量）：', ''))

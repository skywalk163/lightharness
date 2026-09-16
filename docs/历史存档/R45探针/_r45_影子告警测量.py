# R45 探针：测量「影子变量告警」在全语料上的命中率与噪声
import os, sys, glob, io

ROOT = os.path.dirname(os.path.abspath(__file__))
LM = os.environ.get('LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)

from light_parser_v3 import LightParser  # noqa: E402
from scope_shadow_check import check_global_shadow  # noqa: E402

targets = []
for pat in (os.path.join(ROOT, 'examples', '*.light'),
            os.path.join(ROOT, 'src', '*.light')):
    targets.extend(sorted(glob.glob(pat)))
# 顺带扫 light-merge 语料（语言本体自带例子），用于「跨仓清单审定」
_LM_EX = os.path.join(os.path.dirname(ROOT), 'light-merge', 'examples')
if os.path.isdir(_LM_EX):
    targets.extend(sorted(glob.glob(os.path.join(_LM_EX, '*.light'))))
    # 子目录例子也扫一层
    for sub in sorted(glob.glob(os.path.join(_LM_EX, '*'))):
        if os.path.isdir(sub):
            targets.extend(sorted(glob.glob(os.path.join(sub, '*.light'))))

total = 0
hit_files = 0
n_warn = 0
samples = []
parse_err = 0
for f in targets:
    try:
        src = io.open(f, encoding='utf-8').read()
    except Exception:
        continue
    total += 1
    try:
        mod = LightParser().parse(src, filename=os.path.basename(f))
    except Exception:
        parse_err += 1
        continue
    try:
        ws = check_global_shadow(mod, os.path.basename(f))
    except Exception as e:
        samples.append(f'[检查异常] {os.path.basename(f)}: {type(e).__name__}: {e}')
        n_warn += 1
        hit_files += 1
        continue
    if ws:
        hit_files += 1
        n_warn += len(ws)
        for w in ws:
            samples.append(w)

print(f'扫描文件 = {total}，解析失败 = {parse_err}')
print(f'命中文件 = {hit_files}，告警总数 = {n_warn}')
print('---- 前 40 条 ----')
for s in samples[:40]:
    print(s)

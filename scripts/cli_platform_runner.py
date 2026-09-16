#!/usr/bin/env python3
"""ASCII helper for legacy Windows PowerShell 5.1 and POSIX CLI checks."""
from pathlib import Path
import os, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
def find(pattern, markers):
    for p in sorted(ROOT.glob(pattern)):
        try: text = p.read_text(encoding='utf-8-sig')
        except Exception: continue
        if all(x in text for x in markers): return p
    raise RuntimeError('entry not found')
runner = find('*.py', ['from cli.light import main'])
entry = find('examples/*.light', ['从 总入口 导入 主', '主()'])
test = find('examples/test_*CLI*.light', ['test_CLI命令面', '主()'])
mode = sys.argv[1] if len(sys.argv) > 1 else 'entry'
target = test if mode == 'test' else entry
raise SystemExit(subprocess.run([sys.executable, str(runner), str(target)], cwd=ROOT, env=os.environ).returncode)

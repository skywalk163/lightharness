# -*- coding: utf-8 -*-
"""R59 任务4 归因取证：12 条目标在当前工作树（任务1-3 已改）上的实际状态。"""
import subprocess, sys, os
from pathlib import Path

LM = Path(r'G:\dswork\duan-light-merge\light-merge')
PY = r'G:\dswork\duan-light-merge\light-merge\.venv\Scripts\python.exe'
os.chdir(LM)
env = dict(os.environ, PYTHONIOENCODING='utf-8')

targets = [
    ('异步5', 'tests/test_frontend_blockers_run.py -k 异步修饰符'),
    ('旧式语法2', 'tests/_test_null_safety.py::TestBackwardsCompatibility::test_paragraph_call tests/_test_null_safety.py::TestNullSafetyFunctionCall::test_func_non_nullable_param_with_nullable_arg'),
    ('compact', 'tests/unit/test_parser.py::TestParser::test_compact_binary_expr_with_call'),
    ('R13B', 'tests/unit/test_原生腿_R13B_能力扩展.py::Test行政区划扩展::test_O0_行政区划代码_对拍与扩展'),
    ('R13C', 'tests/unit/test_原生腿_R13C_对拍扩展.py::test_URL编码解码'),
    ('地板搬迁', 'tests/unit/test_地板搬迁_列表_S2.py::test_十个段落全部导出且两版都可调用'),
    ('examples聚合', 'tests/unit/test_examples_run.py::TestExampleFilesRun::test_all_examples_output'),
]
for tag, spec in targets:
    cmd = [PY, '-m', 'pytest', *spec.split(), '-q', '--tb=line', '-p', 'no:xdist', '-o', 'addopts=', '-p', 'no:cacheprovider']
    r = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=600)
    out = (r.stdout + r.stderr)
    # 取失败名 + 摘要行
    lines = [l for l in out.splitlines() if l.strip()]
    tail = '\n'.join(lines[-14:])
    print(f'===== [{tag}] rc={r.returncode} =====')
    print(tail[:1600])
    print()

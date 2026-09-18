# -*- coding: utf-8 -*-
"""R61 收口：0.82 定向复跑 2 个疑似环境性红（ffi / lightpub httpbin）。"""
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(r'G:\dswork\duan-light-merge\lightharness\scripts')
spec = importlib.util.spec_from_file_location('sync082', SCRIPTS / '同步0.82.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cli = mod.connect()
mod.ensure_shim(cli)
rd = mod.load_remote_dir()
print('远端副本', rd)

PY = '/usr/local/bin/python3.12'
cases = [
    ('ffi', f"cd {rd}/light-merge && {PY} -m pytest tests/test_ffi_phase2.py::test_ffi_full_workflow -q --tb=short -o addopts=''"),
    ('lightpub', f"cd {rd}/light-merge && {PY} -m pytest tests/test_lightpub_bridge.py -q --tb=short -o addopts='' -k 获取JSON"),
]
for tag, cmd in cases:
    print(f'\n=== {tag} ===')
    rc, out = mod.run_remote(cli, cmd, timeout=600, quiet=False)
    print(f'rc={rc}')
    tail = out.strip().splitlines()[-8:]
    for ln in tail:
        print('  |', ln)

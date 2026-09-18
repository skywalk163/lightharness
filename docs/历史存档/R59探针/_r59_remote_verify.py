# -*- coding: utf-8 -*-
"""R59 0.82 定向验证：最新副本（173534）跑 5 个关键测试（非全量）。"""
import importlib.util, os, sys
from pathlib import Path

ROOT = Path(r'G:\dswork\duan-light-merge\lightharness')
spec = importlib.util.spec_from_file_location("sync082", ROOT / 'scripts' / '同步0.82.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cli = mod.connect()
try:
    cli.get_transport().set_keepalive(30)
    remote = '/tmp/r44-20260918-173534/light-merge'
    cmd = (
        f'cd {remote} && PYTHONIOENCODING=utf-8 /usr/local/bin/python3.12 -m pytest '
        '"tests/unit/test_原生腿_T6C_向量复数颜色参数编码.py::test_O0_参数解析_选项默认类型_对拍" '
        '"tests/unit/test_原生腿_T6C_向量复数颜色参数编码.py::test_O0_编码解码_URL_对拍" '
        '"tests/test_R40_语言支撑配套.py::Test现状钉桩_既有词法回归::test_现状钉桩_R19_为字整串合并" '
        '"tests/unit/test_原生腿_R13B_能力扩展.py::Test行政区划扩展::test_O0_行政区划代码_对拍与扩展" '
        '"tests/unit/test_原生腿_R13C_对拍扩展.py::test_URL编码解码" '
        '-q --tb=short -p no:cacheprovider 2>&1 | tail -8'
    )
    rc, out = mod.run_remote(cli, cmd, timeout=600, quiet=False)
    print('[0.82 定向] rc=%s' % rc)
finally:
    cli.close()

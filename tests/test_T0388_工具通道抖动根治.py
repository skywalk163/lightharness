# -*- coding: utf-8 -*-
"""T-0388「工具通道持续抖动」根治专项的 pytest 门禁包装。

真正的判据在 examples/test_T0388_工具通道抖动根治.light（三层全覆盖 + 反跑已验证）：
  §1 参数名别名归一   src/工具.light:归一参数 / 候选规范键
  §2 校验明细回传     src/工具.light:格式化校验错误 / 工具注册表.执行
  §3 连续失败熔断     src/代理.light:记参数失败 / 参数熔断门限

本文件只负责把它接进 `python -m pytest tests/` 全量门禁：子进程跑 .light，
断言 rc=0 且打印专属通过标记（防 .light 内部断言被删空导致假绿）。
与 test_R45_L166影子变量告警.py 同道：BASE=项目根，subprocess 继承环境
（LIGHT_MERGE 由 tests/conftest.py 写入），cwd=项目根。
"""
import os
import subprocess
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIGHT_SCRIPT = os.path.join(BASE, 'examples', 'test_T0388_工具通道抖动根治.light')
PASS_MARK = 'test_T0388_工具通道抖动根治 全部通过'


def _run():
    return subprocess.run(
        [sys.executable, os.path.join(BASE, '运行.py'), LIGHT_SCRIPT],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=120, cwd=BASE, env=dict(os.environ),
    )


def test_T0388_工具通道抖动根治():
    p = _run()
    assert p.returncode == 0, (
        f"T-0388 专项 .light 应绿，实际 rc={p.returncode}\n"
        f"--- stdout ---\n{p.stdout[-1500:]}\n--- stderr ---\n{p.stderr[-1500:]}"
    )
    assert PASS_MARK in p.stdout, (
        f"缺少通过标记，疑似用例被清空或提前退出（假绿）\n--- stdout ---\n{p.stdout}"
    )

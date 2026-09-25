# -*- coding: utf-8 -*-
"""test_support 基建 smoke test。

不针对具体业务模块，只验证：
  1. run_light_source 能跑通最小 .light 片段；
  2. assert_success / out_contains 断言链工作；
  3. 能 import src/ 下的模块（验证导入路径）。
"""
from test_support import (
    run_light_source, assert_success, out_contains, out_not_contains,
)


def test_smoke_basic():
    """最小片段：打印一句话，断言 rc=0 且 stdout 含该句。"""
    r = run_light_source('''
段落 主程序:
  打印("LH_SMOKE_OK")
''')
    assert_success(r)
    out_contains(r, "LH_SMOKE_OK")


def test_smoke_import_src_module():
    """能 import src/ 下的模块并调用其导出。

    选「字典增强」——纯函数，无 IO 副作用，参数简单。
    """
    r = run_light_source('''
从 字典增强 导入 字典获取, 字典合并
段落 主程序:
  设 a 为 {"x": 1}
  设 b 为 {"y": 2}
  设 c 为 字典合并(a, b)
  设 v 为 字典获取(c, "x")
  打印("MERGED=" + 转字符串(v))
''')
    assert_success(r)
    out_contains(r, "MERGED=1")


def test_smoke_failure_detection():
    """反向：应报错的片段被识别为 rc!=0。"""
    r = run_light_source('''
段落 主程序:
  设 x 为 1 除以 0
  打印(x)
''', timeout=30)
    # 零除应非零退出（不强行断言具体错误文案，只确认基建能看到失败）
    assert r.rc != 0, f"零除应 rc!=0，实际 rc=0\n{r.output}"

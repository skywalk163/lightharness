# -*- coding: utf-8 -*-
"""tests/conftest.py —— 测试环境的统一入口（只做路径探测，不改任何用例语义）。

为什么需要这个文件
------------------
本仓有 13 个词法/回归测试文件各自写了同一段：

    LIGHT_MERGE = os.environ.get("LIGHT_MERGE", r"G:\\dswork\\duan-light-merge\\light-merge")
    sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))

那串默认值是**原开发机的 Windows 路径**。换台机器（Linux / CI / 别人的 Mac）只要
没有显式 `export LIGHT_MERGE`，这些文件在**收集期**就 `ModuleNotFoundError: No module
named 'lexer'` —— 21 个测试模块集体 ERROR，看着像代码坏了，其实只是路径不属于这台机器。

修法选择：不改那 13 个文件（它们写法本身没错，只是默认值不该写死），而是在收集之前
把探测结果写回 `os.environ`，让它们原样读到正确值；同时把 `<编译器根>/src` 前置进
`sys.path`，供需要直接 `import lexer` / `light_parser_v3` 的用例使用。

探测口径与 `运行.py::_find_light_merge` 一致 —— **改一处要同步另一处**。
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _find_light_merge():
    """定位光明编译器仓（判定标准：目录下有 src/）。显式 $LIGHT_MERGE 永远最优先。"""
    候选 = []
    显式 = os.environ.get("LIGHT_MERGE")
    if 显式:
        候选.append(显式)
    候选 += [
        os.path.join(_ROOT, "..", "light"),                   # dswork/{light,lightharness}
        os.path.join(_ROOT, "..", "light-merge"),
        os.path.join(_ROOT, "..", "duan-light-merge", "light-merge"),
        os.path.join(_ROOT, "..", "..", "light"),
        r"G:\dswork\duan-light-merge\light-merge",            # 原 Windows 开发机，兜底
    ]
    for c in 候选:
        if os.path.isdir(os.path.join(c, "src")):
            return os.path.normpath(c)
    return None


_LM = _find_light_merge()

if _LM:
    # 写回环境：那 13 个文件的 os.environ.get("LIGHT_MERGE", ...) 与子进程都会拿到正确值
    os.environ["LIGHT_MERGE"] = _LM
    _SRC = os.path.join(_LM, "src")
    if _SRC not in sys.path:
        sys.path.insert(0, _SRC)
else:
    # 一个都不中：保持沉默，让用例自己报「找不到光明编译器」，比在这里 sys.exit 好排查
    pass

# -*- coding: utf-8 -*-
"""_动态加载.py —— 按文件路径编译加载任意 .light 模块（R111 第二版）。

用途
----
光语静态 `导入 <名>` 走 sys.meta_path 裸名查找，宿主 src/ 在搜索路径前列，
与 lightplugin 插件同名的模块会命中宿主版（无 .挂载 段），挂不上插件。

本模块绕开裸名查找：直接调 _light_import_hook._compile_light 把指定路径的
.light 编译成 Python 源码，exec 到一个全新 module 命名空间，返回模块对象。
拿到对象后光语侧即可调 `模块.挂载(注册表)`，与静态 import 等价但不撞名。

典型用法（光语）::

    从 _动态加载 导入 加载为模块
    设 模块 为 加载为模块(".../lightplugin/插件/代理团队/代理团队.light")
    模块.挂载(注册表)
"""
from __future__ import annotations

import os
import sys
import types

from _light_import_hook import _compile_light

# src/ 的上一级是 lightharness/，stdlib 地板在 lightharness/stdlib（含 builtins.py）
_HERE = os.path.dirname(os.path.abspath(__file__))
_STDLIB_FLOOR = os.path.normpath(os.path.join(_HERE, "..", "stdlib"))


def _ensure_compiler():
    """兜底把 light-merge/src（含 light_parser_v3 / code_generator）加进 sys.path。

    正常宿主入口（运行.py）已配置；此处只保证本模块被独立调用时也能编译。
    """
    try:
        from light_parser_v3 import LightParser  # noqa: F401
        return
    except ImportError:
        pass
    candidates = [
        os.path.normpath(os.path.join(_HERE, "..", "..", "light-merge", "src")),
        os.path.normpath(os.path.join(_HERE, "..", "..", "light-merge", "antlrparser")),
    ]
    for c in candidates:
        if os.path.isdir(c) and c not in sys.path:
            sys.path.insert(0, c)


def 加载为模块(light_path: str) -> types.ModuleType:
    """编译指定 .light 文件并返回模块对象（不注册进 sys.modules）。

    调用方拿到后可直接调其顶层段落（如 .挂载(注册表)）。
    """
    if not os.path.isfile(light_path):
        raise FileNotFoundError("找不到 .light 文件: " + light_path)
    _ensure_compiler()
    code = _compile_light(light_path, _STDLIB_FLOOR)
    mod_name = os.path.splitext(os.path.basename(light_path))[0]
    mod = types.ModuleType(mod_name)
    mod.__file__ = light_path
    mod.__light_source__ = light_path
    exec(compile(code, light_path, "exec"), mod.__dict__)
    # 注册进 sys.modules：让插件内部 `从 <兄弟插件> 导入 ...` 命中插件版，
    # 而不是宿主 src/ 的同名残骸（否则撞车链如下游团队界面会断）。
    sys.modules[mod_name] = mod
    return mod


def 插件文件路径(插件根: str, 插件名: str) -> str:
    """拼出 <插件根>/<插件名>/<插件名>.light 的绝对路径。"""
    return os.path.join(插件根, 插件名, 插件名 + ".light")

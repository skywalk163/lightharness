# -*- coding: utf-8 -*-
"""
lightharness 运行器
====================
在 lightharness 项目内用「光明」编译器编译并运行 .light 程序。
lightharness 自带一份自包含 stdlib（本目录下 stdlib/），不依赖 light-merge 的 stdlib。

用法:
    python 运行.py src/主程序.light [参数...]
    python 运行.py examples/hello.light

原理:
    光明生成的 Python 代码自带 stdlib 引导（_light_stdlib 搜索），依次查找:
      <脚本目录>/stdlib  →  <脚本目录>/../stdlib  →  cwd/stdlib  →  <脚本目录>/../../stdlib
    lightharness 把 stdlib 放在项目根，.light 源码放在 src/，因此
    `python 运行.py src/xxx.light` 时脚本目录是 src/，其上级就是项目根，
    引导会命中 lightharness/stdlib —— 自包含成立。
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
STDLIB = os.path.join(ROOT, 'stdlib')
SRC = os.path.join(ROOT, 'src')

# 第2步：lightplugin 生产接线根路径（默认取兄弟目录，可用 LIGHTPLUGIN 覆盖）
LIGHTPLUGIN = os.environ.get('LIGHTPLUGIN', os.path.normpath(os.path.join(ROOT, '..', 'lightplugin')))


def _lightplugin_paths():
    """第2步：lightplugin 路径表（仓根 + 集成/ + 插件/ + 各插件一级目录）。

    照抄 lightplugin/运行.py:38-47 的 _plugin_search_dirs：每个插件的一级目录都要
    入搜索路径，否则插件之间无法互导（例：图片生成 要 `从 异步作业轮询 导入 提交作业`）。
    lightplugin 不存在时返回空表（未接线的环境照旧只挂核心工具，不报错）。
    """
    dirs = []
    if not os.path.isdir(LIGHTPLUGIN):
        return dirs
    dirs.append(LIGHTPLUGIN)
    jicheng = os.path.join(LIGHTPLUGIN, '集成')
    if os.path.isdir(jicheng):
        dirs.append(jicheng)
    plugins_dir = os.path.join(LIGHTPLUGIN, '插件')
    if os.path.isdir(plugins_dir):
        dirs.append(plugins_dir)
        for name in sorted(os.listdir(plugins_dir)):
            p = os.path.join(plugins_dir, name)
            if os.path.isdir(p) and not name.startswith(('_', '.')):
                dirs.append(p)
    return dirs

# 光明编译器来自 light-merge 仓库（语言本体），可用环境变量 LIGHT_MERGE 覆盖
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
if not os.path.isdir(os.path.join(LIGHT_MERGE, 'src')):
    print(f'错误: 找不到光明编译器（LIGHT_MERGE={LIGHT_MERGE}）')
    sys.exit(1)


def _setup_paths():
    """把 lightharness 自包含 stdlib 与 light-merge 编译器放入 sys.path。

    R100 路 B 修复：**lightharness 自身路径必须排在 light-merge 之前**。
    原实现 insert(0) 循环顺序使 LIGHT_MERGE 仓根反而位于 sys.path 前部，
    生成代码引导 `import stdlib.FFI` 时 `stdlib` 常规包先命中
    light-merge/stdlib（而非本仓 stdlib），其 builtins.py 顶层又把
    light-merge/stdlib install 进导入钩子搜索路径——随后
    `从 字符串工具 导入 …` 被钩子解析到 light-merge/stdlib/字符串工具.light
    （纯光明版），其 `从 re 导入 re_花括号` 生成 `from _light_re import …`
    别名导入，宿主运行期解析不到 → lightharness examples 恒红。
    宿主运行期永远不该吃到兄弟仓的 .light stdlib，故本仓路径置前。
    """
    # 先放 light-merge（编译器），再放 lightharness 自身——最终 sys.path 前部
    # 是 lightharness 的 SRC / ROOT / STDLIB，`import stdlib` 命中本仓 stdlib 包。
    for p in [os.path.join(LIGHT_MERGE, 'src'),
              os.path.join(LIGHT_MERGE, 'antlrparser'),
              LIGHT_MERGE,
              SRC, ROOT, STDLIB]:
        if p not in sys.path:
            sys.path.insert(0, p)
    # 第2步：lightplugin 生产接线 —— 插件路径**追加**在宿主路径之后（不遮蔽本仓
    # stdlib，保住 R100 修复的宿主优先序），照抄 lightplugin/运行.py:50-60 的 sys.path 段
    for p in _lightplugin_paths():
        if p not in sys.path:
            sys.path.append(p)
    # 安装「纯光明模块」导入钩子：让 .light 模块在运行时被找到
    try:
        import _light_import_hook
        # 第2步：宿主路径在前（保住 _stdlib_dir 取 search_paths[0] 的既有语义），
        # lightplugin 路径追加在后；install 重复调用安全（extend 追加，见钩子 :229-234）
        _light_import_hook.install([SRC, STDLIB, ROOT] + _lightplugin_paths())
    except Exception as exc:  # noqa: BLE001 - 钩子失败不致命，.py 版 stdlib 仍可用
        print(f'警告: 纯光明导入钩子安装失败: {exc}')


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0
    # 第45轮：把「当前解释器的绝对路径」注入环境，供 .light 用例里再 spawn
    # 子解释器时使用（HARNESS_PY）。此前用例一律写死 `python`，依赖 PATH 上
    # 恰好有这个名字：Windows 上可能是应用商店别名或压根没有，FreeBSD 上只有
    # python3——全量回归里 test_子进程后台 偶发红就有这条成因。
    os.environ.setdefault('HARNESS_PY', sys.executable)
    _setup_paths()
    entry = argv[1]
    if not os.path.isabs(entry):
        entry = os.path.join(ROOT, entry)
    if not os.path.isfile(entry):
        print(f'错误: 找不到入口文件 {entry}')
        return 1
    # 委托给光明 CLI（run 子命令）
    from cli.light import main as light_main
    # R100 路 B：cli.light 模块被 import 时会把 light-merge 的仓根/src/antlrparser
    # 重新插到 sys.path 最前（cli/light.py:34-36）。而生成的代码引导对 stdlib 路径
    # 用的是「已存在则不重复插」守卫——宿主 stdlib 已在 sys.path 里（只是不在最前）
    # 时 insert(0) 变 no-op，随后 `import stdlib.FFI` 命中 light-merge/stdlib 包，
    # 其 builtins.py 顶层再把 light-merge/stdlib install 进导入钩子搜索路径，
    # 宿主运行期就开始吃到兄弟仓的 .light stdlib（uuid工具/字符串工具 等）。
    # 这里在 CLI 导入之后重申宿主路径优先，保证 `import stdlib` 命中本仓 stdlib 包。
    for _p in (STDLIB, ROOT, SRC):
        while _p in sys.path:
            sys.path.remove(_p)
        sys.path.insert(0, _p)
    # R98/D 修复：显式传入 lightharness 自带 stdlib，使地板 builtins.py 稳定加载
    # （转字符串 等内置走英文 str 口径），不再依赖 cwd 探测 —— 从任意目录（含
    # pytest 子进程 cwd=临时目录）运行都不会回退到中文兜底 lambda。
    argv = ['light', 'run', '--stdlib-dir', STDLIB, entry] + argv[2:]
    sys.argv = argv
    return light_main()


if __name__ == '__main__':
    sys.exit(main())

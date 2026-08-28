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

# 光明编译器来自 light-merge 仓库（语言本体），可用环境变量 LIGHT_MERGE 覆盖
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
if not os.path.isdir(os.path.join(LIGHT_MERGE, 'src')):
    print(f'错误: 找不到光明编译器（LIGHT_MERGE={LIGHT_MERGE}）')
    sys.exit(1)


def _setup_paths():
    """把 lightharness 自包含 stdlib 与 light-merge 编译器放入 sys.path。"""
    for p in [STDLIB, ROOT, SRC,
              os.path.join(LIGHT_MERGE, 'src'),
              os.path.join(LIGHT_MERGE, 'antlrparser'),
              LIGHT_MERGE]:
        if p not in sys.path:
            sys.path.insert(0, p)
    # 安装「纯光明模块」导入钩子：让 .light 模块在运行时被找到
    try:
        import _light_import_hook
        _light_import_hook.install([SRC, STDLIB, ROOT])
    except Exception as exc:  # noqa: BLE001 - 钩子失败不致命，.py 版 stdlib 仍可用
        print(f'警告: 纯光明导入钩子安装失败: {exc}')


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    if len(argv) < 2 or argv[1] in ('-h', '--help'):
        print(__doc__)
        return 0
    _setup_paths()
    entry = argv[1]
    if not os.path.isabs(entry):
        entry = os.path.join(ROOT, entry)
    if not os.path.isfile(entry):
        print(f'错误: 找不到入口文件 {entry}')
        return 1
    # 委托给光明 CLI（run 子命令）
    from cli.light import main as light_main
    argv = ['light', 'run', entry] + argv[2:]
    sys.argv = argv
    return light_main()


if __name__ == '__main__':
    sys.exit(main())

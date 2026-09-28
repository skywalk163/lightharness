# lightharness Nuitka 独立 EXE 打包成功

## 最终成果

**lightharness.exe**（8.2MB）— 客户无需装 Python，双击即可运行。

## 解决的问题链

| 问题 | 解决方案 |
|------|----------|
| Nuitka GBK 编码读中文模块名乱码 | 维护 `module_map.json` 中文→英文映射表 |
| 纯导出模块（.light 只有 `导出` 声明）无函数体 | 复制 stdlib/*.py 实现文件到 build_py/ |
| fallback 分支缺 `环境变量` 等内置函数 | 批量补丁 240 个文件，改 import light_builtins |
| `signal.py` 覆盖 Python 标准库 | 重命名为 `light_signal.py` |
| 编译器模块 `light_parser_v3` 未打包 | 复制 light-merge/src/*.py 到 build_py/ |

## 编译流程

```bash
# 1. 编译 .light → .py（自动维护映射表）
python build_py.py

# 2. Nuitka 打包
vcvars64.bat
python -m nuitka --msvc=14.2 --onefile \
  --output-dir=nuitka_final --output-filename=lightharness.exe \
  --include-data-dir=webui=webui \
  --include-data-dir=stdlib=stdlib \
  build_py/main.py
```

## 文件

- `lightharness.exe` — 8.2MB 独立可执行文件
- `module_map.json` — 中文→英文模块名映射表（290 条）
- `build_py.py` — 批量编译脚本

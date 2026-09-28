# lightharness Nuitka 打包指南

## 前置条件

- Python 3.10+（Nuitka 专用）
- Visual Studio 2019 BuildTools（MSVC 14.2）
- Nuitka 4.2.2

## 一键打包命令

```bash
# 1. 编译 .light → .py（自动维护 module_map.json 中文→英文映射）
python build_py.py

# 2. Nuitka 打包
"C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
python -m nuitka --msvc=14.2 --onefile ^
  --output-dir=nuitka_final --output-filename=lightharness.exe ^
  --include-data-dir=webui=webui ^
  --include-data-dir=stdlib=stdlib ^
  build_py\main.py
```

## 打包流程详解

### 第 1 步：build_py.py 做了什么

1. **收集** src/*.light（201 个）+ stdlib/*.light（87 个）+ 入口
2. **映射表**：维护 `module_map.json`（中文模块名 → 英文别名），保持稳定不漂移
3. **编译**：每个 .light 编译成 build_py/英文名.py
4. **复制实现**：stdlib/*.py 实现文件按映射表复制到 build_py/（覆盖纯导出空壳）
5. **import 替换**：
   - `from 中文名 import` → `from 英文名 import`
   - `import 中文名` → `import 英文名 as 中文名`（保留别名，后续代码用中文名调用）
6. **补丁 fallback**：把 `types.ModuleType('_light_builtin')` 替换为 `__import__('light_builtins')`

### 第 2 步：Nuitka 做了什么

- MSVC 14.2 编译 C 代码
- onefile 模式打包成单个 exe
- 包含 webui/ 静态文件 + stdlib/ 目录

## 关键文件

| 文件 | 作用 |
|------|------|
| `build_py.py` | 批量编译脚本 |
| `module_map.json` | 中文→英文模块名映射表（290 条） |
| `build_py/` | 编译输出目录 |
| `nuitka_final/lightharness.exe` | 最终 exe |

## 已知问题及解决方案

### 1. 中文模块名 GBK 乱码
**方案**：build_py.py 维护 module_map.json，编译时转英文名

### 2. 纯导出模块无函数体
**方案**：复制 stdlib/*.py 实现文件覆盖

### 3. fallback 缺内置函数
**方案**：补丁 240 个文件，改 import light_builtins

### 4. signal.py 覆盖标准库
**方案**：重命名为 light_signal.py

### 5. import 缺少别名
**方案**：`import 中文名` → `import 英文名 as 中文名`

## 测试

```bash
# 启动 exe
lightharness.exe

# 输出：web 服务器已启动 http://127.0.0.1:PORT/?token=xxx
```

## 客户部署

1. 把 `lightharness.exe` 复制到目标机器
2. 双击运行
3. 浏览器打开 `http://127.0.0.1:PORT/?token=xxx`
4. 无需安装 Python

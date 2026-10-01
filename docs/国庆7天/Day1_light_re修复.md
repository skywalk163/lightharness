# Day1 ｜ `_light_re` import hook 缺陷修复报告

> 执行：Day1-A 线 ｜ 日期：2026-10-01 ｜ 仓库：`light-merge`（语言本体）+ `lightharness`（宿主/应用侧钩子副本）
> 判据：最小探针 exit 0 + 三元（failed 不增 / skipped 不增 / passed 不降）
> 所有数字均为本机实跑，`未跑` 的条目已如实标注；未执行任何 `git add/commit/push`。

---

## 0. 一句话结论

**断掉的层 = 导入钩子的「别名 → 真实 stdlib 模块」解析层（运行期），不是词法层、也不是 codegen。**

codegen 生成 `from _light_re import re_花括号` 是**正确**的；真正的断点在于：
实际生效的那份钩子（`lightharness/stdlib/_light_import_hook.py`，宿主仓的副本）把别名 `_light_re`
剥成 `re` 之后，**只在宿主的 `search_paths`（`lightharness/src`、`lightharness/stdlib`、`lightharness`）
里找 `re.light`** —— 而纯光明实现 `re.light` 只存在于**编译器仓** `light-merge/stdlib/re.light`，
宿主搜索路径里根本没有 → `ModuleNotFoundError: No module named '_light_re'`。

---

## 1. 根因（取证链，每条都贴了命令与退出码）

### 证据 1：最小探针复现（exit 1）

探针 `lightharness/.scratch/lr_probe.light`：

```
从 re 导入 re_花括号。

段落 主:
  显示 re_花括号(2, 3)

主()
```

```bash
cd /g/dswork/duan-light-merge && PYTHONUTF8=1 light-merge/.venv/Scripts/python.exe \
    light-merge/cli/light.py run lightharness/.scratch/lr_probe.light
```

输出：`错误: 模块未找到 / No module named '_light_re'`（指向第 1 行第 15 列），**EXIT=1**。

### 证据 2：生成码正确——锅不在 codegen

```bash
light-merge/.venv/Scripts/python.exe light-merge/cli/light.py compile \
    lightharness/.scratch/lr_probe.light -o lightharness/.scratch/lr_probe_compiled.py
```
EXIT=0，产物里确实是被期待的那一行（别名确由 codegen 生成）：

```
from _light_re import re_花括号
```

生成点 = `light-merge/src/code_generator.py:5064-5077`（`_PYTHON_LEG_PURE_LIGHT_ALIAS = frozenset({'re'})`，
定义在同文件 `:52`）。`src/code_generator.py:5115` 那条注释「`import _light_re` 导致 re 未定义」说的是
**另一件事**：`导入 re`（无 symbols 的多模块分支）不能走别名；它在 `:5117-5124` 已经正确地避开了。
即 5115 的注释是「已修过的历史说明」，不是本次缺陷的机制线索——v2 计划书把它当线索属于误指。

### 证据 3：换对 stdlib 立刻通过 → 证明 `re.light` 本身是好的

```bash
light-merge/.venv/Scripts/python.exe light-merge/cli/light.py run \
    lightharness/.scratch/lr_probe.light --stdlib-dir light-merge/stdlib
```
输出 `{2,3}`，**EXIT=0**。说明：只要钩子搜索路径里有 `light-merge/stdlib`，别名解析就成立。

### 证据 4：真正生效的钩子是宿主副本（关键一击）

`lightharness/.scratch/lr_diag2.py` 复刻 `light.py run` 的调用链后打印：

```
RUN FAIL: ModuleNotFoundError No module named '_light_re'
_light_import_hook = G:\dswork\duan-light-merge\lightharness\.scratch\..\stdlib\_light_import_hook.py
finder.search_paths = ['...\lightharness\.scratch', '...\lightharness\stdlib', '...\duan-light-merge']
find_spec(_light_re) = None
code_generator in sys.modules: True  G:\dswork\duan-light-merge\light-merge\src
```

原因链条：生成码引导 `_generate_python_header`（`src/code_generator.py:1216-1220`）先
`sys.path.insert(0, _light_stdlib)`，而 `_light_stdlib` 按「脚本所在目录往上找 stdlib」探测到的是
`lightharness/stdlib`（该目录确实存在且含 `builtins.py`），于是 `import _light_import_hook`
命中的是**宿主仓那份钩子**，而不是 light-merge 那份。`lightharness/运行.py:88-95` 又把宿主路径
置前（R100 路 B 的宿主优先序），进一步坐实。

### 证据 5：剥前缀逻辑早就有了，缺的是「找不到之后去哪儿找」

修复前 `lightharness/stdlib/_light_import_hook.py:219-222` 已经会把 `_light_` 前缀剥掉
（R100 路 B 修的），但剥完之后 `for base in self.search_paths` 一圈下来都没有 `re.light`，
函数末尾直接 `return None` → Python 继续走标准导入 → `ModuleNotFoundError`。

**点名根因位置**：`lightharness/stdlib/_light_import_hook.py` 的 `LightFinder.find_spec`
（修复前 `:207-259`，尾行 `return None`）/ 同源缺陷也在 `light-merge/stdlib/_light_import_hook.py:212-258`。

---

## 2. 做了什么（改动清单）

| 文件 | 改动 | 行号（修复后） |
|---|---|---|
| `light-merge/stdlib/_light_import_hook.py` | 新增 `LightFinder._alias_fallback_dirs()` + `find_spec` 末尾别名兜底 | 212-241 / 296-310 |
| `lightharness/stdlib/_light_import_hook.py` | 同上（两份钩子按 R100 路 B 惯例同步）+ 新增 `_THIS_DIR` 锚点 | 42 / 212-240 / 288-302 |

`src/`（codegen / lexer / parser）**一行未改**；`stdlib/*.light` **一行未改**。

### diff 摘要

```python
# 新增：LightFinder._alias_fallback_dirs()
def _alias_fallback_dirs(self) -> list:
    dirs = []
    for cand in (_THIS_DIR,):                       # 1) 本钩子所在目录 light-merge 版即编译器 stdlib
        if cand and os.path.isdir(cand) and cand not in dirs:
            dirs.append(cand)
    for mod_name in ('code_generator', 'light_parser_v3'):   # 2) 由编译器模块位置反推 <安装根>/stdlib
        mod = sys.modules.get(mod_name)
        if mod is None and _COMPILE_DEPTH == 0:
            try: mod = importlib.import_module(mod_name)
            except Exception: mod = None
        ...
        for cand in (os.path.join(os.path.dirname(src_dir), 'stdlib'), src_dir):
            if os.path.isdir(cand) and cand not in dirs:
                dirs.append(cand)
    return dirs
```

```python
# find_spec 末尾新增（替代原来的裸 return None）
        # ---- 别名兜底：只对 `_light_<名>` 形式生效，且只在 search_paths 全落空后 ----
        if fullname != realname:
            try:
                for base in self._alias_fallback_dirs():
                    light_file = os.path.join(base, realname + '.light')
                    if not _exists_exact(base, realname + '.light'):
                        continue
                    if _exists_exact(base, realname + '.py') and not _is_pure_light(light_file):
                        continue
                    loader = LightLoader(fullname, light_file, self._stdlib_dir)
                    return importlib.util.spec_from_loader(fullname, loader)
            except Exception:
                return None
        return None
```

### 为什么这样改是窄的、不会重新踩 R100 的坑

1. **只对别名生效**：`if fullname != realname`，即只有 `_light_<名>` 这种 codegen 刻意生成的形态才走兜底。
   `_light_import_hook` 自己作为模块被 import 时 realname=`import_hook`，各兜底目录都没有 `import_hook.light` → 照旧 `None`。
2. **只在宿主全线落空后触发**：兜底排在 `for base in self.search_paths` 之后，宿主同名 `.py` 永远优先。
   实测 `find_spec('字符串工具')` 仍为 `None`（宿主的 `字符串工具.py` 归标准机制），宿主优先序未变。
3. **不污染 search_paths**：兜底目录不 `extend` 进 `search_paths`，因此不会让编译器 stdlib 反过来遮蔽宿主模块。
4. `.py` 优先原则保留：兜底目录里若存在同名 `.py`，仍要求 `.light` 显式声明「纯光明实现」才接管。

---

## 3. 现在能跑什么

### 3.1 最小探针（修复后）

```bash
cd /g/dswork/duan-light-merge && PYTHONUTF8=1 MSYS_NO_PATHCONV=1 \
    light-merge/.venv/Scripts/python.exe light-merge/cli/light.py run \
    lightharness/.scratch/lr_probe.light
```

```
{2,3}
EXIT=0
```

（修复前同一条命令 EXIT=1 + `No module named '_light_re'`。）

### 3.2 扩展探针（同时验证「`导入 re` 仍必须命中 CPython re」这条不变量）

`lightharness/.scratch/lr_probe4.light` = `从 re 导入 re_花括号 re_编译 re_查找所有 re_替换。` + `导入 re。`
（后者用 `re.compile(...).findall(...)`）：

```bash
# CLI 路径
... light.py run lightharness/.scratch/lr_probe4.light
{2,3}
['1', '22', '333']
#
['1', '22']
EXIT=0

# 宿主路径
cd lightharness && .../python.exe 运行.py _lr_p4.light
{2,3}
['1', '22', '333']
#
['1', '22']
EXIT=0
```

前 3 行走 `re.light` 纯光明实现，最后 1 行走 CPython `re` —— `src/code_generator.py:5115` 注释要求的那条不变量仍然成立。

### 3.3 钩子层体检（`lr_diag.py` / `lr_diag2.py`）

```
find_spec(_light_re) = ModuleSpec(name='_light_re', loader=<LightLoader>)
   loader.light_path = G:\dswork\duan-light-merge\light-merge\stdlib\re.light
find_spec(字符串工具) = None          ← 宿主优先序未被破坏
import _light_re OK -> ...\light-merge\stdlib\re.light
```

### 3.4 三元数字对比

| 套件 | 基线（修复前） | 修复后 | 差值 |
|---|---|---|---|
| lightharness `tests/unit` | **588 passed / 0 failed / 0 skipped** | 见 §5 | 待填 |
| lightharness `tests/test_回归.py`（examples） | 未取到干净基线（见 §5.1） | 见 §5 | — |
| light-merge `tests/unit` | 未取到干净基线（见 §5.2） | 见 §5 | — |
| light-merge `tests/unit/test_light_import_hook_stdlib.py` | 5 passed（修复后补跑） | **5 passed** | 0 |
| light-merge `tests/test_module_system.py`（默认） | **1 skipped（整模块跳过）** | 1 skipped | 0 |
| light-merge `tests/test_module_system.py`（补 ANTLR 产物路径） | 未跑 | **46 passed / 12 skipped** | 见 §4 |

---

## 4. 关于「`test_regex_*` skip 应转 passed」——结论：**与 `_light_re` 无关，不建议在本线改**

v2 计划书要求「修好后 `test_module_system.py:264-297` 的 `test_regex_*` skip 应转 passed」。实跑结论是两回事：

1. 该模块**默认根本进不去**：缺 ANTLR 生成产物 `LightLangLexer`
   （`pip` 里有 `antlr4-python3-runtime 4.13.2`，但生成产物在 `antlrparser/light_parser/`，
   而测试只把 `../antlrparser` 加进 `sys.path`），整模块 `pytest.skip(allow_module_level=True)` → 只报 1 skipped。
2. 把 `antlrparser/light_parser` 补进 `PYTHONPATH` 后模块能跑（**46 passed / 12 skipped**），
   此时 `test_regex_search/findall/replace/is_match` 的 skip 原因是：

   ```
   正则搜索 API 不兼容: 执行错误: No module named '正则'
   正则查找所有 API 不兼容: 执行错误: No module named '正则'
   正则替换 API 不兼容: 执行错误: No module named '正则'
   正则是否匹配 API 不兼容: 执行错误: No module named '正则'
   ```

   即**测试自己写了不存在的模块名《正则》**（真实模块是 `正则表达式.light` / `re.light`），
   不是 `_light_re` 断链。`test_regex_escape` 则是 `skipTest("正则模块没有\"转义\"函数")`——设计如此。

→ 建议另立一条:**修正测试用例里的模块名**（`正则` → `正则表达式`）或补齐 ANTLR 产物路径，
  不要塞进本线（改测试让它们变绿 ≠ 修缺陷）。

---

## 5. 未完成 / 如实交代

- **5.1 examples（`tests/test_回归.py`）基线丢失**：基线任务在打补丁前启动，但跑到中途读到补丁，
  且输出未落盘导致 SUMMARY 行丢失，属不可用数据，已作废（未在报告中冒充 baseline）。
  原因是补跑需 ~15 分钟且不能与本线其它长跑并发（并发会污染结果）。
- **5.2 light-merge `tests/unit` 基线缺失**：同上，未在打补丁前单独留一份干净基线。
- **5.3** §3.4 中标注「见 §5」的三元组以报告末尾的命令清单实跑结果为准。

---

## 6. 命令清单（真实执行 + 退出码）

见文末表格。

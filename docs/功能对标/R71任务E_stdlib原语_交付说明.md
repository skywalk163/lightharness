# R71 任务E · stdlib 原语补全（L-160 主目录 / L-174 随机UUID）交付说明

> 轮次：R71 第 1 轮 / 任务 E　|　日期：2026-09-19
> 来源任务书：`docs/功能对标/光明语言语法缺陷清零_R71-R73三轮并发开发任务书.md`
> 严重度：中（L-160 低 / L-174 中）

## 一、结论速览

| 项 | 结果 |
|----|------|
| 零导入 `主目录()`（L-160） | ✅ 可用：Windows 取 `USERPROFILE`，其余取 `HOME`（对齐 `os.path.expanduser("~")`） |
| 零导入 `随机UUID()`（L-174） | ✅ 可用：uuid4 等价（os.urandom 熵源、版本位 4、RFC 4122 变体位、8-4-4-4-12 连字、36 位） |
| 新增测试 | `lightharness/examples/test_R71_E_stdlib原语.light`（格式 13 断言 + 1000 次零碰撞 + 主目录 6 断言，全绿） |
| 全量回归 | `python -m pytest tests/test_回归.py -q` → **446 passed，零红** |
| 双后端 | SRC 与 unified 均验证（`主目录`/`随机UUID` → `_light_builtin.*`） |
| 遮蔽兼容 | `设 主目录 为 …` / 形参 `随机UUID` 正常压过内置（builtin_map 让位语义不变） |
| 门禁 | 地板门禁 70.21%（基线 69.57%，未降 ✓）；原生产品门禁通过；`test_ci_gates_round9.py + test_ci_gates.py` 68 passed |

## 二、实现口径（与任务书建议的差异及理由）

任务书实现要点建议在 `stdlib/builtins.py` 直接写
`def 主目录(): return os.path.expanduser("~")` / `def 随机UUID(): return str(uuid.uuid4())`。
本任务改走**地板搬迁（has_light_impl）**路线，原因：

- `tools/ci/floor_bootstrap.py` 门禁对 `builtins.py` 顶层函数与
  `任务书/自举地板清单.json` 做**名单双向咬合**：builtins.py 新增 def 必须登记；
- 新登记若归 `native_required`（读环境/熵源确实是真边界）会触发
  「native_required 名单**新增即红**、数量只降不升」的棘轮；
- 归 `has_light_impl` 则要求纯光明真身可定位、不被同名 `.py` 遮蔽、builtins.py 真转发。

于是按既有 `内置核心字符串.light` 等范式交付：

1. **新增纯光明真身模块 `stdlib/内置核心系统.light`**（模块名独立，无同名 `.py`）：
   - `段落 主目录`：`环境变量("USERPROFILE")` 为空取 `环境变量("HOME")`——真系统边界留在
     既有 native_required 地板内置 `环境变量`，光明层只做组合；
   - `段落 随机UUID`：`随机字节(16)`（os.urandom，native_required 地板内置）作熵源，
     光明层置版本/变体位、拼 8-4-4-4-12。
2. **`stdlib/builtins.py` 增两条惰性转发**（函数体内 `import 内置核心系统`，遵守地板
   转发三规矩；不顶层 import）：
   ```python
   def 主目录() -> str:
       """获取当前用户主目录（地板已搬迁：真身 stdlib/内置核心系统.light:10；L-160，R71-E）。"""
       import 内置核心系统
       return 内置核心系统.主目录()
   ```
   `随机UUID` 同型（真身 :21）。
3. **双 codegen `builtin_map` 注册**：`src/code_generator.py` 与
   `src/code_generator_unified.py` 各加 `'主目录': '_light_builtin.主目录'`、
   `'随机UUID': '_light_builtin.随机UUID'`。
4. **双副本同步**：`lightharness/stdlib/` 是自包含部署副本（生成产物序言按
   `<脚本目录>/stdlib` 先命中它），`builtins.py` 增量与 `内置核心系统.light` 均已镜像。
5. **门禁账同步**：
   - `任务书/自举地板清单.json`：+2 条 `has_light_impl`（总数 154→156、分子 64→66）；
   - `任务书/原生腿产品清单.json`：`stdlib原生可编译矩阵` 补入
     `内置核心系统 = 可编译`（真编译实测 rc=0）。

## 三、顺手修复的存量红（与门禁相关的环境清账）

- `内置核心列表.light` 的 **11 条清单证据行整体漂移**（该文件此前增行、清单未跟），
  修复前 `floor_bootstrap.py` 本就红（53/92）；按当前段落行逐条更正后地板门禁回绿：
  **66/94 = 70.21%**（基线 69.57%，棘轮只升不降 ✓）。
- 注：地板门禁主体不在 pytest 门禁内（pytest 只咬合名单集合），此修复属环境清账。

## 四、验证记录

| 检查 | 结果 |
|------|------|
| `python 运行.py examples/test_R71_E_stdlib原语.light` | rc=0 全部通过 |
| SRC / unified 探针（导入真身 + 零导入内置双路径） | 均 rc=0，UUID v4 格式正确 |
| 1000 次唯一性 | 零碰撞 |
| 主目录 × 环境变量一致性 | Windows 下 == USERPROFILE；POSIX 语义 == HOME |
| `python -m pytest tests/test_回归.py -q` | **446 passed，零红** |
| `floor_bootstrap.py --root .` | 通过（70.21% ↑） |
| `native_product.py --root .` | 通过（22.81% ↑，未实测/坏路径未增） |
| `test_ci_gates_round9.py + test_ci_gates.py` | 68 passed |

## 五、边界与未覆盖项

- LLVM 原生腿（`codegen_typed.py`）未注册这两个符号——任务书实现要点只要求
  `code_generator.py` / `code_generator_unified.py` 两条腿；原生腿注册属 R73 位运算/
  工具收尾泳道的既有口径（`随机字节`/`环境变量` 等真边界同样只在 Python 腿）。
- `主目录()` 不做 `~username` 展开与 `HOMEDRIVE/HOMEPATH` 兜底（对齐主路径语义；
  若后续需要，在 `内置核心系统.light` 光明层补组合即可，不动地板）。

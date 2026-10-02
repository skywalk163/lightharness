# Day9 · 语言缺陷账终态（LP-D-014~017）

> 派单：Day2 S3｜执行：C 路｜日期：2026-10-02
> 被测 SHA：light-merge `d6b84a716` / lightharness `f21c0191` / lightplugin `11c78735`
> 跑法：`light-merge/.venv/Scripts/python.exe light-merge/cli/light.py run <探针>`（SRC 默认后端）

---

## 〇、一句话

四条全部终态，**无一提代码修复、无需快门/门**：
- LP-D-014 / 015 → **销账**（契约纠正，反跑验证）
- LP-D-016 → **已修复**（stdlib R99-C 名实对齐，Day2 复测行为与注释一致）
- LP-D-017 → **已修复**（宿主侧 R99，回归 14/14 green）

活账 `lightharness/docs/功能对标/语言缺陷账.md` 四条状态列已全部刷新，**不再有「待定」**。

---

## 一、LP-D-014 · 模块顶层写 `全局 X。`

### 探针
`probes/lp014_probe.light`：
```light
全局 环境字典。
设 环境字典 为 {}
```

### 实测输出
- 命令：`python cli/light.py run probes/lp014_probe.light`
- rc = **1**
- stderr：`代码生成错误: 「全局」只能写在段落（函数）体内：模块级的变量本来就在最外层作用域，无需声明。 (节点类型: ScopeDeclStmt)`
- 日志：`logs/day2/S3_lp014_probe.log{,.err}`

### 反跑（契约纠正后的正确写法）
`probes/lp014_fixed.light`：
```light
设 环境字典 为 {}
段落 主:
  打印("ok")
主()
```
- rc = **0**，stdout = `ok`
- 日志：`logs/day2/S3_lp014_fixed.log`

### 判定与处置
**销账（契约纠正，非语言缺陷）**。编译器行为正确且诊断清晰：模块顶层本就在最外层作用域，不需要 `全局`；只有段落内回写模块级标量才需要。活账状态列已从「已定性（契约纠正）」刷新为「**已销账（契约纠正，Day2 2026-10-02 反跑验证）**」。

---

## 二、LP-D-015 · `切片` 并非全局内置

### 探针
`probes/lp015_probe.light`：
```light
段落 主:
  打印 切片("abcdef", 1, 3)
主()
```

### 实测输出
- rc = **1**
- stderr：`名称错误: name '切片' is not defined`
- 日志：`logs/day2/S3_lp015_probe.log{,.err}`

### 反跑（正确写法 `[起:止]`）
`probes/lp015_fixed.light`：
```light
段落 主:
  设 s 为 "abcdef"
  打印(s[1:3])
主()
```
- rc = **0**，stdout = `bc`（开区间：索引 1 起、3 止，不含 3）
- 日志：`logs/day2/S3_lp015_fixed.log`

### 判定与处置
**销账（契约纠正，非语言缺陷）**。`切片` 不是全局内置；取子串用 `[起:止]` 索引切片。活账状态列已刷新为「**已销账（契约纠正，Day2 2026-10-02 反跑验证）**」。`light-merge/docs/STDLIB_REFERENCE.md` 不在本次修改范围（契约允许但不要求）；stdlib/内置核心判型.light 与切片相关文档已在 R 系列修复中对齐，本次无新增文档改动。

---

## 三、LP-D-016 · 判型族名实错位

### 探针
`probes/lp016_probe.light`：
```light
段落 主:
  打印(是数字(7))
  打印(是数字("7"))
  打印(是数字符("7"))
主()
```

### 实测输出
- rc = **0**
- stdout：
  ```
  True
  False
  True
  ```
- 日志：`logs/day2/S3_lp016_probe.log`

### 追补探针（`probes/lp016_followup.light`）
```light
段落 主:
  打印(是数字符("7"))       # True
  打印(是数字符("abc"))      # False
  打印(是数字符("7a"))       # False
  打印(是数字符(7))          # 类型错误（isdigit 不吃 int）
  打印(是数字("7"))          # False（名实错位依旧：是数值语义）
  打印(是数字(7))            # True
主()
```
- rc = **1**（最后一组 `是数字符(7)` 抛类型错误，符合预期）
- stdout：`True / False / False`
- stderr：`类型错误：descriptor 'isdigit' for 'str' objects doesn't apply to a 'int' object（stdlib/内置核心判型.light:64）`
- 日志：`logs/day2/S3_lp016_followup.log{,.err}`

### 根因（读 stdlib/内置核心判型.light:59-106）
Day2 复测时发现：**账内旧记「是数字符 根本未注册」已过时**。stdlib 层 R99-C 已做名实对齐：
- 内部段落 `是数字(字符)` = `str.isdigit(字符)`（:63-64）
- 内部段落 `是数值(值)` = `isinstance(值, int) 或 isinstance(值, float)`（:81-84）
- code_generator builtin_map：用户关键字 `是数字` → `是数值`；`是数字符` → `是数字`（内部段落名）
- 另补 `字符串全数字(串)`（:101-106）全串版
- :59-62 注释明确写：「判值是否为数值类型用是数字；判字符串是否全是数字字符用是数字符」

实测行为与注释完全一致。

### 判定与处置
**已修复（stdlib R99-C 名实对齐，Day2 2026-10-02 复测）**。活账状态列已从「已定性待修」刷新为「**已修复（stdlib R99-C 名实对齐）**」。无需提代码修复，无需快门。

---

## 四、LP-D-017 · 工具 schema 注册期形状校验

### 探针
`probes/lp017_probe.light`（注册 `properties: []` 坏 schema）：
```light
从 工具 导入 工具注册表, 造工具定义
段落 主:
  设 reg 为 新建 工具注册表()
  设 坏 为 造工具定义("probe017", "坏schema探针", ["type": "object", "properties": []], 空)
  reg.注册(坏)
  打印("不应到达")
主()
```

### 实测（回归套件）
直接跑权威回归 `tests/unit/test_工具_schema自检.py`（该文件即 LP-D-017 修复的固化）：
- 命令：`python -m pytest tests/unit/test_工具_schema自检.py -v -o "addopts=" -p no:xdist`
- 结果：**14 passed in 56.05s**
- 关键用例：
  - `test_坏schema_properties空列表_注册期报错` PASSED（`properties: []` 被拦下）
  - `test_坏schema_properties非空列表_注册期报错` PASSED
  - `test_正常schema_properties空映射_注册成功` PASSED
  - `test_正常100工具冒烟` PASSED
- 日志：`logs/day2/S3_pytest_lp017_schema.log`

### 判定与处置
**已修复（宿主侧 R99，Day2 2026-10-02 复测 14/14 green）**。`lightharness/src/工具.light` 的 `工具注册表.注册` 已加注册期形状自检（type=object、properties 为映射、required 为字符串列表、enum/items/oneOf 递归校验），不合法即抛 INVALID_TOOL_SCHEMA 并点名工具名。活账状态列已从「已定性待修」刷新为「**已修复（宿主侧 R99）**」。

---

## 五、四件套

| 项 | 值 |
|---|---|
| light-merge SHA | `d6b84a7169b645231d89e1f27ba20321a148d603` |
| lightharness SHA | `f21c0191e663fa9a3b397bbc8f377cdaf19caf2b` |
| lightplugin SHA | `11c78735a81d32673d880e44a264d6ffada179b4` |
| 日志目录 | `G:\dswork\duan-light-merge\logs\day2\S3_*` |
| 探针目录 | `lightharness/docs/国庆7天/probes/lp01{4,5,6,7}_*.light`（共 7 个文件） |
| 改动文件 | `lightharness/docs/功能对标/语言缺陷账.md`（四条状态刷新）、`lightharness/tests/unit/test_Day4_LP013_探针回归.py`（xfail reason 刷新，见 S4 附件） |
| 代码改动 | **0**（未动 light-merge/src/、antlrparser/、stdlib/） |

## 六、反跑判据验证

1. LP-D-014：按错误写法（模块顶层 `全局 X。`）跑 → rc=1 复现原报错 ✓；按正确写法跑 → rc=0 ✓
2. LP-D-015：按错误写法（`切片(...)`）跑 → rc=1 `name '切片' is not defined` ✓；按正确写法（`[1:3]`）跑 → rc=0 `bc` ✓
3. LP-D-016/017：已修复项，若未来回归，对应探针/回归用例（`test_工具_schema自检.py`、`test_Day4_LP013_探针回归.py` ANTLR 两例）会立红。

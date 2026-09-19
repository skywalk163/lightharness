# R73 任务D · match-case 模式匹配完善（G-11）修复说明

> 轮次：R73 任务 D　|　日期：2026-09-19
> 来源任务书：`docs/功能对标/光明语言语法缺陷清零_R71-R73三轮并发开发任务书.md` §五 D
> 严重度：低（G-11，「待确认」→ 确认缺字典/元组解构、rest 死循环挂死）

## 一、结论速览

| 项 | 结果 |
|----|------|
| 字典解构 `情况 {"键": 值, ...}:` | ✅ 新增（此前 LBRACE 起始模式被 parser 拒绝） |
| 元组解构 `情况 (甲, 乙):` | ✅ 新增（此前 LPAREN 起始模式被 parser 拒绝） |
| 列表 rest `情况 [首, *余]:` | ✅ 新增（此前 `*` 不消费 token → 编译死循环挂死） |
| 守卫（`若` 关键字 / 布尔守卫式 / 括号守卫式） | ✅ 回归验证（原有能力，tuple 分支回退路径新增覆盖） |
| 通配符 `_` | ✅ 回归验证（顶层 + 嵌套） |
| 顶层 `情况 *余:` | ✅ 编译期明确报错 rc≠0（rest 仅限列表/元组模式内部） |
| 双后端 | SRC（code_generator.py）与 unified（code_generator_unified.py）同步实现 |
| 新增测试 | `lightharness/examples/test_R73_D_模式匹配.light`（15 段 19 断言全绿） |
| 反向哨兵 | `lightharness/examples/test_R73_D_顶层星号模式.light`（rc≠0，登记 EXPECT_RED） |
| 全量回归 | `python -m pytest tests/test_回归.py -q` **462 passed，0 failed** |

## 二、语法口径（本次新增/确认）

```光明
# 字典解构：键取字面量（字符串/数字/真/假/空），值递归匹配
匹配 {"甲": 1, "乙": 2}:
    情况 {"甲": 值, "乙": 值乙}: 打印 值 + 值乙      # 字典解构匹配

# 元组解构：多元素 / 单元素 / 空
匹配 (1, 2):
    情况 (甲, 乙): 打印 甲 + 乙                       # 元组解构匹配

# 列表 rest：`*名` 绑定剩余元素为列表
匹配 [1, 2, 3, 4]:
    情况 [首, *余]: 打印 首 + 列表(余)                # 输出 1[2, 3, 4]

# 守卫三形态
匹配 85:
    情况 x 若 x >= 80: 打印 x                          # 「若/如果」关键字守卫
匹配 分数:
    情况 分数 >= 90: 打印 "优"                        # 布尔守卫式（纯表达式守卫）
匹配 高度:
    情况 (高度 >= 185): 打印 "高"                     # 括号守卫式（tuple 分支回退重解析）

# 通配符（原有，回归验证）
匹配 任意值:
    情况 _: 打印 "通配命中"
```

约束：rest 模式（`*名`）只允许出现在列表/元组模式内部；顶层 `情况 *余:` 编译期报
「rest 模式 '*' 只能出现在列表 '[]' 或元组 '()' 模式内部（如 `情况 [首, *余]:`）」。
or 模式（`情况 1 | 2:`）按 L2 规范明确不支持，本任务不实现。

## 三、修复前行为（本次消灭）

- `情况 {"甲": 值, "乙": 值乙}:` → 解析错误（`_parse_match_pattern` 无 LBRACE 起始分支）；
- `情况 (甲, 乙):` → 解析错误（无 LPAREN 起始分支）；
- `情况 [首, *余]:` → **编译挂死**（`*` 分支不消费 token，`while` 死循环）——比
  「不支持」更严重的缺陷，实测以超时终止；

## 四、修复落点（light-merge/src/）

1. **ast_nodes_v3.py**
   - `MatchPattern` 新增 `keys: List[str] = None`（dict 模式键——规范化为 Python 字面量
     文本）与 `trailing_comma: bool = False`（tuple 单元素尾逗号）两个 slot，
     `__init__`/`__repr__` 同步扩展。
2. **parser_stmt.py**
   - `_parse_match_pattern` 新增 `in_sequence: bool = False` 参数：列表/元组内元素递归
     传 `True`，rest 模式仅在 `in_sequence=True` 时合法。
   - 新增 tuple 分支：逐元素解析；遇到比较/逻辑守卫运算符（`>=`/`<=`/`==`/`!=`/`>`/`<`
     及 `且`/`或` 等）立即停止且**不消费**该运算符与右括号，返回部分 tuple——交上层
     `_parse_match_case` 的 `_is_match_guard_operator` 回退逻辑整体重解析为表达式
     （`情况 (分数 >= 90):` 的支撑路径）。
   - 新增 dict 分支：键必须是字面量（字符串/数字/真/假/空），规范化为 Python 字面量
     文本存入 `keys`；值递归 `_parse_match_pattern`。
   - 新增 rest 分支：`*名`，「名」递归为模式元素；`in_sequence=False` 时报上述中文错误。
   - 兜底分支：由「不消费 token 返回 wildcard」（死循环根因）改为「消费 token +
     wildcard」；对守卫式（如 `情况 -分数 >= 0:` 以运算符起始）不误伤——守卫回退
     会重置 pos 整体重解析表达式。
3. **code_generator.py**（SRC 主管线）
   - `_generate_match_pattern` 新增 tuple（空 `()` / 单元素 `(甲)` 或 `(甲,)` 尾逗号 /
     多元素）、dict（键字面量 + 值递归）、rest（`*` + 内层模式）三分支。
4. **code_generator_unified.py**（unified 后端对齐）
   - 同样三分支，沿用该文件 hasattr/getattr 防御式风格。

## 五、测试

- `lightharness/examples/test_R73_D_模式匹配.light`（15 段 19 断言）：
  字典解构（字符串键/数字键）、元组解构、列表 rest、列表字面全匹配、`若` 关键字守卫、
  布尔守卫式、括号守卫式、顶层通配、类型匹配+绑定、嵌套解构（dict 套 dict 套 list）、
  元素个数不匹配回退、缺键回退、默认分支、字符串字面模式——`python 运行.py` rc=0 全绿。
- `lightharness/examples/test_R73_D_顶层星号模式.light`（反向哨兵）：
  顶层 `*余` rc≠0，已登记 `tests/test_回归.py` EXPECT_RED。

## 六、验证

- 全量回归：`python -m pytest tests/test_回归.py -q` → **462 passed，0 failed**（零红）。
- 并行轮次收尾：R73-C 将 `记录` 提升为关键字后，`examples/test_宿主配置.light` 的
  局部变量 `记录` 触发关键字冲突解析错误；本任务将用例变量改名 `记录表`（最小侵入，
  导入的 `记录变更` 函数名不动），用例恢复 rc=0。`_e2_会话存储_tmp/` 历史残留造成
  `test_会话存储.light` 偶发「初始会话列表=4」——清理临时目录后 rc=0（环境残留，
  非代码缺陷）。
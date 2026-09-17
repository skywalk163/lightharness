# 任务5（R54·P1）交付报告 —— 跨平台复测（0.82 / FreeBSD 15.1）

> 日期：2026-09-17 ｜ 状态：**完成**
> 交付物：本报告 ｜ 铁律遵守：0.82只读执行。
> 远程副本：`/tmp/r44-20260917-230951`（全量同步，含R54 L-170修复）
> 验证对象：任务2 L-170编译器修复（`src/parser_stmt.py`）

---

## 一、0.82环境信息

| 项 | 值 |
|---|---|
| 主机 | 192.168.0.82（FreeBSD 15.1） |
| Python | /usr/local/bin/python3.11 |
| 远程副本 | /tmp/r44-20260917-230951 |
| 同步方式 | 全量tar.gz打包上传解压（41914文件，127.2MB） |
| examples数量 | 420（与本机一致） |

---

## 二、L-170复现用例验证（0.82）

**用例**：`light-merge/examples/test_L170.light`

**执行命令**：
```bash
cd /tmp/r44-20260917-230951/light-merge
export LIGHT_MERGE=$PWD
python -m cli.light run examples/test_L170.light
```

**实测输出**：
```
L170-OK
rc=0
```

**判定**：✅ **通过**。赋值真生效（运行时断言），静默变比较已消除。

---

## 三、lightharness全量pytest（0.82）

**执行命令**：
```bash
cd /tmp/r44-20260917-230951/lightharness
export LIGHT_MERGE=/tmp/r44-20260917-230951/light-merge
python -m pytest tests -q -o addopts=""
```

**实测结果**：
```
7 failed, 1260 passed, 5 skipped, 2 warnings in 403.14s (0:06:43)
```

---

## 四、失败项归因（7条，全部为存量词法红）

| # | 失败用例 | 归因 |
|---|---|---|
| 1 | test_R31_EMBED表保留+flaky修复_token.py::test_fanhui_embedded_scan_triggered | 存量词法红（R31 EMBED） |
| 2 | test_R31_EMBED表保留+flaky修复_token.py::test_fanhui_return_value_merged | 存量词法红（R31 EMBED） |
| 3 | test_R32_OPERATOR+MERGE_WHOLE精简_token.py::test_deleted_return_code_still_merged | 存量词法红（R32 OPERATOR） |
| 4 | test_回归.py::test_example_exit_code[test_R22_嵌入关键字冗余验证.light] | 存量词法红（R22） |
| 5 | test_回归.py::test_example_exit_code[test_R26_词首并入反向.light] | 存量词法红（R26 词首并入） |
| 6 | test_回归.py::test_example_exit_code[test_R26_词首并入混合.light] | 存量词法红（R26 词首并入） |
| 7 | test_回归.py::test_example_exit_code[test_R27_词首并入反向.light] | 存量词法红（R27 词首并入） |

**与R53基线对比**：

| 侧 | passed | failed | 说明 |
|---|---|---|---|
| R53（上轮基线） | 1260 | 7 | 7存量词法红 |
| R54（本轮） | 1260 | 7 | 7存量词法红（完全一致） |

**判定**：✅ **零新增红**。7条failed与R53基线完全同名同数，均为R22/R26/R27/R31/R32时代的存量欠账，与L-170修复无关。

---

## 五、结论

1. **L-170复现用例在0.82（FreeBSD）通过**：rc=0，`L170-OK` 打印（运行时断言赋值真生效）。
2. **lightharness全量pytest零新增红**：7 failed全部为存量词法红，与R53基线完全一致。
3. **跨平台一致性确认**：L-170修复（parser_stmt.py赋值分流）在FreeBSD上行为与Windows完全一致，未引入平台相关差异。
4. **0.82只读执行**：全程未修改0.82上任何源码，仅在/tmp副本上执行测试。

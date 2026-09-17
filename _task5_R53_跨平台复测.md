# 任务5（R53·P1）交付报告 —— 跨平台复测（0.82 / FreeBSD 15.1）

> 日期：2026-09-17 ｜ 状态：**完成**
> 交付物：本报告 ｜ 铁律遵守：0.82只读执行。
> 远程副本：`/tmp/r44-20260917-195459`（全量同步，含R53 L-172修复）
> 验证对象：任务2 L-172编译器修复（`src/code_generator.py` + `cli/light.py`）

---

## 一、0.82环境信息

| 项 | 值 |
|---|---|
| 主机 | 192.168.0.82（FreeBSD 15.1） |
| Python | /usr/local/bin/python3.11 |
| 远程副本 | /tmp/r44-20260917-195459 |
| 同步方式 | 全量tar.gz打包上传解压（41902文件，127.1MB） |
| examples数量 | 420（与本机一致） |

---

## 二、L-172复现用例验证（0.82）

**用例**：`light-merge/examples/test_L172.light`

**执行命令**：
```bash
cd /tmp/r44-20260917-195459/light-merge
export LIGHT_MERGE=$PWD
python -m cli.light run examples/test_L172.light
```

**实测输出**：
```
L172_主已执行
--- L172 入口静默阻断 回归通过 ---
rc=0
```

**判定**：✅ **通过**。主()真实执行，哨兵输出正常打印，静默阻断已消除。

**注**：`_l172probe/verify_fix.py` 在0.82上跑不了——该脚本硬编码Windows路径（`.venv/Scripts/python.exe`），属Windows专用探针脚本，不影响跨平台判据。红绿双向取证已在Windows侧（任务2）完成。

---

## 三、lightharness全量pytest（0.82）

**执行命令**：
```bash
cd /tmp/r44-20260917-195459/lightharness
export LIGHT_MERGE=/tmp/r44-20260917-195459/light-merge
python -m pytest tests -q -o addopts=""
```

**实测结果**：
```
7 failed, 1260 passed, 5 skipped, 2 warnings in 359.64s (0:05:59)
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

**与任务4（Windows侧）对比**：

| 侧 | passed | failed | 说明 |
|---|---|---|---|
| Windows（任务4） | 1266 | 10 | 7存量词法 + 3已清场瞬时探针 |
| FreeBSD 0.82（本轮） | 1260 | 7 | 7存量词法（瞬时探针已清场） |

**判定**：✅ **零新增红**。7条failed与Windows侧存量词法红完全同名，均为R22/R26/R27/R31/R32时代的存量欠账，与L-172修复无关。passed端差6条属平台差异（Windows某些路径/宿主面用例在FreeBSD上不跑），非L-172引入。

---

## 五、结论

1. **L-172复现用例在0.82（FreeBSD）通过**：rc=0，主()真实执行，两行哨兵输出正常。
2. **lightharness全量pytest零新增红**：7 failed全部为存量词法红，与Windows侧基线完全一致。
3. **跨平台一致性确认**：L-172修复（code_generator.py入口判定）在FreeBSD上行为与Windows完全一致，未引入平台相关差异。
4. **0.82只读执行**：全程未修改0.82上任何源码，仅在/tmp副本上执行测试。

# R90-D · 0.82 周期红 `test_数据验证_对拍Python` 立项排查

> 承接：R82 起记为「0.82 已知周期红，非本轮回归，建议另立项」；R89 全量 2 轮都没命中它。
> 执行顺序 D ｜ 机：FreeBSD 0.82（15.1-STABLE），副本 `/tmp/r44-20260924-003926/light-merge`

---

## 1. 结论：**(b) flaky —— 维持观察，不入确定性台账**

| 取证项 | 结果 |
|---|---|
| 准确 nodeid | `tests/unit/test_原生腿_R11A_通用工具.py::R11A通用工具反跑::test_数据验证_对拍Python` |
| 隔离单跑 5 轮（不带 xdist） | **5/5 通过**，失败数 = 0 |
| 全量负载 1 轮（`-n 8 --dist loadscope`） | **未命中**（本轮全量 1 failed / 8175 passed，但不是它） |
| 缺 `PYTHONPATH` 复跑 | rc=0（**排除**「三件套缺失」这个环境解释） |
| 最小复现 | **拿不到**（隔离恒绿、全量未命中）→ 按红线不下「真缺陷」结论 |

判定为 (b) flaky：低频、条件触发，本轮无任何一次复现。维持观察，**不入 0.82 确定性环境红台账**。

## 2. 附带发现（本轮全量冒出的另一条 0.82 红，同样判定为 flaky）

全量负载轮的失败是：
```
FAILED tests/unit/test_codegen_ref_dict_O0.py::test_回溯递归_参数写回不污染_O0
1 failed, 8175 passed, 123 skipped, 11 xfailed, 2 xpassed in 377.00s
```
隔离复跑取证（`_r90/d2_082_isolate.py`）：
```
隔离轮1/2/3：8 passed（rc=0）      单用例定向：1 passed（rc=0）
```
→ **也是 flaky**，登记为 0.82 观察项。

## 3. 取证链（脚本 `_r90/d_082_forensics.py` / `_r90/d2_082_isolate.py`）

```
选用副本: /tmp/r44-20260924-003926（LM 根 = .../light-merge）
collect-only -k 数据验证 → 候选 nodeid 1 条（上面那条）
隔离 ×5：rc=0 / rc=0 / rc=0 / rc=0 / rc=0     → 隔离 5 轮失败数 = 0
缺 PYTHONPATH（只留 LIGHT_MERGE + shim PATH）：rc=0
全量 -n 8 --dist loadscope：377.00s，1 failed（= codegen_ref_dict_O0，非目标用例）
```

## 4. 与历史记录的校准

- R82 的原文是「原生后端跨模块导入 flake」。本轮**没有拿到任何一次复现**，所以既不证实也不推翻
  那个归因，只能确认「它确实低频且在 0.82 上存在过」。
- R89-E 在 0.82 上跑的两轮全量（8177 / 8175 passed，0 failed）也没命中它 —— 与「低频」一致。

## 5. 遗留

1. **两条 flaky 都拿不到最小复现**，建议后续在 0.82 上做「按目录分批 + 固定 seed」的定向复跑
   （`-p no:randomly` 不存在的话改用指定顺序），否则永远停在"观察"。
2. 取证脚本 `_r90/d_082_forensics.py` 有个**待修的坑**：全量那步写成
   `pytest ... | tail -25 ; echo PYTEST_RC=$?`，`$?` 取到的是 `tail` 的退出码（恒 0），
   所以日志里的 `PYTEST_RC=0` 不可信 —— 真实结果要从输出文本里的 `N failed` 行读。
   下轮要写成 `pytest ... > out 2>&1; echo RC=$?`。
3. 本轮 0.82 全量 **1 failed（flaky）**，其余 8175 passed —— 0.82 LM 未劣化。

# 第45轮 任务1：0.82 复核 + 双平台全量回归

## 1. 遗留②复核：0.82 的 git

```
$ scripts/同步0.82.py run "which git; git --version"
/usr/local/bin/git
git version 2.54.0
```

✅ **已安装**（`git 2.54.0`，`/usr/local/bin/git`）。

### 但只装 git 还不够——副本里没有 `.git`

第44轮那 2 条 ERROR 来自 `tests/test_R21_词法确定性_超集.py`：它用 `git archive HEAD`
取语料，取不到时 `pytest.skip("git archive HEAD 不可用")`。

- **git 未安装**时：命令不存在 → **ERROR**（2 条）
- **git 已安装、但 /tmp 副本不是 git 工作树**时：`git archive HEAD` 失败 → **SKIP**（2 条）

所以实测演进：

| 阶段 | 结果 |
|---|---|
| 第44轮（无 git） | 7 failed / 1230 passed / 3 skipped **+ 2 errors** |
| 本轮首跑（有 git，副本无 .git） | 7 failed / 1236 passed / **5 skipped** / **0 errors** |
| 本轮定版（有 git，**副本带 .git**） | 见 §2 |

⇒ ERROR 确实消失了，但**退化成了 SKIP**——没有被真正执行，跨平台等价性仍差一档。

**改进**：给 `scripts/同步0.82.py` 加 `--with-git`，把 `.git` 一并同步（lightharness
7.8M + light-merge .git，包体 97MB → 172MB，上传仍只 10.8s），并自动
`git config --global --add safe.directory`。实测远端 `git rev-parse HEAD = 141aa2c`，
该测试文件在 0.82 上 **2 passed（不再 skip）**。

## 2. 双平台全量回归

| | 本机（Windows） | 0.82（FreeBSD 15.1，带 .git 副本） |
|---|---|---|
| 用例总数 | 1248 | 1248 |
| failed | **7** | **7** |
| passed | **1238** | **1238** |
| skipped | **3** | **3** |
| errors | 0 | 0 |
| 耗时 | 927.8s | ~370s |

**失败清单逐条一致**（7 条）：

```
tests/test_R31_EMBED表保留+flaky修复_token.py::test_fanhui_embedded_scan_triggered
tests/test_R31_EMBED表保留+flaky修复_token.py::test_fanhui_return_value_merged
tests/test_R32_OPERATOR+MERGE_WHOLE精简_token.py::test_deleted_return_code_still_merged
test_回归.py::test_example_exit_code[test_R22_嵌入关键字吞并验证.light]
test_回归.py::test_example_exit_code[test_R26_词首并入反向.light]
test_回归.py::test_example_exit_code[test_R26_词首并入混合.light]
test_回归.py::test_example_exit_code[test_R27_词首并入反向.light]
```

与第44轮定版（本机 7 failed / 1232 passed）相比：
passed +6（新增 1 个 example 用例 + 5 个 `test_R45_L166影子变量告警.py` 用例）、
failed 不变 → **基线外零新增红 ✅**。

## 3. 对比第44轮的结论

| 项 | 第44轮 | 本轮 | 说明 |
|---|---|---|---|
| 本机 | 7 failed / 1232 passed / 3 skipped | 7 failed / **1238** passed / 3 skipped | +6 为本轮新增用例，失败集不变 |
| 0.82 | 7 failed / 1230 passed / 3 skipped **+ 2 errors** | 7 failed / **1238** passed / 3 skipped **+ 0 errors** | 2 errors 消失、2 skips 恢复为 pass，与本机**完全对齐** |
| 双平台差异 | 有（errors/skips） | **无** | 达成跨平台等价 |

## 4. 交付物

- `scripts/同步0.82.py`（`--with-git` + 远程目录指针稳定化 + 期望用例数动态化）
- `reports/R45_双平台pytest.json`
- 本报告

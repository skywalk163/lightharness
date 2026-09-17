# 第55轮任务3交付：本机 lightharness 全量基线固化

> 日期：2026-09-18 ｜ 目标：本机 Windows 上 lightharness 全量 pytest 基线固化，作为**快速回归门**判据
> 交付物：`reports/本机lh基线_2026-09-18-003014.json`（+ `latest` 指针）、`_本机lh_results_2026-09-18-000509.xml`
> 铁律遵守：只跑验证，**未改任何源码 / 未改任何用例**

---

## 一、基线数字（固化）

| 项 | 数值 |
|---|---|
| 平台 | 本机 Windows 10，`light-merge/.venv` Python 3.13.14 |
| 命令 | `-m pytest tests/ -q --tb=no -rfE -o addopts= -p no:cacheprovider -p no:xdist --timeout 60` |
| 用例总数 | **1272** |
| 通过 | **1262** |
| 失败 | **7**（0.55%） |
| 跳过 | 3 |
| 耗时 | pytest 自报 **1493.96s（24:53）** |

> ⚠️ **纠正任务书里的一个数字**：任务书说本机 lightharness 全量「6-7 分钟」，实测 **25 分钟**。
> 后续排回归时间按 25 分钟算，别按 7 分钟排。

### 失败清单（7 条，全部计入基线）

| # | 用例 | 失败信息 |
|---|---|---|
| 1 | `test_R31_EMBED表保留+flaky修复_token.py::test_fanhui_embedded_scan_triggered` | `assert '返回表' in ['设','x','为','返回','表',None]` |
| 2 | `test_R31_...::test_fanhui_return_value_merged` | `assert '返回值' in ['设','x','为','返回','值',None]` |
| 3 | `test_R32_OPERATOR+MERGE_WHOLE精简_token.py::test_deleted_return_code_still_merged` | `assert '返回码' in ['设','x','为','返回','码',None]` |
| 4 | `test_回归.py::test_example_exit_code[test_R22_嵌入关键字冗余验证.light]` | 应绿，实际 rc=1 |
| 5 | `test_回归.py::test_example_exit_code[test_R26_词首并入反向.light]` | 应绿，实际 rc=1 |
| 6 | `test_回归.py::test_example_exit_code[test_R26_词首并入混合.light]` | 应绿，实际 rc=1 |
| 7 | `test_回归.py::test_example_exit_code[test_R27_词首并入反向.light]` | 应绿，实际 rc=1 |

这 7 条是**当前欠账**，已写入基线；之后每轮只拦「基线之外的新红」。

---

## 二、怎么复现 / 怎么守这个门

```bash
cd G:/dswork/duan-light-merge/lightharness
PY="G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe"

# 重跑一遍并刷新基线（~25 分钟）
$PY scripts/多平台矩阵.py --mode gate --local-only

# 已经有了 junitxml、只想重算基线和 diff（秒级，调脚本时用）
$PY scripts/多平台矩阵.py --mode gate --local-only --local-xml reports/_本机lh_results_2026-09-18-000509.xml
```

判据：**新增红（本轮失败集合 − 基线失败集合）= ∅ 才 rc=0**。
首次跑（没有历史基线）会把失败原样记为基线并通过，不会造成「第一跑必红」。

一个必须记住的坑：`-o addopts=` 会连同 `pytest.ini` 里的 **`--timeout=60`** 一起清掉，
而 `test_回归.py` 里有真实网络/服务器类 example，没有单用例超时会整轮 hang 住
（本轮实测：跑到 84% 卡了 8 分钟不动）。所以脚本里在 `-o addopts=` 之后**显式补回 `--timeout 60`**。

---

## 三、与 0.82 侧基线的差异（两套不同的套件）

| 侧 | 套件 | 用例数 | 失败 | 失败率 | 耗时 |
|---|---|---|---|---|---|
| 本机 Windows 10 / py3.13 | lightharness | 1272 | 7 | 0.55% | 24:53 |
| 0.82 FreeBSD 15.1 / py3.11 | light-merge | 7806 | 117 | 1.50% | 25:17 |

两者是**不同套件**（按设计分工：本机跑 harness，0.82 跑语言本体），所以不能用「同一套用例互相 delta」。
真正有意义的是**同源项跨平台核对**，见下节。

---

## 四、同源项跨平台核对（真做了，不是嘴上说）

把本机那 7 条红搬到 0.82 上逐个复跑（`_r55_probe082e.py`），结果分成两类：

### 4.1 共有红（3 条，非平台差异）

```
0.82: 3 failed in 0.19s
E AssertionError: assert '返回表' in ['设','x','为','返回','表',None]     ← 与本机一字不差
E AssertionError: assert '返回值' in ['设','x','为','返回','值',None]
E AssertionError: assert '返回码' in ['设','x','为','返回','码',None]
```

→ 这 3 条在 Windows 与 FreeBSD 上**行为完全一致**，是词法层的共有缺陷：
`返回` 在 `_EMBED_MAX_MATCH_KEYWORDS` 里，`设 x 为 返回值` 被切成 `['设','x','为','返回','值']`，
「后置合并不生效」（与语言缺陷账里的 L-155 嵌入块吞并同源）。**与平台无关。**

### 4.2 平台差异（4 条，Windows 红 / 0.82 绿）

| example | 本机 Windows rc | 0.82 FreeBSD rc |
|---|---|---|
| test_R22_嵌入关键字冗余验证 | 1 ❌ | 0 ✅ |
| test_R26_词首并入反向 | 1 ❌ | 0 ✅ |
| test_R26_词首并入混合 | 1 ❌ | 0 ✅ |
| test_R27_词首并入反向 | 1 ❌ | 0 ✅ |

**排除了一个想当然的解释**：不是 CRLF 行尾。本机工作树 `core.autocrlf=true`（工作树 CRLF / blob LF），
0.82 副本解包后是 LF —— 但把同一个文件分别按 CRLF / LF 在本机各跑一遍（`_r55_probe_crlf.py`）：

```
test_R22_嵌入关键字冗余验证  原样rc=1  CRLF rc=1  LF rc=1
test_R26_词首并入反向        原样rc=1  CRLF rc=1  LF rc=1
test_R26_词首并入混合        原样rc=1  CRLF rc=1  LF rc=1
test_R27_词首并入反向        原样rc=1  CRLF rc=1  LF rc=1
```

四种形态全红，行尾不是变量。**尚未隔离的两个候选**（本轮未继续深挖，如实登记）：

1. **解释器版本**：本机 py3.13.14 vs 0.82 py3.11.16 —— light-merge 声明支持 ≥3.10，存在版本行为差的可能；
2. **OS / 路径差异**：0.82 副本根目录是 `/tmp/r44-…/lightharness`，本机是 `G:\dswork\...`，
   Light 模块解析顺序为 SRC>ROOT>STDLIB，ROOT 不同可能命中不同模块或不同分支。

隔离办法（本轮未做）：在 0.82 上装一个 3.13，或者在本机装一个 3.11 跑同一批 example。
→ **登记待办**，不臆断归因。

---

## 五、遗留 / 待办

1. 上面 §4.2 的 4 条平台差异归因未隔离（候选：py3.13 vs py3.11 / OS 路径）。
2. lightharness 侧**没有** `-m slow` 标记，1272 条是全跑的；如果后续想再压时间，
   需要先给慢 example 打标记（本轮没做，因为要动 `-m`，属于改配置不是改源码）。
3. 本机 25 分钟的耗时主要花在 `test_回归.py` 的 example 逐个拉起 cdm 编译器；
   真正的加速空间在给 0.82 装 xdist 之后跑 light-merge，本机这条腿暂时就这个价。

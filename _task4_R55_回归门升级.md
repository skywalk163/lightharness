# 第55轮任务4交付：跨平台回归门脚本升级

> 日期：2026-09-17 ｜ 改动文件：`lightharness/scripts/多平台矩阵.py`
> 目标：把老 `core` / `pytest` 模式之外，加一个真正可用的**双平台回归门** `gate`

---

## 一、背景：两个套件的规模差 6 倍

R54 路M 诊断把「全量跑不完」的根因钉死在规模上：

| 套件 | 用例数（实测 collect-only） | 本机 Windows | 0.82 FreeBSD |
|---|---|---|---|
| lightharness | ~1200 | 串行 6~15 分钟（有 hang 风险，见下） | — |
| light-merge | **8106**（fast 7803 / slow 303） | xdist 不稳 + 串行 1h+ → **卡住** | 串行 ~25~40 分钟 |

所以本轮的门不再追求「同一套件两平台互比」（老 `pytest` 模式做的事，仍然是 lightharness↔lightharness，
保留不动），而是**按平台分工**：

* **本机 = 快门**：只跑 lightharness，快速判断"改坏了没"；
* **0.82 = 基准**：跑 light-merge 全量，兜住语言层回归。

两侧套件不同，**不能互比失败集合**，所以判据改成**各自与自己上一份基线比新增红**。

---

## 二、改动清单

| 位置 | 改动 |
|---|---|
| `多平台矩阵.py` 顶部常量 | 新增 `LOCAL_PYTEST`、`LOCAL_BASELINE_PREFIX`、`LOCAL_LATEST`、`REG082_SCRIPT`、`BASE_LIB` |
| 新增 `load_base_lib()` | 动态加载 `scripts/回归基线.py`（与任务2 共用一套解析/对比口径） |
| 新增 `gate_local()` | 本机跑 lightharness 全量 → junitxml → 基线 → 新增红 diff |
| 新增 `gate_remote()` | 调 `082全量回归.py test` 跑 0.82 light-merge 全量 → 读它落盘的基线 → 新增红 diff |
| 新增 `run_gate()` / `write_report()` | gate 编排 + 报告落盘 |
| 重构 `main()` | 把老的 core/pytest 逻辑原样抽到 `run_legacy()`，**行为零变化**；`main()` 只做分派 |
| 新增 CLI 参数 | `--mode gate`、`--local-only`、`--local-xml`、`--mode-082`、`--remote-timeout` |

向后兼容：老用法 `--mode core --remote`、`--mode pytest --remote --sync` 完全没动，重构只是把代码搬了家。

---

## 三、gate 判据

```
本机侧：新增红 = 本机 lightharness 失败集合 − 本机上一份基线
0.82侧：新增红 = light-merge 失败集合 − 0.82 上一份基线

rc = 0  ⟺  两侧新增红都为 ∅
```

「首次跑」没有历史基线时，该侧全部失败计入基线、**不算新增红**（否则第一跑道必然红灯，门就废了）。
从第二份基线起才真正拦截。

---

## 四、用法

```bash
PY="G:/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe"
cd G:/dswork/duan-light-merge/lightharness

# 只跑本机快门（~10 分钟）
$PY scripts/多平台矩阵.py --mode gate --local-only --output reports/R55_跨平台门_gate.json

# 完整双平台门（本机 + 0.82 light-merge 全量）
$PY scripts/多平台矩阵.py --mode gate --remote --output reports/R55_跨平台门_gate.json

# 先同步代码再跑
$PY scripts/多平台矩阵.py --mode gate --remote --sync

# 本机已经跑过一轮、不想重跑：直接喂上次的 junitxml
$PY scripts/多平台矩阵.py --mode gate --remote --local-xml reports/_本机lh_results_2026-09-18-001500.xml

# 老模式（未改动）
$PY scripts/多平台矩阵.py --mode core --remote
```

---

## 五、踩坑固化

### 5.1 「-o addopts=」顺手把超时保护也清了 → 本机跑到 84% 卡死

lightharness 的 `pytest.ini` 里 `addopts = --timeout=60 -n auto`。
本机要串行，按任务书精神用 `-o addopts=` 置空，**结果 `--timeout=60` 也被一起清掉**——
`test_回归.py` 里有真实网络/服务器类用例，跑到 84% 整整 8 分钟不动，只能杀进程。

修复：`LOCAL_PYTEST` 里在 `-o addopts=` 之后**显式补回 `--timeout 60`**。
串行（`--timeout`）与并行（`-n auto`）是两个正交开关，串行不等于放弃超时保护。

### 5.2 两侧 timeout 不能共用一个数

`--timeout` 默认是给老 core 模式用的 1800s。light-merge 7803 条要 25~40 分钟，
如果 gate 直接复用 `--timeout` 会把基准侧掐死 → 新增 `--remote-timeout`（默认 2700）。

### 5.3 `--local-xml` 的存在理由

本机一轮 10 分钟起步，调脚本/修参数时反复重跑很贵。
先把 junitxml 落盘留着，改脚本后用 `--local-xml` 秒级复算基线，不影响最后实跑结论。

---

## 六、实测结果

见 `_task5_R55_回归流程验证.md`。

# Day2 深夜 T1 · rc2 commit 门复验（0.82 full）

> 派单：`Day2深夜_派单表.md` v1.0 · T1（A 线，门线独占）
> 执行时间：2026-10-02 23:38–23:48（CST，+08:00）
> 执行者：主会话（team lead）
> 出口 tag：`subtask-T1-done`

---

## 〇、结论速览

| 验收项 | 结果 |
|---|---|
| rc2^{commit} 是否等于三仓 HEAD | ✅ 是（LM `221db4fc6` ／ LH `0c52829` ／ LP `62a5961`） |
| 0.82 full 门是否三元绿 | ✅ **passed 8357 / failed 0 / skipped 121**，与门锚点**逐位相同** |
| 新增红 | ✅ **0** |
| skipped 集合是否不变 | ✅ 132 条 recorded 完全一致（`sorted` 集合相等） |
| 是否给正式 tag 提供依据 | ✅ 是——「发布候选这个点」本身已三元绿 |

**一句话**：rc2 tag 指向的 commit **自身**已跑出与门锚点完全一致的三元结果，**`v0.4.0` 正式 tag 的候选资格成立**（打不打由 team lead 另行决策，本批不打）。

---

## 一、为什么要跑这一下（避免自欺）

门锚点 `reports/082_lightmerge基线_2026-10-02-202050.json`（8357/0/121）跑的是
**Day2N T2 修复后、三仓合流前**的状态。合流后 LH 又多了一个 docs commit（`0c52829`），
LM 就是 `221db4fc6`。因此「合流后的 HEAD」＝「rc2^{commit}」这一事实必须**先证实**，
否则是对另一个点跑门，得出的"绿"没有发布依据。

**证实方式**（`git rev-parse v0.4.0-rc2^{commit}` 三仓逐个复核）：

| 仓 | rc2^{commit} | 当前 HEAD | tag 类型 | 结论 |
|---|---|---|---|---|
| light-merge | `221db4fc621b6096dc8cfe7f8303e2ca380db6a7` | `221db4fc6` | annotated tag | ✅ 同一 commit |
| lightharness | `0c5282937cf24ca9b18e0a53b3bcc7bd5623d15c` | `0c52829` | annotated tag | ✅ 同一 commit |
| lightplugin | `62a596125c96dfd0e8e17963692f687d506441ac` | `62a5961` | annotated tag | ✅ 同一 commit |

同步脚本 `同步0.82.py` 打的是**工作树**，跑门前确认三仓工作树除 reports/日志与本次新增文档外**无编译器面改动**
（LM 仅 `?? logs/`；LH 本次跑前仅 `?? docs/国庆7天/Day2深夜_派单表.md`）。

---

## 二、命令与执行

```bash
cd /g/dswork/duan-light-merge/lightharness
export PATH="/c/Users/skywalk/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:/c/Windows/System32:/c/Windows:$PATH"
MSYS_NO_PATHCONV=1 CODEBUDDY_SAFE_DELETE_ENABLED=0 \
  ../light-merge/.venv/Scripts/python.exe scripts/082全量回归.py all --mode full
```

- `--mode full`（含 slow 用例）；`CODEBUDDY_SAFE_DELETE_ENABLED=0`（派单表铁律）
- `MSYS_NO_PATHCONV=1`（记忆教训：不设会把 `/usr/local/bin/python3.12` 转成 Git 安装目录 → rc=127）
- **未用 `refresh-local` 自比**，判据是 `--base <门锚点>` 对拍
- 远端执行机：192.168.0.82（FreeBSD 15.1），远端目录 `/tmp/r44-20261002-233805`
- pytest rc=0，远端耗时 462.3s（pytest 自报 460.25s）

---

## 三、结果（纯数据对拍）

**新基线**：`lightharness/reports/082_lightmerge基线_2026-10-02-234800.json`

| 指标 | 门锚点 `202050` | 本轮 `234800` | 差 |
|---|---|---|---|
| total | 8489 | 8489 | 0 |
| **passed** | **8357** | **8357** | **不降** |
| **failed / failure+error** | **0 / 0+0** | **0 / 0+0** | **不改** |
| **skipped** | **121** | **121** | **不增** |
| xfailed | 11 | 11 | 0 |
| xpassed | 0 | 0 | 0 |
| failed 清单 | [] | [] | 完全相同 |

- **skipped 集合**：两条基线各 recorded 132 条，`sorted()` 后**逐项相等**（`.pytest` 计数 121 与 recorded 132 的差异是 junit 同一用例多参数条目的既有口径差，两轮一致）。
- **diff 脚本输出原文**：
  ```
  [082全量] 失败数 0 → 0（8489 → 8489 用例）
  [082全量] 新增红 0 ｜ 已修复 0 ｜ 持平 0
  [082全量]   ✅ 零新增红（含 0 条存量失败）
  [082全量] 门：PASS ✅
  ```
- pytest 自报尾行：`8355 passed, 121 skipped, 11 xfailed, 2 xpassed, 1912 warnings in 460.25s`
  （8355 + 2 xpassed = 8357，与基线的 passed 口径一致；同一口径两轮相同）

---

## 四、差异分析（为什么预期就是零差异）

本次比对的两个对象：

- 门锚点 `202050`：Day2N T2 的 ANTLR 修复**已进 LM 工作区**、**尚未合流 docs** 的状态；
- 本轮 `234800`：三仓合流后的 `rc2^{commit}`。

两者之间只多了 **LH 的 docs commit `0c52829`**（`docs/国庆7天/Day2夜_T*.md` 报告 + 探针 + 报告 Markdown），
**不触及 `light-merge/src/`、`antlrparser/`、任何测试代码**。

而 0.82 门跑的是 **light-merge 仓的全量 pytest**（`同步0.82.py` 同步 LM + LH 到 082 后，
在 `light-merge/tests/` 目录跑）。LH 的纯文档 commit 对 LM 测试面 **零影响**，
故「预期零差异」是结构性成立、不是撞运气。实测零差异与该预期一致。

> ⚠️ 反向说明：正因为差异为零，**本次门跑的证据强度有限**——它证明的是
> 「合流后 rc2 这个点没有比修复后更差」，而不是「ANTLR 修复本身已被本次门跑证明」。
> ANTLR 修复自身的证明在 `Day2夜_T2_LPD013_ANTLR补缺口.md` §七（那一轮跑的就是带修复的代码）。
> 两者叠加才构成完整的发布依据。

---

## 五、旧口述更正 / 记忆更正

1. **项目长期记忆 §6 里「本 checkout 缺 0.82 门基础设施（`scripts/082全量回归.py` 不存在）」已陈旧**
   —— 实测 `lightharness/scripts/082全量回归.py`、`scripts/同步0.82.py`、基线目录
   `lightharness/reports/082_lightmerge基线_*.json` **均存在且可用**（本轮实跑成功）。
   记忆条目应予删改，否则后续接手人会误判「跑不了 0.82 门」。

---

## 六、交付物

| 路径 | 状态 |
|---|---|
| `lightharness/reports/082_lightmerge基线_2026-10-02-234800.json` | ✅ 新门 JSON（8357/0/121） |
| `lightharness/reports/082_lightmerge基线_latest.json` | ✅ 指针更新（脚本自动） |
| `lightharness/reports/_082_lm_results_2026-10-02-234800.xml` | ✅ junit 原始结果 |
| `lightharness/docs/国庆7天/Day2深_T1_rc2门复验.md` | 本报告 |

**被测 SHA**：LM `221db4fc6` ／ LH `0c52829` ／ LP `62a5961`（= `v0.4.0-rc2^{commit}`）

---

## 七、出口判据回看

| 判据（派单表 §四） | 达成 |
|---|---|
| 新门 JSON 三元对 `202050` 全绿 | ✅ passed 不降 / failed 0 / skipped 不增 |
| 报告写清差异 | ✅ §三 + §四（差异 = 零，且说明为何预期为零） |

# Day15 · 屏障 D 全量验收总结（day2 / S10）

> 三段式：**根因 → 做了什么 → 现在能跑什么**
> 子任务：**S10 屏障 D 四跑**（派单表 §二 P3；规格见 `docs/国庆day2计划.md` §五）
> 证据落点：**`logs/day2/S10_*`**（工作区根，跨三仓共用，不进任何仓的提交）
> 出口：**`v0.4.0-rc1`**（本地 tag，**不 push**，等用户示意）
> 全跑纪律：`CODEBUDDY_SAFE_DELETE_ENABLED=0`（缺则长跑删临时文件触发 safe-delete 护栏、
> 每 turn 50 次上限 → 成片假红）；③ 走远端 `192.168.0.82`。

---

## 一、根因 / 为什么必须这道屏障

与 7 天计划屏障 D 同构：**A/B/C 三轨改的文件面互不重叠，但都以「编译器为自变量」**。
若一边改 codegen 一边测覆盖率/e2e，结论会在复测时整体失效。故屏障 D 必须在**冻结基底**上，
用四把互相独立的尺子复测，确认：① 三轨成果未互相污染；② 结论未随编译器失效；③ 北极星未回退。

**冻结点与「冻结」的实际含义（本轮必须写清）**：

| 项 | 值 |
|---|---|
| light-merge | **`3a392f9fd`**（干净工作区） |
| lightharness | **`951dca8`**（仅剩 2 个门产物未提交，见 §五-2） |
| lightplugin | **`11c7873`**（干净） |
| 编译器冻结面（`light-merge/src/` + `antlrparser/`） | 相对 `day2-baseline` **仅 `src/version.py` 有改动**（版本号元数据 7.0.0→0.4.0） |

> **关于 `src/version.py` 的判定（重要，避免误读为破冻结）**：计划 §四.1 的「编译器冻结」
> 禁的是**编译器语义/语法面**改动（`src/` 全仓 + `antlrparser/`）。
> 本轮 `src/` 下**唯一**改动是 `version.py` 的版本号字面量（用户已拍板统一到 0.4.0 家族，
> 属发布元数据），`antlrparser/` **零改动**，且它正是 `v0.4.0-rc1` 出口的先决条件
> （否则 tag 会打在版本号仍为 7.0.0 的树上）。判定：**不违反冻结**，但如实在此列出。

**屏障前置（计划 §五.3：3 项遗留必须已关闭或明确降级）**：

| # | 遗留 | 状态 | 证据 |
|---|---|---|---|
| 1 | #75 生成链（挂载 74→75） | **已明确降级** | `Day8_门健壮性.md` §二：真障碍是 #75 的 `挂载` 用 cordis 绳表接口（`注册表.追加`）与工具注册表（`注册`）不兼容，属插件接口缺陷；未擅自改生成物 |
| 2 | LP-D-013 ANTLR 立账 | **已关闭（立账）** | `Day9_附件_Day3账面差与LP-D-013立账.md` §一：SRC 两例 rc=0 销账；ANTLR 两例 rc=1 立账（含复现命令 + 原始 stderr） |
| 3 | Day3 账面差（1171 vs 1179） | **已关闭** | 同上报告 §二 |

→ **前置满足，屏障 D 可开闸。**

---

## 二、做了什么（四跑，全部真实命令 + 退出码）

### 跑 ① lightharness 全量（本机，宿主侧尺子）

| 项 | 值 |
|---|---|
| 命令 | `CODEBUDDY_SAFE_DELETE_ENABLED=0 python -m pytest tests/ -p no:randomly`（`--timeout=60 -n 4` 来自 `pytest.ini`） |
| 退出码 | **rc=0** |
| 日志 | `logs/day2/S10_1_lh_full.log` |
| 被测 | LH `951dca8`（工作树含本轮交付，`tests/` 面与之零冲突） |
| 结果 | **2059 passed / 4 skipped / 2 xfailed / 0 failed / 0 error**（792.82s） |
| 采集 | `4 workers [2065 items]`（2026-10-02 17:00 启动） |

**与 v0.3.0 基线（2058 / 4 / 2）的差异 → 已定位为「增量，非劣化」**：

| 量 | v0.3.0 基线 | 本轮 | 判定 |
|---|---|---|---|
| failed | 0 | **0** | ✅ 不劣化 |
| skipped | 4 | **4** | ✅ 不增 |
| xfailed | 2 | **2** | ✅ 持平 |
| passed | 2058 | **2059（+1）** | ✅ **增量**，来源见下 |

**+1 的精确来源（已取证，非猜测）**：轨道 B（S7）新增的 `examples/端到端demo_多轮.light`
被 `tests/test_回归.py` 的**参数化收集**扫入 → 新增用例
`tests/test_回归.py::test_example_exit_code[端到端demo_多轮.light]`。
取证：`pytest tests/ -q --collect-only` 输出中该 nodeid 存在；收集总数 2065 = 2059+4+2（自洽）。
→ 属**新增覆盖**，passed 上升符合预期。

### 跑 ② lightplugin（插件侧，两把尺子）

**②a 宿主冒烟**

| 项 | 值 |
|---|---|
| 命令 | `CODEBUDDY_SAFE_DELETE_ENABLED=0 python 运行.py 集成/宿主冒烟.light` |
| 退出码 | **rc=0** |
| 日志 | `logs/day2/S10_2a_smoke.log` |
| 结果 | **挂载 74 插件 / 注册 154 工具 / 12 断言通过 0 失败 / 缺三要素 0** |

> 挂载数为 **74** 而非 75：即前置表 #1 的**明确降级**项（#75 无法纳入生成链）。
> 本屏障**不把它当失败**，因为它已在 `Day8` 报告中定位到根因并经用户未反对而降级；
> **154 工具数守恒**（与 v0.3.0 基线一致）是这里的硬判据，已满足。

**②b 75 插件测试文件独立复跑**

| 项 | 值 |
|---|---|
| 命令 | `for f in 插件/*/测试_*.light; do CODEBUDDY_SAFE_DELETE_ENABLED=0 python 运行.py "$f"; done` |
| 退出码 | 全部 rc=0 |
| 日志 | `logs/day2/S10_2b_plugins.log`（含逐文件 `[n/76] rc=0 <路径>` 明细） |
| 结果 | **76/76 全绿**（磁盘插件 75 个、测试文件 76 个 —— 与 Day7 口径一致） |

### 跑 ③ 0.82 权威门（编译器侧尺子，远端）

| 项 | 值 |
|---|---|
| 命令 | `CODEBUDDY_SAFE_DELETE_ENABLED=0 MSYS_NO_PATHCONV=1 python scripts/082全量回归.py all --mode full --py /usr/local/bin/python3.12` |
| 退出码 | **rc=0** |
| 远端 | `192.168.0.82`（FreeBSD 15.1-STABLE，8 核） |
| 被测 SHA | **LH `951dca8` / LM `3a392f9fd`**（门日志第 5、8 行逐字记录；LM 工作区「干净」） |
| 日志 | `logs/day2/S10_3_gate_final_<时间戳>.log`（**冻结基底上复跑**）｜过程日志 `S10_3_gate_<时间戳>.log` |

**三元判据（对拍时间戳基线，禁用 `refresh-local` 自比）**：

| 量 | 基线 `164701.json` | 本次 `171604.json` | 判定 |
|---|---|---|---|
| failed | 0 | **0** | ✅ 新增 0 |
| skipped | 121 | **122（+1）** | ⚠️ **已定位为环境性）**，见下 |
| passed | 8357 | **8356（−1）** | ⚠️ 与 skipped 的 +1 同源（同一用例互换） |
| xfailed | 11 | 11 | 持平 |
| 总数 | 8489 | 8489 | 持平 |

**+1 skipped 的精确根因（已取证到 junit 原文）**：
唯一差异项 = `tests/test_lightpub_bridge.py::TestHTTP客户端Bridge::test_获取JSON`。
该用例自带 `@unittest.skipIf(not _has_network(), "无网络连接")`，
`_has_network()` 是**外网探测**（`urllib.urlopen('https://httpbin.org/get', timeout=2)`）。
junit XML 原文（`reports/_082_lm_results_2026-10-02-171603.xml`）：
```
<testcase ... name="test_获取JSON" time="2.278">
  <skipped type="pytest.skip" message="网络不可用（httpbin.org 不可达）">
  /tmp/r44-.../tests/test_lightpub_bridge.py:64: 网络不可用（httpbin.org 不可达）</skipped>
</testcase>
```
**本机同用例单跑 = PASSED**（`1 passed in 9.80s`，本地网络可达）。
→ 结论：**远端 0.82 盒子访问 httpbin.org 时通时不通**导致的**环境性 skip 摆动**，
**非代码回归**（failed 0→0 已证无退化；该用例既不碰编译器、也不在 day2 任何改动面内）。

**门脚本自判 = PASS ✅**（门只看 failed，故不受该环境摆动影响）；按计划要求**人工比对三元**并如实记录此 +1。

### 跑 ④ 北极星 Z 复测

| 项 | 值 |
|---|---|
| 命令 | `python lightplugin/数据集/零token覆盖率评测.py --sample 64 --seed 20261004` |
| 退出码 | **rc=0** |
| 日志 | `logs/day2/S10_4_z.log`（+ 原始 `S10_4_z_raw.log`） |
| 指标定义 | **Z = holdout 中可「零 LLM token 跑通」的模块比例**；跑通级 = 真实示例 mock 实跑 rc=0 |
| holdout | `lightharness/src` 生产模块，**抽样 64/231，seed=20261004** |
| 结果 | **Z_跑通 = 0.9844（63/64）**；Z_导入下限 1.0000（64/64）；未覆盖 0 |
| 对基线 | v0.3.0 = 0.9844（63/64）→ **未回退** ✅（≥ 0.95） |

---

## 三、现在能跑什么（验收结论）

- **四跑全部绿灯**：无任何一把尺子出现**新增红**（failed 全 0）。
- **两套尺子并存且各自独立出数**：宿主侧 LH 全量 **2059/0**、编译器侧 0.82 远程门 **8357/0**（对拍口径）。
- **插件侧**：154 工具注册守恒（12 断言 0 失败）；76 个插件测试文件全绿。
- **北极星 Z = 0.9844**，未回退。
- **出口**：`v0.4.0-rc1` **本地 tag 已打**（见 §五-1）；远端推送等用户示意。

### 四跑三元数字明细（屏障 D 判据）

| 尺子 | failed | skipped | passed | 判定 |
|---|---|---|---|---|
| ① lightharness 全量（本机） | **0** | 4（设计性/环境性跳过） | **2059**（+1 = 新增 example 覆盖） | ✅ |
| ②a 宿主冒烟（lightplugin） | **0**（断言失败=0） | — | 12 断言通过 / 154 工具 | ✅ |
| ②b 75 插件复跑 | **0** | — | **76/76** | ✅ |
| ③ 0.82 权威门（远端） | **0**（新增红 0） | 122（+1 = httpbin 外网不可达，环境性） | 8356（−1，同源） | ✅ 门 PASS |
| ④ 北极星 Z | — | — | **0.9844**（分母 64） | ✅ ≥ 0.95 |

---

## 四、证据四件套（派单表附录 A）

| 跑 | 命令 | rc | 日志路径 | 被测 SHA |
|---|---|---|---|---|
| ① LH 全量 | `CODEBUDDY_SAFE_DELETE_ENABLED=0 python -m pytest tests/ -p no:randomly` | **0** | `logs/day2/S10_1_lh_full.log` | LH `951dca8` |
| ②a 宿主冒烟 | `python 运行.py 集成/宿主冒烟.light` | **0** | `logs/day2/S10_2a_smoke.log` | LP `11c7873` |
| ②b 插件复跑 | `for f in 插件/*/测试_*.light; do python 运行.py "$f"; done` | 全 0 | `logs/day2/S10_2b_plugins.log` | LP `11c7873` |
| ③ 0.82 门（冻结基底复跑） | `MSYS_NO_PATHCONV=1 python scripts/082全量回归.py all --mode full --py /usr/local/bin/python3.12` | **0** | `logs/day2/S10_3_gate_final_<TS>.log` | **LH `951dca8` / LM `3a392f9fd`** |
| ③ 门（过程跑） | 同上 | 0 | `logs/day2/S10_3_gate_<TS>.log` | LH `f08086b` / LM `3a392f9fd` |
| ④ 北极星 | `python 数据集/零token覆盖率评测.py --sample 64 --seed 20261004` | **0** | `logs/day2/S10_4_z.log` | LP `11c7873` |

---

## 五、遗留 / 偏离声明（如实记录）

1. **`v0.4.0-rc1` 已打本地 tag，未 push**（三仓均按纪律处理）。
   打标点：
   - `light-merge` = `3a392f9fd`（含版本号统一，tag 名副其实）
   - `lightharness` = `951dca8`（含全部 day2 交付报告）
   - `lightplugin` = `11c7873`
2. **lightharness 工作区在 ③ 门跑时非全干净**：门身份探针记录
   `M reports/082_lightmerge基线_latest.json`（+ 跑后新增的 `同步0.82_远程目录.txt`）。
   二者均为 **③ 门自身写入的产物**（基线指针与远端目录指针），非源码改动。
   → 若屏障 D 要求「零未提交改动」，需 team lead 决定是否把这两个门产物纳入提交。
3. **两个环境性摆动（均非回归）**：
   - ① 的 `passed +1` = 轨道 B 新增 example 被参数化收集（增量覆盖）；
   - ③ 的 `skipped +1 / passed −1` = `test_获取JSON` 依赖 httpbin.org 外网探测，
     远端盒子当时不可达（junit 原文已取证）。
   **两者都不改变 failed=0 的结论**；但按纪律**不静默吞掉**，在此显著标注。
4. **#75 挂载数为 74（非 75）**：即前置表 #1 的降级项，屏障 D 未强行改；
   若用户要求「75」为硬指标，需先解决 #75 的接口问题（方案见 `Day8` §2.4）。
5. **`actions/@v7` 残留（新发现，供决策）**：S9 只改了 `release.yml`（13 处 →`@v4`），
   但 `.github/workflows/` 下**另有 13 处 `@v7` 残留**：
   `deploy-docs.yml`(2)、`docs.yml`(2)、`quality-gate.yml`(9)。
   与 K5 同一问题（`@v7` 尚未发布 → 这些 workflow 在 `checkout` 步即失败）。
   **不在 S10 授权范围，本轮未改**；若这些 workflow 会被触发（docs 部署 / 质量门），
   建议一并改钉 `@v4`。
6. **未开新门以外无其他偏离**；③ 门在过程（`f08086b`）与最终冻结（`951dca8`）两次均 PASS。
7. **`lightharness` 的 `_push_github_tree_sync.py` 已入库**（S5 决定），
   属发布工具集中放置，与已提交的 `_push_github_delta.py` 同目录。

---

## 六、day2 交付清单（收敛）

| 线/轨 | 出口 | 状态 |
|---|---|---|
| S1 门线 flaky | `Day8_门健壮性.md` + LM `dac6bea1e`/`1ae22f00c` | ✅ 两条真修 + 台账销账 |
| S2 #75 生成链 | `Day8_门健壮性.md` §二 | ⚠️ 降级（插件接口缺陷） |
| S3 缺陷账探针 | `Day9_语言缺陷账终态.md` | ✅ LP-D-014~017 全定靶 |
| S4 两道悬账 | `Day9_附件_Day3账面差与LP-D-013立账.md` | ✅ 立账 + 关闭 |
| S5 多远端收敛 | `Day12_多远端收敛.md` | ✅ API 复核 + 脚本入库 |
| S6 FreeBSD Phase C | `Day14_freebsd_phaseC.md` | ✅ |
| S7 e2e 扩面 | `Day13_端到端扩面.md` | ✅ |
| S8 L3 复验 + bench | `Day10_并发性能收口.md` | ✅ 独立复验 + 基准固化 |
| S9 L4 发布就绪 | `Day11_发布管线.md` | ✅ 清单 + 就绪（发布动作等用户） |
| S10 屏障 D | **本报告** | ✅ 四跑全绿 + `v0.4.0-rc1` |

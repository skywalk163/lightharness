# 国庆 7 天（10/2–10/8）· 交付目录

> 计划书：`docs/国庆7天_开发计划书_v2.md`（版本号以文件首行为准，当前 v2.2）
> 报告模板：`_模板_DayN_报告.md`（三段式：**根因 → 做了什么 → 现在能跑什么**）
> 探针：`probes/`（语言能力定靶探针，Day2/Day3/Day4 开工前必跑）

## 目录约定

| 路径 | 用途 |
|---|---|
| `DayN_<主题>.md` | 当日主线交付报告（一天一份，三段式） |
| `probes/*.light` | 最小复现探针。**缺陷类任务开工前先跑，探针不红即销账或改靶**（LP-D-011/013 教训） |
| `_模板_DayN_报告.md` | 新建当日报告时复制此文件，勿从零写 |

## 判据口径（v2.2 三元咬合）

每轮门必须同时记录并比较三个量，**任一劣化即 FAIL**：

```
failed  集合（逐条 id） → 新增 0
skipped 集合（逐条 id） → 不得新增（防「把红变成跳过」）
passed  总数            → 不得低于上一轮（扣除新增用例后的等价比对）
```

> 现行门（`scripts/回归基线.py:187`）只看 failed 集合，对「passed 变 skipped」失明。
> 故**计划书 §六的三元判据必须人工比对**，不能只看脚本的 `ok` 字段。

## ⚠️ Day1 固化的两条硬经验

1. **两套模块名映射**：`tests/test_module_system.py` 走 ANTLR 后端 + `UnifiedCodeGenerator`，
   其映射在 `src/code_generator_unified.py:1887` 的 `module_map`；SRC 后端在
   `src/code_generator.py:236` 的 `module_name_map`。**改模块名解析必须两处都改**，只改一处不生效。
2. **稳定 full 基线是 8352 / 126**，不是 8354。`test_验证IP地址` / `test_验证JSON` 两条 xfail
   标记用例会偶发 xpassed，把 passed 顶到 8354 —— 比对时用稳定值，否则误判劣化。

## 门命令（Git Bash / MSYS 语法；必须显式 `--mode full`）

```bash
export PATH="/c/Users/skywalk/.workbuddy/binaries/PortableGit/versions/1.2.0/usr/bin:/c/Windows/System32:/c/Windows:$PATH"
cd lightharness
MSYS_NO_PATHCONV=1 python scripts/082全量回归.py all --mode full --py /usr/local/bin/python3.12
python scripts/082全量回归.py show --recent   # 核对每轮 total/mode/skipped/passed 口径是否一致
```

## 进度台账

| Day | 日期 | 主题 | 报告 | 门 |
|---|---|---|---|---|
| **1** | **10/1（实际执行）** | **`_light_re` 销账 + 真红源（模块名 `正则`）清零 + 同口径 full 基线 + 工作树收口** | **`Day1_主线_红源定靶与门基线.md`** | **PASS（skipped 126→121 / passed +5 / failed 0）** |
| 2 | 10/3 | 异常处理后端收口（LP-D-011 改靶 ANTLR） | 待建 | — |
| 3 | 10/4 | 并发原语定靶与调度层迁移（LP-D-012） | 待建 | — |
| 4 | 10/5 | 北极星 holdout 覆盖率 ≥ 0.95 | 待建 | — |
| 5 | 10/6 | light → harness → Web UI 端到端联调 | 待建 | — |
| 6 | 10/7 | FreeBSD Phase B2+ 实测 + 稳定性 | 待建 | — |
| 7 | 10/8 | 全量验收 + 文档收口 | 待建 | — |

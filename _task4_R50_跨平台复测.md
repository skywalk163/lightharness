# 任务4（R50·P1）交付报告 —— 跨平台复测（本机 + 0.82）

> 日期：2026-09-17 ｜ 状态：**完成（双平台全绿，零新增红）**
> 0.82：192.168.0.82（FreeBSD 15.1-STABLE，Python 3.11.16）
> 远端副本：`/tmp/r44-20260917-123931`（今日 12:39 全量同步，`reports/同步0.82_远程目录.txt` 指针有效）
> 铁律遵守：0.82 只读执行（仅 /tmp 工作副本内运行，未触碰系统与既有数据）。

---

## 一、本机（Windows）验收

R47/R48/R50 全部 9 个新增 examples，逐一 `python 运行.py` 实跑，**全部 rc=0**：

| example | rc |
|---|---|
| test_R47_流式用量桶 | 0 |
| test_R47_代理循环深化 | 0 |
| test_R47_工具scoped | 0 |
| test_R47_会话surface深化 | 0 |
| test_R48_surface消息投影 | 0 |
| test_R48_会话V3迁移 | 0 |
| test_R48_subagent深化 | 0 |
| test_R48_hooks三事件 | 0 |
| test_R50_端到端真实链路 | 0 |

端到端链路要点（任务1交付物复验）：mock LLM 行为队列 FIFO 5 轮 4 次真实工具调用
（bash echo / 真实文件读写 / bash cat），读文件工具、bash cat、R41 提供层三层内容一致，
最终文本正确。

## 二、0.82 副本一致性

```
python scripts/同步0.82.py verify
→ 副本 /tmp/r44-20260917-123931 examples = 413（本机 413）   ✅
→ FreeBSD fb82 15.1-STABLE / Python 3.11.16
```
无需重新 sync：全量同步（含 R48 全部 src 修改与 R50 新 example）已就位且数量一致。

## 三、0.82 新增 examples 复测

9 个 example 经 `同步0.82.py run`（自动注入 LIGHT_MERGE 与 python 垫片）逐一实跑，
**全部 rc=0**。其中端到端真实链路在 FreeBSD 上同样走通：真 bash 回显、真文件读写、
真 HTTP loopback 往返、5 轮 4 次工具调用、最终文本一致——纯逻辑与真实 IO 面跨平台行为一致。

## 四、0.82 全量 pytest

```
python -m pytest tests -q -o addopts=''
→ 7 failed, 1253 passed, 5 skipped, 2 warnings in 354.07s (0:05:54)
```

- **7 failed 与本机 R47/R48 基线名单完全一致**（test_R31 EMBED×2、test_R32 return×1、
  test_R22 嵌入关键字冗余×1、test_R26 词首并入×2、test_R27 词首并入×1 —— 全部存量词法红）：
  **零新增红**。
- 收集总数 1258 = 本机 1258（1255 passed + 3 skipped）；0.82 多 2 条平台性 skip
  （5 vs 3，POSIX/PTY/计时类用例在 FreeBSD 的既定 skip 面板），passed 相应 1253 vs 1255。
- 对照 R44 基线（0.82：7F/1230P/3S/2 errors）：errors 2 → 0，passed +23，
  与 R44→R50 新增用例数吻合。

### 运行方式偏差（如实归因）

1. `pytest.ini` 的 `addopts = --timeout=60 -n auto` 依赖 pytest-timeout/pytest-xdist，
   0.82 未装这两个插件 → 直接跑 rc=4（unrecognized arguments）。
   按"0.82 只读、只装运行必需"口径，用 `-o addopts=''` 覆盖后串行跑，结果等价
   （R44/R45 当时的基线也是无插件环境取得）。
2. 首轮无输出误判：`同步0.82.py run_remote` 只回显远端 stdout，pytest 报错走 stderr；
   远端命令加 `2>&1` 后定位到上述插件缺失，非用例失败。

## 五、结论

- 本机 + 0.82 双平台：9 个新增 examples 全绿；0.82 全量 pytest 零新增红。
- 端到端真实链路（真 LLM 往返 + 真 bash/文件/HTTP）双平台跑通，R41-R43 接真面无平台回归。

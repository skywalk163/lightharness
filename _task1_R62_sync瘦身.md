# R62 任务1：sync 打包瘦身（中间产物进 EXCLUDE）

- 轮次：R62 ｜ 日期：2026-09-19 ｜ 执行：主 agent
- 目标：把 `_taskR11B_test_*/`、docs 历史探针、媒体/打包产物纳入同步 EXCLUDE，
  包体从 **120.3MB 压回 30MB 量级**，让 R61 拆仓的「文件数红利」真正兑现成体积红利。

## 1. 根因复核（R61 结论 + 本轮量化确认）

R61 实测：拆仓后文件数 41197 → 5312（−87%），但包体 30.71MB → 120.24MB（+291%）。
真因不是拆仓失败，而是**本地中间产物被一起打包**——它们与测试无关，却占绝大多数体积。

本轮用探针 `lightharness/_probe_R62_bulk.py`（只读，不删任何文件）重扫两仓，
按「≥1MB 单文件」与「二级目录聚合」两路核对，结果与 R61 登记表一致，无漏网大项：

| 目标 | 位置 | 体积 | 文件数 | 性质 |
| --- | --- | --- | --- | --- |
| `docs/历史存档/` | lightharness | 92.93MB | 732 | R57~R61 历史探针档案（最大单文件 `_r58_tok_A_detail.txt` 49.91MB） |
| `_taskR11B_test_*` | light-merge 根（49 目录） | ~143MB | 245 | R59 测试中间产物（`main.ll` 4.12MB ×9 等），未跟踪 |
| `demo_video/` | light-merge 根 | 12.70MB | 1 | 媒体 `Cinematic_*.mp4` |
| `2026-09-11-d613c31d/` | light-merge 根 | 10.92MB | 15 | 历史任务输出目录（含 `lv_full.tar.gz` 10.85MB） |
| `light_verify.tar.gz` | light-merge 根 | 5.79MB | 1 | 未跟踪打包产物 |
| `data/finetune/` | lightharness | 9.85MB | 7 | 微调语料 jsonl |

≥1MB 单文件合计 **59 个 / 217.82MB**。

### 依赖自查（排除前必须确认「没有测试读它」）

| 排除目标 | 自查方式与结论 |
| --- | --- |
| `_taskR11B_test_*` | 全仓 grep：唯一引用是 `tests/unit/test_原生腿_R11B_中文工具.py:148` 的<br>`tempfile.TemporaryDirectory(prefix="_taskR11B_test_", dir=_ROOT)`——<br>即**测试运行时自己创建**这些目录，现存 49 个是历史残留。<br>排除只影响打包，不影响用例（用例会在 0.82 副本里重新生成）。 |
| `docs/历史存档/` | `tests/` 内唯一出现是 `lightharness/tests/test_回归.py:51` 的**注释**；<br>`light-merge/tests/unit/doc_block_scan.py` 扫的是 **light-merge** 的 `docs/`，<br>与 lightharness 的 `docs/历史存档` 不是同一棵树。无依赖。 |
| `demo_video` / `2026-09-11-d613c31d` | `grep -rn "demo_video" light-merge/tests lightharness/tests` → **零命中**。 |
| `data/finetune` | `grep -rn "finetune" light-merge/tests lightharness/tests` → **零命中**。 |
| `light_verify.tar.gz` | 打包产物本身，`scripts/pack_verify_tar.py` 的产物，非测试输入。 |

## 2. 排除逻辑升级（`lightharness/scripts/同步0.82.py`）

原实现只有**精确目录名集合** `EXCLUDE_DIRS` + `_should_skip()` 遍历 `path.parts` 精确匹配，
**不支持通配/前缀**，因此无法枚举 49 个随机名目录 `_taskR11B_test_<8位随机>`。

### 改动一：新增两类规则

```python
# 1) 目录名**前缀**规则（EXCLUDE_DIRS 是精确匹配，枚举不了随机名）
EXCLUDE_DIR_PREFIXES = ("_taskR11B_test_",)

# 2) 相对仓根的**精确路径前缀**规则（元组为路径分量序列；目录/文件皆可）
EXCLUDE_REL_PREFIXES = (
    ("docs", "历史存档"),        # lightharness：R57~R61 历史探针档案 92.9MB / 732 文件
    ("demo_video",),             # light-merge：Cinematic_*.mp4 12.7MB
    ("2026-09-11-d613c31d",),    # light-merge：历史任务输出目录 10.9MB
    ("light_verify.tar.gz",),    # light-merge：未跟踪打包产物 5.8MB
    ("data", "finetune"),        # lightharness：微调语料 9.9MB（全仓 grep 零测试引用）
)
```

`_should_skip()` 改为：先判路径前缀 → 再判目录名前缀 → 再走原 EXCLUDE_DIRS / 后缀逻辑。
**默认排除集不变**，行为向后兼容。

### 改动二：`build_tarball` 改 `os.walk` + 目录剪枝

原 `base.rglob("*")` 仍会**递归进** 143MB 的 `_taskR11B_test_*` 与 92.9MB 的 `docs/历史存档`
再逐条丢弃——白走一遍树。改为 `os.walk` 并对 `dirnames` 就地剪枝，整棵子树不再遍历。

> 实测副作用（正面）：打包耗时 8.3s → 3.8s（且不再依赖磁盘缓存）。

### 明确保留（0.82 跑测试必需 / 报告类小文件）

`docs/功能对标/`、`docs/语言缺陷账.md`、`lightharness/scripts/`、`reports/`、
两仓根下 `_task*_R*.md` 报告——**一律不排除**。

## 3. 实测验收（`lightharness/_probe_R62_syncsize.py`，本地真实打包）

| 指标 | 改前 | 改后 | 变化 |
| --- | --- | --- | --- |
| 文件数 | 5338 | **4336** | −1002（−18.8%） |
| tar.gz 体积 | 120.43 MB | **30.32 MB** | −90.11MB（**−74.8%**） |
| 打包耗时 | 8.3s | 3.8s | −54% |

**验收线 tar.gz ≤ 35MB：PASS**（30.32MB，落在「30MB 量级」目标内）。

体积构成说明：剩余 30.32MB 主要是两仓源码 + stdlib + examples + 已跟踪的
docs/功能对标 与 reports 基线（含 1.23MB 的 `_082_lm_results_*.xml` 测试结果，
属 reports/ 保留范围，未排除）。

> ⚠️ 踩坑记录：探针首版在同一进程里复用同一个已 import 的模块对象，
> 「改前」把两张排除表清空后「改后」沿用被清空的值 → 测出两组完全相同的假数据
> （5337/120.43MB 与 5337/120.43MB）。**每次测量必须重新加载模块**。

## 4. 无依赖验证

- 打包阶段：无「无法读取」跳过告警（脚本对 OSError 有打印，本次零输出）。
- 运行期依赖：由任务4 的唯一一次 0.82 全量兜底——判据为
  **收集用例数与 R61 的 7884 一致**且无「缺文件 / No such file」类新增红。
  排除的 6 类目标经上表自查均为零测试引用。

## 5. 交付物与改动清单

| 文件 | 改动 |
| --- | --- |
| `lightharness/scripts/同步0.82.py` | 新增 `EXCLUDE_DIR_PREFIXES` / `EXCLUDE_REL_PREFIXES`；`_should_skip` 支持前缀；`build_tarball` 改 os.walk+剪枝 |
| `lightharness/_probe_R62_bulk.py` | 新增：两仓体积构成探针（只读） |
| `lightharness/_probe_R62_syncsize.py` | 新增：打包前后体积/文件数实测（本地打包，不上传） |
| `lightharness/_task1_R62_sync瘦身.md` | 本报告 |

⛔ 全程**只改同步脚本排除逻辑，未物理删除任何已跟踪文件**
（`_taskR11B_test_*` 为未跟踪残留，本轮不动，留待人工确认后清理）。

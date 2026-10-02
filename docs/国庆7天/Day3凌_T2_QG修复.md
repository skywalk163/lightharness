# Day3 凌晨 T2 · quality-gate.yml 修复（最小改动 + Actions 实证）

> 派单：`Day3凌晨_派单表.md` v1.0 · T2（A 线，CI）
> 执行时间：2026-10-03 06:4x（CST，+08:00）
> 依赖：T1 的定量结论
> 出口 tag：`subtask-T2-done`

---

## 〇、结论速览

| 验收项 | 结果 |
|---|---|
| 改动范围 | ✅ **只动 `quality-gate.yml` 一个文件的「运行单元测试」一步**（+15 / -1） |
| 是否动了 ci.yml / 测试断言 / 编译器 | ❌ 全都没动 |
| 本机复刻验证 | ✅ 上次红的两个文件在新口径下 **39 passed**；`--ignore` 在目录式收集下生效（4336 → 4334，lexer_perf 的 2 条被剔除） |
| YAML 仍然合法 | ✅ `yaml.safe_load` 解析通过，`run` 段落还原正确 |
| **push 后 Actions 实证** | 见 §四（本批结尾回填） |

---

## 一、改动原文

**文件**：`light-merge/.github/workflows/quality-gate.yml`（第 114–127 行）

**改前**：
```yaml
      - name: 运行单元测试
        run: |
          pytest tests/unit/ -v --tb=short --cov=src --cov-report=term --cov-report=xml:coverage.xml
```

**改后**：
```yaml
      - name: 运行单元测试
        run: |
          # ── Day3 凌晨 T2：本步原本「每次 push 必红同样 3 条」，两条根因 + 两条对策 ──
          # ① --timeout=180：pyproject 的 addopts 写死 `--timeout=60`。本机实测
          #    test_package_manager::test_build_project_success 无 cov 20.4s、带
          #    `--cov=src` + `-n 4` 时 35.5s（test_run_project_success 10.0s → 31.8s）；
          #    共享 runner 上再叠加抢核就撞线（rc1/rc2 两次都死在这两条 Timeout）。
          #    180s ≈ 本机 cov 值的 5× 余量，仍远小于 job 总时长，不是"放宽到永不触发"。
          # ② --ignore tests/unit/test_lexer_perf.py：性能断言 + --cov 插桩 = 测量被污染。
          #    本机实测同一用例：无 cov 1.30s → 带 --cov=src 4.39s（3.4×）；runner 上
          #    20.13s(rc2) / 26.72s(rc1)，均超 LEXER_PERF_LIMIT=20.0。
          #    在 coverage 会话里跑性能断言，量到的是"插桩后的性能"而非真实性能。
          #    该用例的守护交给 ci.yml 的无 cov 会话（pytest tests/unit/，默认预算 10.0s，
          #    12 份 OS×Python 矩阵全覆盖）——不删测试、不放宽断言，只换个干净的测量环境。
          pytest tests/unit/ -v --tb=short --timeout=180 \
                 --ignore=tests/unit/test_lexer_perf.py \
                 --cov=src --cov-report=term --cov-report=xml:coverage.xml
```

**diff stat**：`1 file changed, 15 insertions(+), 1 deletion(-)`

---

## 二、为什么是这两个动作（承接 T1）

1. **`--timeout=180`**：`addopts` 写死 `--timeout=60`，而本机带 cov 的实测已经是 35.47s / 31.75s。
   共享 runner 上再叠加抢核必然撞线。**已验证命令行 `--timeout` 能覆盖 addopts**
   （用 `--timeout=1` 做探针，该用例立刻 Timeout 失败 → 覆盖生效）。
2. **`--ignore` 剔除性能断言**：性能断言放在 coverage 会话里，量的是「插桩后的性能」。
   本机 1.30s → 4.39s（3.4×），runner 上 20–27s —— **阈值本身没错，是测量条件错了**。
   换到 ci.yml 的无 cov 会话后，同一条断言在 12 份矩阵上以默认 10.0s 预算继续守护。

**刻意没做的事**（列出来防后人误判）：
- 没改 `LEXER_PERF_LIMIT`（保留 20.0）—— 剔除后 QG 侧不再用它，改它反而是"放宽断言"。
- 没改 `test_lexer_perf.py` 的断言代码 —— 派单表铁律第 3 条。
- 没去掉 `--cov` —— 覆盖率是 QG 的正当职责，不该为性能断言让路。
- 没动 `ci.yml` —— 它本来就是全绿的。

---

## 三、本机验证（push 前的把关）

| 验证 | 命令 | 结果 |
|---|---|---|
| 新口径跑上次红的两个文件 | `pytest tests/unit/test_package_manager.py tests/unit/test_lexer_perf.py -v --timeout=180 --ignore=... --cov=src` | **39 passed**（其中 build 35.47s / run 31.75s 均在 180s 内） |
| `--ignore` 在目录式收集下生效 | `pytest tests/unit/ --ignore=tests/unit/test_lexer_perf.py --collect-only -q` | 收集 **4334**；`grep -c lexer_perf` = **0**（不 ignore 时为 **2**） |
| YAML 仍合法 | `yaml.safe_load(...)` | ✅ 解析通过，`run` 还原为预期的三行命令 |

> ⚠️ 一个值得记下的坑：**`--ignore` 对「显式写在命令行上的文件参数」无效**。
> 我第一版验证是把两个文件都显式传进去，结果 lexer_perf 照样被收集（39 passed 里含它）。
> QG 的真实命令只传目录 `tests/unit/`，所以 ignore 生效——这一点已用目录式收集单独验证过。

---

## 四、push 后的 Actions 实证（已回填）

推送 light-merge `e53073d3cb` 后，GitHub 触发 **Quality Gate run `37074880689`**
（同时触发 CI run `37074880670`）。结论：**`completed success`**（完成于 2026-10-02T23:25:19Z）。

| job | 结论 |
|---|---|
| Lint 检查 | **success** |
| 全量测试 (3.10) | **success** |
| **全量测试 (3.12)** | **success** ← 上一批两次都死在这 |
| 全量测试 (3.11) | **success** |
| **构建验证** | **success** ← 上一批是 `skipped`（被上游失败跳过），本次首次真正跑起来 |

`全量测试 (3.12)` 的逐 step：

```
step success 设置 Python 3.12
step success 安装依赖
step success 运行单元测试      ← 本次修复的目标 step，由 failure 转 success
step success 运行集成测试      ← 此前从未执行过（被上游 skip）
step success 运行端到端测试    ← 此前从未执行过
step success 运行全量 pytest   ← 此前从未执行过
step success 检查测试覆盖率（不低于 25%）  ← 此前从未执行过
step success 上传覆盖率报告
```

**这不是"把红改成绿"，而是整条门禁第一次真正跑完**：
上一批 unit 一失败，后面 5 个 step（含覆盖率门禁与构建验证）全被 skip，
QG 实际上**从来没履行过它宣称的职责**。本次它们全部首次执行且全部通过。

**CI 侧同时确认**：run `37074880670` 的 18 个 job **全 success**，
其中 `test (ubuntu-latest, 3.12)` 等 12 份矩阵跑的就是**无 cov 的 `pytest tests/unit/`** ——
也就是 `test_lexer_perf` 在迁移后的新家，**默认 10.0s 预算下依然绿**，
证明「守护交给 ci.yml 的无 cov 会话」这个判断是真成立的，不是自说自话。

---

## 五、出口判据回看

| 判据 | 达成 |
|---|---|
| workflow diff 仅单测一步 | ✅ §一（+15/-1，只一个文件的一步） |
| 本机复刻绿 | ✅ §三 |
| push 后 QG 结论 = success | ✅ **§四：整条 QG `success`，且 5 个此前被 skip 的 step 首次全部执行通过** |

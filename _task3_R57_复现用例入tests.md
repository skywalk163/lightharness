# R57 任务3 交付 —— 复现用例挂 tests/ + `gate_remote` 透传 `--py`

> 日期：2026-09-18 ｜ 责任范围：任务3 四项工作内容 + 定向验证（未跑任何全量）

---

## 一、交付清单

| # | 交付物 | 位置 | 说明 |
|---|---|---|---|
| 1 | 词法回归用例（token 层钉桩 + 运行层真跑） | `lightharness/tests/test_R57_复现回归.py`（新增，11 用例） | R22/R26/R27 的 4 场景 + 3 条铁律守卫 + 4 例 example 真跑 |
| 2 | L-170 回归用例（G7 缺口收口） | `light-merge/tests/test_R57_L170回归.py`（新增，1 用例） | 源码内嵌 + run/product 双腿 + 断言 `L170-OK` |
| 3 | `gate_remote` 透传 `--py`（G8） | `lightharness/scripts/多平台矩阵.py`（±7 行） | gate 远端腿新增 `--py`（默认仍 `/usr/local/bin/python3.12`） |
| 4 | 惯例固化 | `lightharness/docs/CI.md` 新增章节 | 「缺陷复现用例必须同时挂 tests/，只放 examples/ 不算进全量门」 |
| 5 | 探针 | `lightharness/docs/历史存档/R57探针/_r57_task3_副本核对.py`、`_r57_task3_082定向验证.py` | 副本一致性只读核对 + 0.82 定向验证 |

## 二、用例设计

### 2.1 `test_R57_复现回归.py`（lightharness 侧，11 例）

针对 R56 任务2 归因、R57 任务1a 修复的两处 `src/lexer.py` 缺陷：

| 层 | 用例 | 钉住的行为 |
|---|---|---|
| token | `test_r22_为了_嵌入关键字整词成标识符` | `设 为了 为 "为了值"` → `为了` 整词 IDENTIFIER（修复前 `为`+`了`） |
| token | `test_r26_段名_测试返回语句_不被返回腰斩` | 段名内嵌 `返回` 不切开（修复前 `测试`+`返回`+`语句`） |
| token | `test_r26_段名_测试真的与返回_整词成标识符` | 同上（修复前 `测试真的与`+`返回`） |
| token | `test_r27_段名_测试_返回真_真不被切出成裸名` | `真` 不沦为裸标识符（修复前 `测试_`+`返回`+`真`，`name '真' is not defined`） |
| token | `test_guard_硬语句关键字词首仍切分` | R26 的坑：`返回`/`如果` 词首必须切分 |
| token | `test_guard_L155_嵌入块吞并语义保持` | `返回表`/`行为`/`尝试记录` 仍整词成 IDENTIFIER |
| token | `test_guard_普通赋值不受修复影响` | `设 甲 为 1` 基线形态 |
| 运行 | `test_r57_复现example真跑绿[×4]` | 4 个 example 文件按 `test_回归.py` 机制真跑断 rc==0 |

### 2.2 `test_R57_L170回归.py`（light-merge 侧）

- 源码**内嵌**（与 `examples/test_L170.light` 逐字一致），不依赖被 `.gitignore`
  忽略（`test_*.light` 模式）的 examples 文件，克隆即可用；
- run 腿（`-m cli.light run`，与 `运行.py` 同入口）+ product 腿（`compile -o` 后
  独立执行），沿用 `tests/test_frontend_blockers_run.py` 的双腿机制；
- 断言运行时输出 `L170-OK` 且四个失败标记均不出现。
- ⚠️ 实测发现：`-m cli.light_unified run` **不转发 stdout**（rc=0 但输出为空），
  不能用作输出断言入口；本用例因此选 `cli.light`（已验证）。

### 2.3 `--py` 透传（G8）

- `多平台矩阵.py` 新增 `--py`（dest `py_082`，默认 `/usr/local/bin/python3.12`），
  `gate_remote` 拼装的 `082全量回归.py test` 命令行携带 `--py <值>`；
- 082全量回归.py 原有的「3.12 带 xdist / 3.11 置空 addopts」口径自动继承，无重复实现。

## 三、验证结果（定向，未跑全量）

### 3.1 本机（Windows，py3.12.6，含任务1a 已落地的 lexer 修复）

```
tests/test_R57_复现回归.py   → 11 passed in 4.02s
tests/test_R57_L170回归.py   → 1 passed  in 2.12s
```

### 3.2 0.82（FreeBSD 15.1，py3.12，副本 `/tmp/r44-20260917-235706`）

远端 `src/lexer.py` md5 = `1461c49…`（仍是 R54 旧版，**任务1a 修复尚未同步**），
正好构成「修复前」环境：

| 用例 | 结果 | 说明 |
|---|---|---|
| token 层 4 场景 | **8 failed 中的 4 条红（预期）** | token 流形态与 R56 报告逐项一致（`为`+`了`、`测试`+`返回`+`语句`、`测试真的与`+`返回`、`测试_`+`返回`+`真`）→ **用例判别力直接证实** |
| 3 条守卫 | 绿 | 守卫只钉「修复不许破坏」的语义，旧 lexer 下亦绿，无误报 |
| 运行层 4 example | 红（rc=1，预期） | 与 R56 的 4 例 example 红一一对应 |
| `test_R57_L170回归.py` | **1 passed** | R54 修复入全量门，G7 缺口闭环 |

**证据链完整**：同一份用例在「修复前」（0.82 旧 lexer）红、在「修复后」（本机新
lexer）绿，且报错形态与 R56 取证逐字节同族。

### 3.3 `--py` 自验（秒级）

- `--help` 参数面：`--py PY_082` 在位，默认 3.12；
- 拼装面（mock `_stream_proc` 真走 `gate_remote` 代码路径）：
  `… 082全量回归.py test --mode fast --py /usr/local/bin/python3.11 --timeout-sec 2700`，
  `--py` 位置与取值正确。

## 四、遗留与移交

1. **0.82 上 4 场景 + 4 example 的「绿」验证**：按批次B 规则须在任务1a 修复同步
   0.82 之后做。两个测试文件已上传到远端副本，届时一条命令即可：
   ```sh
   cd /tmp/<rd>/lightharness && LIGHT_MERGE=/tmp/<rd>/light-merge PYTHONIOENCODING=utf-8 \
     /usr/local/bin/python3.12 -m pytest tests/test_R57_复现回归.py -v -o addopts= -p no:cacheprovider
   ```
   预期 11/11 绿；若仍有红说明任务1a 同步未生效或修复不完整。
2. **`甲为三`（G5）未修**：实测当前仍切成 `甲为三` 一词、`为` 关键字丢失
   （任务1a 未覆盖该分支），按任务书「不许扩大改动面」未纳入本批用例，
   维持登记待词法轮处置。
3. lightharness 快门（gate_local）与 0.82 light-merge 全量（路M）将自动收集两个
   新测试文件（文件名不落任何 ignore 规则）。
4. `__RC__` 回显在 FreeBSD sh 下无 PIPESTATUS（bashism），本次判定全部以 pytest
   输出文本为准（符合铁律2 的判红绿口径）。

## 五、纪律自查

- 未跑任何全量（本机 / 0.82 均只有定向子集）；
- 0.82 仅一次排队会话（只读核对 + 上传两个新增文件 + 两条定向 pytest）；
- 未改 `src/`、未改任务2 在改的 `tests/unit/test_lexer_perf.py` /
  `tests/test_distributed_eval_light.py`，无文件冲突；
- MEMORY.md 回填（惯例条目）按任务书归任务5，本报告不越界。

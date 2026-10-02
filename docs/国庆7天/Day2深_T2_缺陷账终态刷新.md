# Day2 深夜 T2 · 缺陷账终态刷新（LP-D-001 ~ LP-D-017 全账终审）

> 派单：`Day2深夜_派单表.md` v1.0 · T2（B 线，纯文档）
> 执行时间：2026-10-02 23:48–00:0x（CST，+08:00）
> 执行者：主会话（team lead）
> 出口 tag：`subtask-T2-done`

---

## 〇、结论速览

| 验收项 | 结果 |
|---|---|
| 是否零编译器改动 | ✅ 只改两本账的状态列 / 证据列，`light-merge/src/`、`antlrparser/` 零改动 |
| 主账 diff 形态 | ✅ 6 行改、6 行增，**仅表格行**（编号/现象/最小复现/期望能力四列原样保留） |
| LP-D-010 | ✅ 改为 **销账（SRC 后端）**，并诚实标注 ANTLR 后端原始形态仍红 → 并入 LP-D-013 族 |
| LP-D-011 | ✅ 维持「已改靶 + ANTLR 收口」，补贴本批 8 次实跑证据 |
| LP-D-012 | ✅ 维持「部分收口」，补贴本批 A/B 复跑 9/9 |
| LP-D-013（两行） | ✅ 改为 **已修复（双后端）**，附新发现的 SRC `返回 跳过` 残留 |
| 全账终审 | ⚠️ 发现 2 条**新观察**（ANTLR 未注册判型族内置 / SRC `返回 跳过`），**未改状态**，建议下批立账 |

---

## 一、改了哪些文件

| 文件 | 改动 | 是否在 git 管辖内 |
|---|---|---|
| `lightharness/docs/功能对标/语言缺陷账.md` | 6 行：1712 / 1713 / 1714 / 1722 / 1732 / 1742 | ✅ 跟踪中，进 commit |
| `lightplugin/_archive/reports/语言缺陷反馈.md` | 5 行状态：LP-D-010/011/012/013/016 | ⚠️ **被 `.gitignore:17: _archive/` 排除**，改动**只落本地磁盘、不进 commit** |

> 源账改了但没法 commit 这件事要写清楚：它是被 ignore 的归档目录。
> 后续若要在远端保留这份刷新，需 `git add -f`（本批不动，避免破坏 ignore 约定）。

---

## 二、本批**亲自复跑**的探针（不是引用旧数）

派单要求「核对」，所以每一行状态背后都是本批当场跑出来的 rc / 输出，而不是抄 Day2 报告。

### 2.1 LP-D-010（3 探针 × 2 后端）

| 探针 | SRC | ANTLR |
|---|---|---|
| `probes/lp010_重名.light` | rc=0（`a`） | **rc=0（`a`）** |
| `probes/lp010_重名_严格.light` | rc=0（`a`） | rc=1 |
| `probes/lp010_账内原文.light` | rc=0（`a`） | rc=1 |

命令：
```bash
cd /g/dswork/duan-light-merge/lightharness && export PYTHONUTF8=1 PYTHONIOENCODING=utf-8
../light-merge/.venv/Scripts/python.exe ../light-merge/cli/light.py run \
  "docs/国庆7天/probes/lp010_重名.light" [--backend antlr]
```

**判定**：酸痛点本体（`遍历` 循环变量与被调用函数同名）**SRC 后端销账成立**。
ANTLR 后端的两例失败**不是**「重名」问题，而是段名/循环变量取了词法关键字 `回调`
（`LightLangLexer.g4` 的 `K_CALLBACK`）导致 `期望 ID，却遇到了 '回调'`——
这是 **LP-D-013 同族**的「关键字作标识符」缺口。因此账行写成：
**✅ 销账（SRC）｜⚠️ ANTLR 原始形态仍红 → 并入 LP-D-013 族**，
而不是简单写「已修复」——后者会让后来者误以为两个后端都能跑原文。

### 2.2 LP-D-011（4 探针 × 2 后端 = 8 次，全 rc=0）

| 探针 | 输出（两后端一致） |
|---|---|
| `lp011_probe` | `TRY_OK` |
| `lp011_probe2` | `CATCH_OK: boom` / `AFTER` |
| `lp011_finally` | `TRY_OK` / `FINALLY_OK` / `AFTER` |
| `lp011_multi_catch` | `CATCH1: boom` / `FINALLY` / `AFTER` |

**判定**：try / 多捕获 / finally 三条路径**双后端全绿**，Day2「已改靶 + ANTLR 收口」维持。

### 2.3 LP-D-012（A/B 等价探针复跑）

```bash
cd /g/dswork/duan-light-merge/lightharness
export PYTHONUTF8=1 PYTHONIOENCODING=utf-8 CODEBUDDY_SAFE_DELETE_ENABLED=0
../light-merge/.venv/Scripts/python.exe docs/国庆7天/probes/lp012_ab_并发对照.py \
  --repo "G:/dswork/duan-light-merge/lightharness" \
  --light-merge "G:/dswork/duan-light-merge/light-merge" --reps 1
```

结果：**`用例总数=9 通过=9 失败=0 耗时=67.5s`，rc=0**（本机 Windows 执行，与 Day2 夜场在
0.82 上 reps=2 两次一致的结论吻合）。反向哨兵「同步段落内写 `等待` 必须报错」也在 9 用例内。
→ 维持「部分收口」，不升格（注入式场景仍在账面上，没消失）。

### 2.4 LP-D-013（2 探针 × 2 后端，两后端全 rc=0）

| 探针 | SRC | ANTLR |
|---|---|---|
| `lp013_probe` | rc=0，**`[1]`** | rc=0，**`[1]`** |
| `lp013_probe2` | rc=0，无语法元素错（输出 `None`） | rc=0，无语法元素错（输出 `[7]`） |

ANTLR 侧由 Day2N T2（light-merge `221db4fc6`）补齐，本批确认仍在绿。
回归用例 `lightharness/tests/unit/test_Day4_LP013_探针回归.py` 的断言口径是
「rc=0 且输出不含『无法识别的语法元素』」，两后端都满足。

**⚠️ 新观察（本批发现，未改状态）**：`lp013_probe2` 的**输出**两后端不一致——SRC `None`、ANTLR `[7]`。
二分定位（新鲜实跑，非推测）：

| 变体 | SRC | ANTLR |
|---|---|---|
| 原文 `设 块 为 7` + `乙()` 内 `跳过.追加(块)` + `返回 跳过` | `None` | `[7]` |
| 改为参数传递 `段落 乙(块):` | `None` | `[7]` |
| **函数内 `打印(转字符串(跳过))`（不返回）** | **`[7]`** | **`[7]`** |

→ 列表 append 与函数内读值都正常，**缺口精准落在 SRC 的 `返回 跳过` 这一步**：
取不到这个重分类变量的值，返回 `None`。
属「关键字词作变量名时的 `返回` 取值」问题，**不影响「成员访问解析」这一本体**，
故**不改 LP-D-013 状态**，只在账行里挂为「建议单独立项」的残留。

### 2.5 LP-D-016（顺带核对 → 又一条新观察）

| 探针 | SRC | ANTLR |
|---|---|---|
| `lp016_probe` | rc=0（`True`/`False`/`True`） | **rc=1**（未定义的变量：`是数字`） |
| `lp016_followup` | rc=1（类型错误：`isdigit` 不接受 int） | **rc=1**（未定义的变量：`是数字符`） |

→ **SRC 侧名实已对齐成立**；**ANTLR 后端未注册判型族内置**（`是数字`/`是数字符`）。
同样写入账行的「复现套件」列作为新观察，**不改状态**（避免把双后端问题伪装成已修）。

### 2.6 LP-D-001 ~ LP-D-009 / 014 / 015 / 017（终审结论）

| 编号 | 源账状态 | 本批评定 |
|---|---|---|
| LP-D-001 ~ 006、008、009 | 已修复（各自带线路与日期） | ✅ 维持，无冲突证据 |
| LP-D-007 | 已定性（更正，非缺陷） | ✅ 维持 |
| LP-D-014 | 已定性（契约纠正） | ✅ 本批实跑 `lp014_fixed` 两后端 rc=0 / `lp014_probe` 两后端 rc=1（期望红），一致 |
| LP-D-015 | 已定性（契约纠正） | ⚠️ `lp015_fixed`（`"abcdef"[1:3]`）**SRC rc=0 输出 `bc`、ANTLR rc=1 解析失败** —— 仅 SRC 成立，同属「ANTLR 覆盖面」观察簇，未改状态 |
| LP-D-017 | 已修复（宿主侧 R99） | ✅ 维持（探针 `lp017_probe` 设计为在 lightharness 仓内跑 pytest，直接 `cli run` 报缺模块属用法不当，非 defect 回潮） |

---

## 三、出口判据回看

| 判据（派单表 §四） | 达成 |
|---|---|
| 账 diff 仅状态列/证据列 | ✅ 6 行替换，前四列（编号/现象/最小复现/期望能力）逐字保留，用 ` | ` 定点替换不重排表格 |
| LP-D-010 → 销账 | ✅（并加了 ANTLR 侧的诚实限定） |
| 其余行与实际一致 | ✅ LP-D-011/012 复跑确认；LP-D-013 升至双后端已修；LP-D-016 挂新观察不改状态 |

---

## 四、遗留 / 建议（给下一批）

1. **ANTLR 后端覆盖面**已成簇：`K_CALLBACK`（LP-D-010 原文形态）、判型族内置（`是数字`/`是数字符`）、
   索引切片写法（`lp015_fixed`）——建议打包成一个专门的「ANTLR 后端内置/词法覆盖面」冲账项。
2. **SRC `返回 <关键字词变量名>` 取值缺口**（`返回 跳过` → `None`）建议单独立账：
   极小复现已在 §2.4 给出（函数内打印都得 `[7]`，唯 `返回` 丢值）。
3. 源账 `lightplugin/_archive/reports/语言缺陷反馈.md` 在 `.gitignore` 里，
   两本账长期会漂移 —— 建议二选一：把它 `git add -f` 纳入，或在聚合账里明确「源账只读」。

---

## 五、工具与幂等

本批用的补丁脚本：`lightharness/scripts/_t2_patch_ledger.py`
- **幂等**：哨兵串 `Day2深夜 T2 刷新`；已应用则整本跳过，不会二次插入。
- **保真**：主账按 ` | ` 切 CELL 定点替换第 4/5 列；CRLF + BOM 用 bytes 读写原样保留。
- **可重放**：`python scripts/_t2_patch_ledger.py --dry` 只预览不落盘。

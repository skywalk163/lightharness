# 任务5（R37）交付报告：性能对比 + 联动评估 + pytest

> 范围：代理循环统一（重命名）后的性能与联动评估；pytest 覆盖统一后导入路径。
> agent-default-model（任务2）相关覆盖**登记为待任务2 交付后补做**。

---

## 一、性能对比

**结论：无显著变化（按构造为 0）。** 本轮为**内容保持的重命名**（`git mv` 不改内容；
4 个 stdlib 文件的 comment 微调不改 token），tokenize 负载与统一前**逐字节相同**。

- 语料：**767 文件 / 3,079,305 字符**（lightharness{src,examples,stdlib} + light-merge{examples,src/stdlib}）。
- 全量 tokenize 两轮取样（同一负载，仅反映本机噪声）：
  - 取样①：11901 / 11537 / 12220 ms，均值 ≈ **11.9 s/轮**；
  - 取样②（CRLF 修复后复跑）：14352 / 16976 / 17029 ms，均值 ≈ **16.1 s/轮**。
  - 两取样相差 ~35%，**纯属 HP Z620 本机系统噪声**（与代码无关：负载逐字节相同）。
- 「统一前」为同一负载（内容字节相同，仅文件名不同）→ Δ = 0（非噪声，是构造性不变）。
- 佐证：本轮修改的 **5 个文件 token 流与 HEAD 逐文件完全一致**（见下表）。

| 文件（当前） | 对比对象（HEAD） | token |
|---|---|---|
| stdlib/代理运行时.light | stdlib/代理循环.light | ✓ 一致 (3868) |
| stdlib/事件总线.light | 同 | ✓ 一致 (1066) |
| stdlib/代理工具集.light | 同 | ✓ 一致 (3852) |
| stdlib/并发.light | 同 | ✓ 一致 (985) |
| stdlib/重试.light | 同 | ✓ 一致 (166) |

---

## 二、联动评估（只出结论，不改代码）

1. **对现有模块的影响：零。** `stdlib/代理运行时.light` 是**孤儿**（全语料 0 个导入方）→
   重命名不触动任何调用点；对 `src/代理循环.light`（核心层）与 `src/代理.light` 的
   `类 代理循环`（17 处 `从 代理 导入` 引用）均无影响。
2. **模块解析方向**：src 先于 stdlib（`运行.py` 路径插入顺序 + 导入钩子 `[SRC, STDLIB, ROOT]`），
   重命名后 `代理循环` **唯一指向 src**，歧义消除。
3. **同类风险登记**：另有 **`加密.light`/`重试.light`** 同时存在于 src/ 与 stdlib/
   （src 优先，未报冲突）。R37 范围外，已在 pytest 中以「已知集合」守卫登记，建议后续轮次评估统一。
4. **agent-default-model 联动**：`代理默认模型`（任务2）尚未交付 → 与 `代理`/`代理团队`/`大模型客户端`
   的联动评估**待任务2 完成后补做**。

---

## 三、pytest

`tests/test_R37_代理循环统一_token.py`（**7 passed**）：
1. `test_代理循环_同名冲突已消除` —— `代理循环.light` 仅在 src、stdlib 已无该名；`代理运行时.light` 在 stdlib。
2. `test_剩余同名冲突仅为已知集合` —— src∩stdlib 同名 ⊆ `{加密.light, 重试.light}`（防新增未处理冲突）。
3. `test_导入符号由src代理循环导出` —— 两测试从 `代理循环` 导入的符号 ⊆ `src/代理循环.light` 导出清单。
4. `test_统一相关文件tokenize正常`（参数化 3 文件）—— 重命名文件 / src 核心 / R37 集成测试 tokenize 无异常。
5. `test_代理运行时保留旧版导出` —— 重命名不改内容，`会话`/`代理循环` 导出保持。

> 注：agent-default-model 核心功能的 pytest 覆盖**待任务2 交付后补做**。

---

## 四、全量回归

`pytest tests/test_回归.py -q` → **382 passed / 0 failed**（20m45s，Windows 串行）。

- R36 该套件为 381 passed；本轮 **+1** = 新增 `examples/test_R37_集成测试.light` 被收集。
- 无新增打红、无基线外失败 ⇒ **零回归**，与 token 零变化取证（§一）互证。

---

## 五、交付物
- `_task5_R37_性能对比+联动评估+pytest.md`（本报告）
- `lightharness/tests/test_R37_代理循环统一_token.py`（7 用例）
- `lightharness/_r37_task5_perf.py`（性能 + token 零变化取证脚本，探针不提交）

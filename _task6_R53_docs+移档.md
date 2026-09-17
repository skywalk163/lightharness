# 任务6（R53·P2）交付报告 —— 缺陷账登记 + docs回填 + 探针移档

> 日期：2026-09-17 ｜ 状态：**完成**
> 交付物：本报告 ｜ 铁律遵守：docs定稿归路M。
> 关联：L-172编译器静默阻断修复（任务1/2）

---

## 一、缺陷账登记：L-172标记已修

**文件**：`lightharness/docs/功能对标/语言缺陷账.md`

**新增条目**：`## L-172（第53轮任务1/2）模块级对入口名取裸引用 → 静默抑制主()自动调用（rc=0 但主()完全不执行）`

**条目要点**：
- **现象**：模块级对入口名取裸引用（`设 X 为 主`）→ 编译器误判为「已启动入口」→ 不补 `if __name__ == '__main__': 主()` → rc=0 但主()完全不执行、无报错、无输出。
- **任务书原描述澄清**：「辅助段落体内按名调用被导入函数」**不触发**阻断（任务1诊断1620组fuzz+全语料扫描均证实），真根因是模块级裸引用。
- **次静默点**：入口带形参（`段落 主 接收 参数:`）→ src腿静默不调用 → 改为编译期告警。
- **修复**：`_node_calls_name()` 增加 `calls_only=True`，只认真正的 ParagraphCall 调用，不再把 Identifier 裸引用算成已启动入口。
- **影响面**：全语料373个有入口段落文件中，修复1影响0例，修复2影响1例（库文件，仅多一条stderr告警）→ 对既有语料行为零变化。
- **状态**：✅ 已修复（第53轮任务2）

---

## 二、docs回填：对标清单 #192

**文件**：`lightharness/docs/功能对标/对标清单.json`

**新增条目 #192**：

| 字段 | 值 |
|---|---|
| 编号 | 192 |
| 功能 | L-172编译器静默阻断修复（模块级裸引用入口名抑制主()自动调用） |
| 原模块 | 编译器codegen入口自动调用判定 |
| 光明模块 | light-merge/src/code_generator.py + cli/light.py |
| 状态 | 已完成 |
| 完成轮次 | 第53轮 |
| 备注 | 任务1/2。修复_module_invokes_entry/_node_calls_name把裸引用Identifier误判为已启动入口的bug，改为只认真正的ParagraphCall调用；带形参入口改为编译期告警不再静默跳过。复现用例examples/test_L172.light红绿双向取证。全量pytest零新增红，0.82跨平台通过。 |

**当前对标清单总条目数**：192（原191 + 新增1）

---

## 三、探针移档

**源**：`light-merge/_l172probe/`（17个文件）
**目标**：`lightharness/docs/历史存档/R53探针/`

**探针文件清单**：
- README.md（探针说明与副作用清单）
- verify_fix.py（红前/绿后双向取证）
- matrix.py（7形态矩阵探针）
- fuzz.py / fuzz2.py（1620组形态fuzz）
- measure_arity.py（arity度量）
- gate3.py（闸门3度量）
- scan_missing_entry.py（全语料缺失入口调用扫描）
- pre_fix.py / mut_r52.py（R52真实用例机械还原）
- w_lightharness.py（lightharness布局验证）
- var_sweep.py（空格/连写变体）
- probe_entry.py / probe_drop.py / cand.py / h1.py / dump.py（辅助诊断脚本）

**操作**：全部17个文件从 `light-merge/_l172probe/` 移动到 `lightharness/docs/历史存档/R53探针/`，原空目录已删除。

---

## 四、本轮改动文件清单

| 文件 | 操作 |
|---|---|
| `lightharness/docs/功能对标/语言缺陷账.md` | 追加L-172条目 |
| `lightharness/docs/功能对标/对标清单.json` | 新增#192条目 |
| `light-merge/_l172probe/` → `lightharness/docs/历史存档/R53探针/` | 移档17个探针文件 |

---

## 五、结论

1. 缺陷账L-172条目已登记并标记**已修复**；
2. 对标清单#192已新增，与L-172修复对应；
3. 探针已移档至 `docs/历史存档/R53探针/`，原位置已清理；
4. docs三件套（缺陷账+对标清单+探针移档）全部完成，归路M定稿。

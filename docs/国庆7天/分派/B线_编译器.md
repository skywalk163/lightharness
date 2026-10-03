# Day3 下午场 · B 线子任务书（编译器）

> **派发对象**：Agent B
> **线**：B（编译器）
> **父派单**：`../Day3下午_派单表.md` v1.1
> **你的领地**：`light-merge/antlrparser/`（g4 + visitor + builtins）
> **你的禁区**：`.github/`、`pyproject.toml`、`lightharness/docs/`、192.168.1.5

---

## 一、你要做什么（串行三步 + 一次门）

### T3 · 修 LP-D-019①：`回调` 作词法关键字作段名/循环变量

**现状**：探针 `lightharness/docs/国庆7天/probes/lp010_重名_严格.light`（段名与循环变量都叫"回调"）
- SRC 后端：rc=0 ✅
- ANTLR 后端：rc=1 `期望 ID，却遇到了 '回调'` ❌

**修法**：参照 `221db4fc6` 那次对 `出/跳过` 的改法（LP-D-013 范式 A 上下文软关键字），
在 ANTLR 侧让 `回调` 可作段名/循环变量。

**⚠️ 硬规程**：改 g4 必须重生成 parser：
1. 姿势照 `Day2夜_T2_LPD013_ANTLR补缺口.md` §三（两步 + `-encoding UTF-8` + `-lib light_parser`）
2. 产物对拍逐字节一致才许继续
3. 本机 java 不可用时，先用该报告的自动下载脚本确认 JRE 工具链
4. **别在没有 JRE 的机器上硬生成**

### T4 · 修 LP-D-019③：索引切片 `"abcdef"[1:3]`

**现状**：探针 `lightharness/docs/国庆7天/probes/lp019_索引切片.light`
- SRC：rc=0 输出 `bc`（止为开区间）✅
- ANTLR：rc=1 `第4行 第13列 语法错误` ❌

**修法**：ANTLR g4/visitor 补索引切片产生式，口径对齐 SRC（止为开区间）。重生成同 T3 硬规程。

### T5 · ANTLR 覆盖面批量补齐

在 T4 收口后串行做：

1. **判型族整族注册**：`是整数`/`是浮点`/`是字符串`/`是列表`/`是字典`/`是空`/`是布尔`/`是函数`
   - 证据探针：`probes/lp019_判型族_语义矩阵.light`
   - 语义对齐 SRC：int/float 排 bool、str 判型、容器判型、callable 判定
   - 加回归探针 `lp019_判型族_整族回归.light`
   - **注意**：清晨场 T4 已注册 `是数字`/`是数字符`，`是数字符` 当前带 `len==1` 守卫
     （`_builtin_is_digit`）。口径裁定等用户三选一，本步**不要动** `是数字符` 语义，
     只补其他 8 个
2. **`列.获取(下标)` 绑定方法**：Day2N T2 补了 追加/移除/弹出/反转/清空，`获取` 漏了
   - SRC 走 `_light_get`：字典 get / 列表下标，缺键缺下标回默认值不抛
   - 加 1–2 条用例
3. **行 19 组合修复**：循环内裸 `跳过` + `跳过.追加(0)` 同文件 → ANTLR `未定义的变量: '自我'`
   - 探针 `probes/lp013_组合_循环内裸跳过与成员访问.light`
   - 两段单独跑都过、组合才触发。先最小化复现再定位

### T3+T4+T5 合并门

全部改完后，跑一次 full 门：
```
cd G:\dswork\duan-light-merge\lightharness
$env:CODEBUDDY_SAFE_DELETE_ENABLED="0"
python scripts\082全量回归.py all --mode full
```
对锚点 `reports/082_lightmerge基线_2026-10-03-093246.json`（8357/0/121）三元判据：
- failed 新增 0
- skipped 不增
- passed 不降（T3/T4/T5 新增用例后应略升）

**门过即 B 线收口**，立刻在会话里报"full 门三元绿"给 A 线 agent（他要等这个信号打 tag）。

---

## 二、绝对禁止

1. 🚫 碰 `src/` 目录（SRC 后端是对的，只修 ANTLR 侧）
2. 🚫 碰 `.github/` / `pyproject.toml`（A 线领地）
3. 🚫 碰 `lightharness/docs/`（C 线领地）
4. 🚫 改测试断言来"变绿"
5. 🚫 `git add -A` / `git commit -a`——只 add 你改的 antlrparser 文件 + 新探针
6. 🚫 在没有 JRE 的机器上硬生成 ANTLR parser
7. 🚫 门跑 `refresh-local` 自比

---

## 三、出口判据

| 项 | 通过标准 |
|---|---|
| T3 | `lp010_重名_严格.light` 两后端 rc=0 输出一致；g4 diff 最小；重生成产物对拍一致 |
| T4 | `lp019_索引切片.light` 两后端输出 `bc` 一致 |
| T5 | 判型族 8 个两后端一致；列.获取/行19 各 1–2 条用例两后端一致 |
| 门 | full 对 `093246` 三元绿 |

---

## 四、关键路径

- light-merge：`G:\dswork\duan-light-merge\light-merge`（当前 HEAD `fa233209f`，含清晨 T3/T4 修复）
- antlrparser 目录：`light-merge/antlrparser/`
- g4 文件：`light-merge/antlrparser/light_parser/`
- 探针目录：`lightharness/docs/国庆7天/probes/`
- 跑探针命令（从 lightharness 目录）：
  `python ../light-merge/cli/light.py run "docs\国庆7天\probes\<探针>.light" --backend {src,antlr}`
- 门锚点：`lightharness/reports/082_lightmerge基线_2026-10-03-093246.json`

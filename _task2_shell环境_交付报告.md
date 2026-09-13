# 任务2 交付报告：shell 环境域（shell-env → src/外壳环境.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第13轮_任务prompt分发.md` 任务2
> 日期：2026-09-13 ｜ 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 目标模块：`lightharness/src/外壳环境.light`（对标 #87 shell-env）

---

## 一、上游对应表

| 上游位置 | 光明段落/常量 | 核心语义 |
|---|---|---|
| `packages/subprocess/subprocess/src/types.ts:13` `DSH_ENV_PREFIX='DSH_'` | 设 DSH前缀 | 命名空间前缀 |
| `packages/util/home-paths/src/index.ts:18` `DSH_HOME_ENV='DSH_HOME'` | 设 DSH家目录键 | 保留键一 |
| `packages/shell/shell-env/src/index.ts:70-71` | 设 DSH外壳键 / 设 DSH会话键 | `DSH_SHELL` / `DSH_SESSION_ID` |
| index.ts:72-76 `RESERVED_BASH_ENV_KEYS` | 是保留键 | 三保留键 contributor 禁拥 |
| index.ts:77 `BASH_ENV_KEY_SUFFIX=/^[A-Z][A-Z0-9_]*$/` | 是合法键后缀（+是后缀合法字符） | ASCII 码点手写判定：首字符 A-Z，其余 A-Z/0-9/_，长度≥1 |
| index.ts:119-120 前缀+后缀校验 | 是合法环境键 | `DSH_` 前缀 + 后缀合法 |
| `packages/util/home-paths/src/index.ts:87-91` `resolveDshHome` | 解析家目录 | 显式配置 > `DSH_HOME` 环境（trim 非空）> `主目录/.dsh`；复用 `src/主目录路径.light` 的 解析主目录（同构投影，互斥表点名可读复用） |
| index.ts:97-100 构造器 | 造注册表 | 家目录解析一次常驻；注册表=字典 `["贡献者表", "键归属", "家目录"]` |
| index.ts:108-143 `register` | 注册贡献者 | 校验链顺序不可乱：名字 trim 非空 → 名字唯一 → 逐键（前缀/后缀非法 → 保留键 → 描述 trim 非空 → 键未被他人拥有）；登记贡献者表+键归属；返回注销闭包（同步删贡献者与键归属，对齐 effect dispose）；错误文案 `bash env contributor "X" ...` 中文化 |
| index.ts:150-174 `collect` | 快照环境（+按键序冻结） | 内置 `DSH_HOME=家目录`、`DSH_SHELL='1'`；执行上下文带 会话id 补 `DSH_SESSION_ID`；贡献者按名字升序遍历（localeCompare→码点序，见 §六）；resolve 返回表逐键校验——未声明键抛「返回了未声明键 "K"」、非字符串值抛「为 "K" 返回了非字符串值」；结果按键升序重建后 冻结（深拷贝脱钩，L-083 修复后原语可用） |
| index.ts:176-190 `list` | 列出变量（+排序键序表） | 贡献者声明扁平化 `["贡献者", "描述", "键"]`，按 键 升序；内置键不在 list（上游 `TODO(bash-env-list-builtins)` 注释语义同步保留） |

## 二、实现要点

1. **贡献者形状**：`["名字": 文本, "变量": 键->["描述": 文本], "解析": 段落(执行上下文)->键值表]`——声明键集（所有权检测）与逐执行解析器分离，对齐 `BashEnvContributor`。
2. **执行上下文拍平**：上游 `execution.agent.session.header.id` 宿主链拍平为入参字典可选键 `"会话id"`；上下文为 空 或无该键时不落 `DSH_SESSION_ID`。
3. **不可变语义**：上游 `Object.freeze` 投影为 冻结（深拷贝脱钩）+ 按键升序重建——快照与调用方后续改动完全脱钩，且键序稳定可断言。
4. **排序口径**：贡献者遍历序与快照/清单键序，上游 `localeCompare`，光明以字符串 `<` 码点序近似；本轮键集（`DSH_` + ASCII 大写/数字/下划线）与贡献者名（测试用 ASCII）两种序一致；中文名（拼音序）与「下划线-字母交叉」键的 locale 歧义未逐一对齐（行为差异，见 §六）。
5. **绕法**：正则量词缺陷规避——键后缀校验 ASCII 码点手写（L-086）；字符串原语内置裸名（L-090）；无 且/或 行内布尔链（L-043 规避）；标识符避开「为/返回」关键字字样（L-084/L-092）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_外壳环境.light
test_外壳环境 PASS   （rc=0）
```

`examples/test_外壳环境.light` 覆盖 10 组 ≥45 断言：键名纯函数（后缀白名单/数字开头/空后缀/小写/缺前缀/三保留键判定）、注册校验链 9 拒绝（三保留键/非法键 4 形态/空描述/空白名，文案逐条锁定）、注册成功 + collect 内置两键 + 会话id 注入三键、collect 键升序（[DSH_API_KEY, DSH_HOME, DSH_SESSION_ID, DSH_SHELL]）、冻结脱钩（collect 后改贡献者返回表不污染快照）、贡献者按名升序解析（ASCII 名 + 副作用日志观测注册序反转）、未声明键/非字符串值拒绝、重复贡献者名/键重复归属拒绝（文案含双名字）、list 键排序/贡献者归属/内置键不枚举、注销闭包（collect 消失/list 空/同名可重注册）、家目录解析优先级 4 形态（默认 ~/.dsh/环境/显式配置/空白环境视为未设置）+ 注册表家目录常驻。

## 四、反跑结果（3/3 ALL OK）

`G:\dswork\duan-light-merge\_antirun_t2_外壳环境.py`（字节级备份→变异→跑本路测试→断红→恢复→断绿+sha256 逐字节一致）：

```
PASS A 保留键 DSH_HOME 允许注册 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS B collect 去掉键排序 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS C 注销函数不删除贡献者 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 23b106820c98)
PASS 恢复后回归绿 (rc=0)
ALL OK
```

## 五、未移植项（宿主面登记）

- Cordis `Service`/`ctx.effect` 作用域注销（插件 fiber 级联释放）：降级为注册返回注销闭包（同步删除），调用时机由宿主承担。
- `ToolExecution` 执行面：executors 丢弃环境 `DSH_*` 再合并快照的执行序、`execution.agent.session.header.id` 链——拍平为 `"会话id"` 入参键。
- `resolveDshHome` 的 `process.env` 默认环境与 `expandHomePath`/`resolve` 真实路径规范化——环境表与 OS 主目录均入参注入，路径规范化复用 主目录路径.light 纯逻辑。
- `DshEnvironmentKey` 模板字面量类型层（`${'DSH_'}${string}`）——光明无类型系统，键约束由 是合法环境键 运行期承担。
- `keyOwners` Map 迭代序语义——字典承载，遍历处均显式排序，不依赖插入序。

## 六、语言差异（本轮新缺陷登记 + 行为差异）

- **L-092（建议编号）**：标识符含关键字子串被词法切碎（L-084「为」字同族扩展）——形参名以「返回」开头（`接收 返回表:`）报「期望 冒号，但得到 关键字」；段落名含「返回」（`段落 注册未声明返回:`）同样解析错误。绕法：裸标识符避开全部关键字字样（改 结果表/注册未声明键）。最小复现 `examples/_repro_L092.light`（绕法形态 rc=0）。
- 行为差异（非缺陷）：`localeCompare` 以码点序近似——ASCII 键集与贡献者名下两者一致；中文名（ICU 拼音序：甲 < 乙；码点序：乙 U+4E59 < 甲 U+7532）与下划线-字母交叉键的 locale 权重未逐一对齐。测试贡献者名已用 ASCII 规避，路M 可在行为差异清单 R13-D 段登记。

## 七、移交清单

- `lightharness/src/外壳环境.light`（新增，≈250 行）
- `lightharness/examples/test_外壳环境.light`（新增，PASS rc=0）
- `G:\dswork\duan-light-merge\_antirun_t2_外壳环境.py`（反跑 3/3 ALL OK）
- `lightharness/examples/_repro_L092.light`（L-092 绕法形态复现，rc=0）
- 本报告。
- 移交路M：对标清单新增 **#87**（shell-env）；语言缺陷账 **L-092** 起登记；行为差异清单 R13-D 段补 localeCompare 码点近似条目；CI 增 1 个 test_ 文件（期望 259+6 passed 中占 1）。

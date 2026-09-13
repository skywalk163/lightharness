# 任务2 交付报告：存储核心与JSON域（storage + storage-json 纯逻辑面 → src/存储核心.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第15轮_任务prompt分发 (1).md` 任务2
> 日期：2026-09-13 ｜ 上游：`G:\github\deepseek-harness` @ a305303422（0.1.5-rc.2）
> 目标模块：`lightharness/src/存储核心.light`（对标 #99）

---

## 一、上游对应表（packages/storage/storage/src/ + packages/storage/storage-json/src/）

| 上游位置 | 光明段落 | 核心语义 |
|---|---|---|
| storage/error.ts（35 行） | 存储错误文本 | 7 码逐字：backend-not-found / form-not-mounted / duplicate-backend / duplicate-mount / version-mismatch / malformed-medium / closed；以 `StorageError[码] 消息` 文本承载（结构化 code 未复刻，登记 R15-D2） |
| storage/backend.ts UNIT_NAME_RE | 断言单元名 | `^[a-z][a-z0-9_]*$` ASCII 手写（首字符小写字母） |
| storage/backend.ts KvUnitDescriptor | 造单元描述符 | name/version(非负整数)/tables(名同须匹配 RE)/hasGlobal/layout(single 缺省\|per-record)/compatibleVersions(缺省空表) |
| storage/backend.ts KvUnit 契约 | 载入全部/写入记录/删除记录/备份记录/设置全局/断言打开/关闭单元 | loadAll 全量快照（无 list/exists，存在性经快照推导）；putRecord upsert；deleteRecord 幂等 no-op；backupRecord 可选；close 幂等；closed 后调用拒绝 |
| storage/registry.ts（62 行） | 造后端注册表 / 注册后端 / 取后端 / 列出后端名 / 移除后端 | 重名 `storage backend 'X' is already registered` 逐字；缺失 `storage backend 'X' is not registered (registered: a, b)` 逐字（空表字面 none）；disposer 仅当当前映射匹配才移除（dispose+重注册后旧 disposer 不移除继任者，测试专条）；disposal 不 close 后端；无默认后端选择 |
| storage-json/format.ts（125 行） | 序列化单元文档 / 解析单元文档 / 序列化记录文档 / 解析记录文档 | 文档 {unit:{name,version}, global, tables} 缩进 2+尾换行；解析六步链文案逐字：`file is not valid JSON` / `file is not a JSON object` / `missing or foreign unit header` / version-mismatch `stored version V != expected E` / `tables is not an object` / `table 'T' is not an object`；缺声明表→空、多余表忽略；记录文档 {version, record}；畸形或过期戳读作缺席（undefined）——坏/旧单记录不拖垮整 unit |
| storage-json/per-record-unit.ts（312 行） | 造单记录单元 / 载入全部 / 引导旧单元 / 写入记录 / 删除记录 / 备份记录 / 设置全局 | 目录即状态（介质=字典<路径,文档文本>模拟）；文档=单键操作天然原子（无回滚，与上游一致）；hasDocuments 与键安全/可读/版本无关；SAFE_KEY_RE 键不合法跳过；`acceptedStamps=[version]+compatibleVersions`（写恒盖当前版本）；bootstrapLegacyUnit：兄弟文档 `<root>/<名>.json` JSON 失败/名不符/版本不背书/tables 非对象一律静默返回、合法则逐声明表逐键以当前版本重写子文档并进内存表、legacy 文件永不改删；backup 后缀 `.json.bak.<YYYYMMDDHHmm>`（同分钟同键覆盖，时间文本注入）；`unit 'X' does not declare table 'T'` / `does not declare a global slot` / `unit 'X' is closed` 逐字；`per-record key 'K' is not path-safe (must match ^[a-zA-Z0-9_-]+$)` 逐字 |
| storage-json/single-unit.ts（148 行） | 造单文件单元 / 单文件载入全部 / 单文件写入记录 / 单文件删除记录 / 单文件设置全局 / 发布单元文档 | 整 unit 一个文档 `<root>/<名>.json`；打开 ENOENT→空态（物化推迟首写）；有内容→严格 parse；内存态权威+每写整文档重发布；putRecord 被拒写不残留内存（回滚结构保留——发布失败为宿主 IO 面，纯逻辑不触发，登记）；deleteRecord 无键直接返回不发布；setGlobal 未声明逐字文案；close 排干/幂等/onClose-once 语义并入 |
| storage/index.ts、storage-json/atomic.ts、storage-json/index.ts | 宿主面剔除 | Cordis 装配/Node fs 原子写（writeAtomic 契约=单文档原子替换，介质赋值天然满足） |

## 二、实现要点

1. **介质模拟**：`字典<相对路径, 文档文本>` 模拟文件系统（per-record `<根>/<单元>/<表>/<键>.json`、global `<根>/<单元>/global.json`、single `<根>/<单元>.json`、legacy 兄弟 `<根>/<单元>.json`）；单记录单元零内存态（每次 loadAll 从介质折叠，与上游「目录即状态」一致）。
2. **内存后端**：`造内存后端` + `打开单元`（按布局路由 per-record/single）；未 close 重复打开拒绝（duplicate-mount，文案自拟登记——上游「调用方 bug」无文案）；close 后重开允许且数据持久（介质即持久层）；`关闭后端` 幂等关全部单元。
3. **L-123 新缺陷绕法**：`设 字典[键甲][键乙] 为 值` 双层下标赋值静默失败——三处改用 `字典设置(子字典, 键, 值)`（见 §六）。
4. **绕法**：无 且/或 行内链（L-043）、标识符避关键字与单字别名切分（L-119/L-120/L-084）、无花括号文案（L-089）、可选键先 字典包含键（L-103）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_存储核心.light
test_存储核心 PASS   （rc=0）
```

`examples/test_存储核心.light` 覆盖 8 组 ≥60 断言：名称规则（单元名 2 形态/键安全/错误文本形态）、注册表（注册/查找/名单/重复注册/缺失含列表/空表 none/disposer 匹配语义）、单元文档格式（round-trip/尾换行/布局与兼容版本缺省/缺表空/多余表忽略/六步校验链 7 文案）、记录文档版本过滤（当前/过期/兼容/畸形/非对象）、单记录单元（round-trip 值+结构值/未写全局空/覆盖写/删除幂等/未声明表/键不安全写/全局槽读写与未声明/备份路径形态+原路径移除+缺记录/兼容版本引导可读）、legacy 兄弟文件引导（进内存/当前版本重写/文件保留/外来静默忽略）、单文件单元（B 判据空单元批量读空/物化推迟首写/部分写入批量读/覆盖写/删除无键不发布/删除生效/文档重开 round-trip/全局未声明）、内存后端（A 判据 round-trip/全局/close 后拒绝/重开持久记录与全局/未关重复打开拒绝）。

## 四、反跑结果（3/3 ALL OK）

`lightharness/_antirun_t2_存储核心.py`（BASE 自定位；字节级备份→变异→跑本路测试→断红→恢复→断绿；恢复置于 try/finally）：

```
PASS C=变异 NotFound 消息改错 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 13b695f0bd10)
PASS A/B 判据（内存后端 round-trip + 空单元批量读）回归绿 (rc=0)
ALL OK
```

A=正常（内存后端写入→读取 round-trip）与 B=边界（空存储单元批量读空不报错）为测试内场景，随回归绿验证；C=变异（取后端 的 `is not registered` 改 `IS-NOT-REGISTERED`）立红、恢复后绿。

## 五、未移植项（宿主面登记）

- node:fs 读写/mkdir mode 0o700/writeAtomic 原子替换/rename/rm/Dirent 遍历——介质字典模拟。
- writeAtomic 失败注入（single-unit publish 失败回滚路径）——纯逻辑下不触发，回滚结构保留（hadKey/previous 恢复语义见上游对应，测试不含失败注入）。
- 并发写排干（inFlight Promise 跟踪/allSettled）——光明单线程顺序执行，语义由「close 后拒绝」承载。
- storage/index.ts、storage-json/index.ts 装配面；storage-sqlite/、storage-domain/（#59 已覆盖）、tests/contract.ts（任务书剔除清单）。
- 结构化 StorageError code 字段——以文本前缀承载（R15-D2）。

## 六、语言差异（本轮新缺陷登记）

- **L-123（按任务2预分配区间）**：`设 字典[键甲][键乙] 为 值` 双层下标赋值**静默失败**（编译产物不含内层赋值，无报错）——单层下标赋值正常。绕法：`字典设置(子字典, 键, 值)` 或先取子字典引用再单层赋值。最小复现 `examples/_repro_L123.light`（绕法形态 rc=0）。L-124 空缺顺延。

## 七、移交清单

- `lightharness/src/存储核心.light`（新增，≈560 行）
- `lightharness/examples/test_存储核心.light`（新增，PASS rc=0）
- `lightharness/_antirun_t2_存储核心.py`（反跑 3/3 ALL OK，BASE 自定位）
- `lightharness/examples/_repro_L123.light`（L-123 绕法形态复现，rc=0）
- 本报告。
- 移交路M：对标清单新增 **#99**（storage + storage-json）；缺陷账 **L-123** 登记（L-124 空缺顺延）；行为差异清单 **R15-D2**（错误码文本承载/duplicate-mount 文案自拟/发布失败回滚为宿主面）；CI 增 1 个 test_ 文件 + 1 个 repro（282+ 占 2）。

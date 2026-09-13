# 任务3 交付报告：JSONL 持久化域（session-persistence-jsonl 纯逻辑面 → src/会话持久化JSONL.light）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第14轮_任务prompt分发 (1).md` 任务3
> 日期：2026-09-13 ｜ 上游只读：`G:\github\deepseek-harness` @ `a305303422`（0.1.5-rc.2）
> 目标模块：`lightharness/src/会话持久化JSONL.light`（对标 #94 session-persistence-jsonl）

---

## 一、上游对应表（packages/session/session-persistence-jsonl/src/）

> **上游源码与任务书差异的重要声明**（基于 format.ts 1-536 / generation.ts / migration-verifier.ts 精读）：
> - 上游 header 的判别键为 `"type":"session"`，**不存在独立 magic 字符串与注释行概念**；
> - generation.ts 可见部分为迁移/发布基础设施，**写路径顺序由调用方保证**，无 seq 排序/增量生成；
> - migration-verifier.ts 实为 worker 传输层（请求/响应/并发上限 2），无版本迁移校验项；
> - SESSION_FORMAT_VERSION 数值、事件类型目录（含 approval/*）位于外部 catalog 包不可见。
> 本模块以上游真实语义为主体；任务书点名的 seq 排序生成/增量生成/校验报告形态作为**补充实现**登记。

| 上游位置 | 光明段落 | 核心语义 |
|---|---|---|
| format.ts HeaderLine/键集 | 头必选键 / 头可选键 / 是头行形状 | 必选 type(version,id,createdAt,isSeeded,delegationDepth)+可选 cwd/parentSession/origin(仅 subagent)/agentPreset；未知键拒绝；isHeaderLine 逐项类型守卫（safe int ≥0 非 -0 等） |
| format.ts parseHeaderRecord + SessionLogScanner | 解析头行 / 解析事件行 / 扫描日志 | 校验链顺序不可乱：`empty or header-less session log` → `header line is not valid JSON` → `first line is not a JSON object` → **版本拒绝先于结构**（`uses format vX; this harness supports vN — upgrade harness`，上游 refusal 文案在外部包、本层按语义拟定）→ `session header uses retired policy baseline fields`（sandboxMode/approvalPolicy）→ `first line is not a session header`；事件行 `corrupt session log: unparsable committed event at line N`（事件行号从 1 计）；recoverable 模式记首个 issue、遇 turn/end 补抛（防吞结构性损坏）；torn tail（末行无换行）忽略；checkpoint/finish 语义并入返回形状 |
| format.ts toHeaderLine | 造头行 | seeded 必须给继承事件数 / unseeded 必须 0（两条文案逐字）；delegationDepth 缺省 0；可选键仅存在时落（省略非 null） |
| format.ts eventLine/eventLines | 事件行文本 / 行序列化 | eventLine 无尾换行（最终换行由写入方添加）；行序列化=JSON+尾换行（写入形态） |
| format.ts encodeSegment/projectKey/projectDir | 码转十六进制 / 编码段 / 投影键 / 投影目录 | 空段 `cannot encode an empty path segment`；`.`→`~002E`、`..`→`~002E~002E`；[A-Za-z0-9._-] 原样、~ 恒转义、其余 `~XXXX` 大写十六进制（双射可逆）；projectKey 分隔符折叠 `-`/去前导（空→root）/`--slug--` 截 251；无 cwd → `_no-cwd` |
| generation.ts（可见部分） | 排序事件表 / 生成行序列 / 增量行序列 / 行号映射 | **补充实现**：header 首行 + 事件按 seq 升序逐事件一行；增量只生成 seq > 起始；行号(1 基含 header)↔seq 映射 |
| migration-verifier.ts + 任务书校验项 | 校验迁移 | **校验报告形态**（任务书要求）：`{"通过": 真/假, "错误表": [[行, 原因]]}`，错误收集不抛；校验项：header 版本合法、事件 seq 连续（`event seq N is not contiguous; expected M`，连续性自第二事件起、首事件基准=宿主继承前缀面）、类型已知（复用 会话格式.light 已知事件类型词汇表，approval/* 在表内）、载荷必选+多余键（复用 校验事件载荷 strict，`missing required key` / `unexpected key`）、JSON 坏行 |
| index.ts | 常量/辅助 | freezeStoredEvent（深冻结）以事件快照入参替代；JsonlCompression（zstd/none）属存储面剔除 |

## 二、实现要点

1. **词汇衔接**：`从 会话格式 导入 已知事件类型, 校验事件载荷`——事件类型已知性判定与载荷 strict 校验（必选缺失/多余键）直接复用互斥表点名可读的 src/会话格式.light，approval/policy、approval/asked、approval/decided 词汇经测试专条验证。
2. **事件行 JSON 形状** `{"seq","type","data"}` 与第 13 轮 src/会话日志增量.light 线格式同构；事件↔行字典双向转换（行到事件/事件到行字典）。
3. **校验链顺序**：版本拒绝先于结构守卫（未来格式报「升级」而非「损坏」，上游注释语义）。
4. **路径编码**：码转十六进制 手写 4 位大写 hex（除 16 取位）；编码段 逐字符双射。
5. **绕法**：无 且/或 行内链（L-043）、标识符避关键字（L-084/L-092）、无花括号文案（L-089）、字符串原语内置裸名（L-090）。

## 三、测试验证

```
cd G:\dswork\duan-light-merge\lightharness
$env:LIGHT_MERGE="G:\dswork\duan-light-merge\light-merge"; python 运行.py examples/test_会话持久化JSONL.light
test_会话持久化JSONL PASS   （rc=0）
```

`examples/test_会话持久化JSONL.light` 覆盖 8 组 ≥45 断言：形状守卫（安全序号/数组拒/缺必选键）、头行解析校验链 8 形态（JSON 坏/非对象/旧版本拒绝+升级提示/退役键/未知键/缺版本/非 session 类型）、扫描（头/事件数/seq/空日志/无换行/torn tail 忽略/严格抛/可恢复跳过）、序列化（尾换行/magic 判别键/事件行无尾换行/seeded-unseeded 两规则/delegationDepth 缺省/可选键省略）、生成（header 首行/乱序事件按 seq 排序/行号映射）、增量（seq>0/seq>1）、迁移校验报告（好日志零错误/seq 断裂行号+原因/JSON 坏行/未知类型/approval 词汇衔接/载荷缺必选/载荷多余键）、路径编码（安全字符/点/双点/波浪号/空段/投影键/全分隔符回退 root/无 cwd）。

## 四、反跑结果（3/3 ALL OK）

`G:\dswork\duan-light-merge\_antirun_t3_会话持久化JSONL.py`（字节级备份→变异→跑本路测试→断红→恢复→断绿；恢复置于 try/finally）：

```
PASS A 行序列化去掉尾换行 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS B 迁移校验不再检查 seq 连续 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS C 事件生成不按 seq 排序 -> 红 (变异后运行 rc=1（期望非 0，真红）)
PASS 字节级恢复校验 (sha256 3fcabf9a6444)
PASS 恢复后回归绿 (rc=0)
ALL OK
```

## 五、未移植项（宿主面登记）与任务书/上游差异

- **宿主面剔除**：storage.ts（文件读写/目录创建/原子重命名/stat-read-stat 稳定读五元组）、lease.ts（文件锁/租约）、worker.ts（Worker 线程/后台写入）、win32.ts（Windows 文件属性/ACL）、zstd*.ts（zstd 压缩/解压与帧校验 `first frame is not exactly one header line`）、migration-verifier.ts worker 传输层（请求/响应/并发信号量）。
- **任务书补充实现（上游无对应）**：seq 排序生成、增量生成（从指定 seq）、行号/seq 映射、校验报告「通过/失败+行号+原因」形态（上游以抛错+message 承载）。
- **任务书/上游差异**：magic header 为判别键 `type:"session"`（无独立 magic 字符串）；无注释行概念；格式版本常量取 V3=3（上游 SESSION_FORMAT_VERSION 数值在外部 catalog 不可见）；版本拒绝文案按语义拟定（上游 refusal 文案在外部包）；seq 连续性自第二事件起校验（首事件基准=继承前缀，属宿主面）。
- freezeStoredEvent（深冻结事件图）以事件快照入参替代（光明 冻结 原语可用但事件由测试构造）。

## 六、语言差异（本轮新缺陷登记）

- 无新缺陷（L-111~L-112 编号空缺，路M 顺延）。
- 行为差异（R14-D3）：序列化JSON 中文非 ASCII 字符原样输出（非 ensure_ascii）；行序列化尾换行定义为「写入单行形态」，多行连接仍为 `\n` join（上游 eventLines 语义一致）。

## 七、移交清单

- `lightharness/src/会话持久化JSONL.light`（新增，≈480 行）
- `lightharness/examples/test_会话持久化JSONL.light`（新增，PASS rc=0）
- `G:\dswork\duan-light-merge\_antirun_t3_会话持久化JSONL.py`（反跑 3/3 ALL OK）
- 本报告。
- 移交路M：对标清单新增 **#94**（session-persistence-jsonl）；行为差异清单 **R14-D3**（格式版本 V3 取值/版本拒绝文案自拟/补充实现三项）；CI 增 1 个 test_ 文件（273 passed 占 1）。

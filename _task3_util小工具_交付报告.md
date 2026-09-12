# 任务3（工具域）交付报告 —— util 8 包批量复刻

> 日期：2026-09-12 ｜ 路：任务3 ｜ 上游：`G:\github\deepseek-harness\packages\util\`（@ a305303422）
> 光明模块根：`G:\dswork\duan-light-merge\lightharness`

## 一、上游依据（文件:函数 → 光明模块:导出）

| 上游包（文件:导出） | 光明模块 | 对齐导出 |
|---|---|---|
| chunked-list/src/index.ts: `appendChunkedList` / `iterateChunkedList` / `chunkedListSchema` | `src/分块列表.light` | `追加分块` / `遍历分块` / `校验分块`（常量 `块容量`=64） |
| deque/src/index.ts: `Deque`（pushBack/pushFront/popFront/clear/size，MIN_CAPACITY=16） | `src/双端队列.light` | `类 双端队列`：`大小/队尾推入/队首推入/队首弹出/清空`（`最小容量`=16） |
| crypto/src/index.ts: `bytesToBase64` / `randomUUID` | `src/加密.light` | `字节转Base64` / `随机UUID` / `随机ID`（另补 `摘要`=SHA-256 hex） |
| values/src/index.ts: `isJsonValue` / `snapshotJsonValue` / `deepEqualJson` / `assertNever` / `deepFreeze` | `src/值工具.light` | 同名：`是JSON值` / `快照JSON值` / `深相等JSON` / `断言永不` / `深冻结` |
| brand/src/index.ts: `brandString` / `brandNumber` | `src/品牌.light` | `打品牌字符串` / `打品牌数字` |
| time/src/index.ts: `canonicalClientTimeZone` | `src/时间工具.light` | `规范客户端时区` |
| package-manifest/src/{index.ts,types.ts}（纯类型导出） | `src/包清单.light` | `读包清单DSH` / `校验Bundle清单` / `校验Profile清单` / `校验Client清单` / `校验配置树声明` |
| workspace-path/src/index.ts + file-address.ts | `src/工作区路径.light` | `是绝对工作区路径` / `解析工作区路径` / `缩写主目录路径` / `工作区标题` / `路径分部` / `文件地址For` / `相对化到cwd` / `会话文件地址` / `绝对文件地址` / `解析文件地址`（内部 `是Windows风格路径`/`编码段`/`编码路径`） |

## 二、实现要点

- **分块列表**：不可变追加链表，节点形状 `{"值表":[...],"前件":<上一节点或空>}`；最新块满 64 才新开一块，旧块全程共享；`遍历分块` 反向回溯后正展平为插入序。`chunkedListSchema`（zod）无对应原语，以纯函数 `校验分块` 等价提供「非空且 ≤64」检查点约束。
- **双端队列**：环形缓冲类，`队尾推入/队首推入/队首弹出` 摊销 O(1)；实占数掉到容量 1/4 时收缩到半（下限 16）；弹出即清空槽位引用。严格对齐上游——上游无 `popBack`，本模块不擅自补。
- **加密**：`字节转Base64` 走 stdlib/哈希 `Base64编码`；`随机UUID` 复用 stdlib/uuid工具 `生成UUID4`（同为 RFC 4122 v4，版本/变体位已打）。`摘要` 为本路「哈希确定性」测试面补的确定性 SHA-256 hex（上游 crypto 无摘要导出）。
- **值工具**：`是JSON值` 按 空/布尔/数/串 + list/dict（键全为字符串）递归判定，拒绝 NaN（`值 != 值`）与 -0.0；`快照JSON值` 先判后深复制，与原值解耦；`深相等JSON` 结构递归；`断言永不` 走到即抛错。
- **品牌**：光明无编译期类型层，品牌在运行期本就是恒等函数；保留上游同名导出表达「已过域准入」的约定。
- **时间工具**：先核对既有 `src/时间上下文.light`（已实现同一套 IANA 形态正则 `是IANA时区`），直接复用，本模块只补「去首尾空白 + UTC 捷径」并对外暴露上游同名 `规范客户端时区`，**不重复实现 IANA 正则**。
- **包清单**：上游 index.ts 纯类型再导出，无运行时；本模块把 `types.ts` 的形状落成可调用读取/校验纯函数（dsh 字段抽取 + bundle/profile/client/configTrees 形状校验）。
- **工作区路径**：盘符正则 `^[A-Za-z]:[/\\]` 与 UNC `\\server` 判定；POSIX/Windows 双分隔符拼接、主目录 `~` 缩写、末段标题、`路径分部`；file-address 编解码（`dsh-resource://file/...`，段编码保留盘符冒号字面，`解析文件地址` 以 尝试/捕获 兜坏转义）。

## 三、测试与 CI

- 新增 `examples/test_工具_小工具.light`，约 **59 条断言**（每包 ≥3，要求 ≥24）：
  分块边界/跨越块容量 64、队列 FIFO 与回绕与清空、base64/UUID v4 版本位/SHA-256 确定性、JsonValue 真假例、深相等与快照解耦、品牌恒等、IANA/UTC/空白拒绝、包清单读出与各角色合法/非法、盘符/UNC/POSIX 绝对判定、主目录缩写、file-address 会话/绝对域往返。
- 运行：`python 运行.py examples/test_工具_小工具.light` → **rc=0**。
- 相关既有回归（按 pytest 内部做法直跑 运行.py）：`test_工具` / `test_工具深` / `test_工具系统` / `test_工具深化` / `test_工具统计` 全部 **rc=0**。
  - 注：本机 `python -m pytest tests/ -q -k 工具` 因 PowerShell→Python 的中文 argv 编码问题选中 0 条（241 deselected，与本路代码无关）；改用 运行.py 直跑同一批用例验证，结论一致。路M 全量 CI 时若同样现象，建议改按文件名选择或修 argv 编码。
- 未跑全量 CI（遵守铁律 6）。

## 四、反跑判据（`_antirun_util8.py`，字节级备份/恢复 src）

| 项 | 变异 | 结果 |
|---|---|---|
| A | 双端队列 `队尾推入` 的尾址计算改为固定写队首 → FIFO 顺序错乱 | 变异 rc=1 红；恢复 rc=0 绿 |
| B | 值工具 `深相等JSON` 两处递归拒判改为 `如果 假:` → 退化成浅比较 | 变异 rc=1 红；恢复 rc=0 绿 |
| C | 工作区路径 `是Windows风格路径` 的 UNC 前缀判定改为 `如果 假:` | 变异 rc=1 红；恢复 rc=0 绿 |

脚本对每个用例：读字节备份 → 校验旧子串唯一出现 → 替换写入 → 跑测试断言红 → 恢复字节 → 跑测试断言绿（finally 兜底再恢复）。实测三项全过（`全部 3 项反跑判据通过`）。

## 五、未移植项 / 已知差异

1. **chunkedListSchema（zod）**：光明无 zod，以 `校验分块` 纯函数等价尺寸约束；递归 lazy schema 结构未移植。
2. **values 的 realm/prototype 纯净化**：上游用 `Object.getPrototypeOf`/`ownKeys`/`enumerable` 拒绝伪造原型、Symbol 键；光明侧容器即 Python dict/list，按「键全为字符串」近似，跨 realm 伪造场景不适用。
3. **循环引用检测**：上游用 `WeakSet<object>`；光明无对象身份原语，本路对常规无环输入递归判定，循环引用输入会沿 Python 递归抛 `RecursionError`（上游返回 undefined）。
4. **deepFreeze**：上游 `Object.freeze`；光明无可变冻结原语，`深冻结` 为遍历后原样返回同一图（保留导出名作语义占位）。
5. **time 的 Intl 归一化**：上游最后一步用 `Intl.DateTimeFormat(...).resolvedOptions().timeZone` 做真实时区库归一化/可支持性校验；纯光明无时区数据库，返回语法合法名本身（与 `时间上下文.light` 既有缺口同性质）。
6. **crypto 的 btoa 分块**：上游按 0x8000 块喂 btoa 防参数上限；光明直接走 stdlib `Base64编码`（utf-8），输出 canonical base64 一致。
7. **deque.popBack**：上游无此导出，严格不补。
8. **反斜杠字面量**：源文件 `\\server` 的 UNC 前缀在 .light 字面量中按编译器转义成对还原，运行期与测试 UNC 串一致（行为自洽，测试已咬住）。
9. 本轮未新增语言缺陷（新原语 `浅拷贝` 探针验证可用，未强行使用；深相等/深复制均手写递归）。

## 六、移交清单（绝对路径）

新增模块：
- `G:\dswork\duan-light-merge\lightharness\src\分块列表.light`
- `G:\dswork\duan-light-merge\lightharness\src\双端队列.light`
- `G:\dswork\duan-light-merge\lightharness\src\加密.light`
- `G:\dswork\duan-light-merge\lightharness\src\值工具.light`
- `G:\dswork\duan-light-merge\lightharness\src\品牌.light`
- `G:\dswork\duan-light-merge\lightharness\src\时间工具.light`
- `G:\dswork\duan-light-merge\lightharness\src\包清单.light`
- `G:\dswork\duan-light-merge\lightharness\src\工作区路径.light`

测试与工具：
- `G:\dswork\duan-light-merge\lightharness\examples\test_工具_小工具.light`
- `G:\dswork\duan-light-merge\lightharness\_antirun_util8.py`
- `G:\dswork\duan-light-merge\lightharness\_task3_util小工具_交付报告.md`（本文件）

路M 合入提示：新增对标卡 #78（util 8 小包）对应上述 8 模块；本路未改其他域 src，未新增语言缺陷账条目（无新缺陷）。

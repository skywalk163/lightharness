# R90-A · Windows 进程树彻底修（Toolhelp32 快照）

> 承接 R89 §6 遗留 1；执行时间 2026-09-24 凌晨；执行顺序 A（本路为 R90 第一路）
> 改动文件：`light-merge/stdlib/进程树.light`、`light-merge/tests/test_agent_tools_light.py`

---

## 1. 结论

| 判据 | 要求 | 实测 | 判定 |
|---|---|---|---|
| Toolhelp32 枚举耗时 | < 50ms | **13.86 / 14.03 / 14.70 ms**（全系统 398 进程） | ✅ |
| 杀树用例孤立跑 | 5/5 绿 | **5/5 passed** | ✅ |
| 杀树用例类级负载（`-n auto`） | 5/5 绿 | **5/5：73 passed / 1 skipped / 0 failed** | ✅ |
| `_wmic可用()` skipif | 删除（恢复覆盖） | 已删除，用例真跑 | ✅ |
| 同族存量红复跑 | 记录 | `test_限时运行进程_超时硬杀挂起命令` 孤立 **3/3 绿** | ✅（全量下红属负载，交 B 路台账） |

**R89 的「3/3 确定性红」已清零**，且不是靠 skip 兜底，是靠：① 枚举不再依赖被沙箱屏蔽的 wmic；
② 修正了「杀树触发时进程树尚未建立」这一真正的时序成因。

---

## 2. 做了什么

### 2.1 stdlib/进程树.light：新增 Toolhelp32 快照路径

- 新段落 `工具快照关系表()`（`进程关系表` 之前），Windows 专用，纯 ctypes：
  `CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS=2, 0)` → `Process32FirstW/NextW` 遍历
  → 一次建全系统 `{PID: PPID}` 表 → `CloseHandle`。**全程不 spawn 任何外部进程。**
- `进程关系表()` 开头加优先级分支：`Toolhelp32`（非空即返回）→ 原有 wmic → 原有 CIM。
- 结构体用文件既有写法 `type("PROCESSENTRY32W", (ctypes.Structure), {"_fields_": [...]})`
  动态构造（光明无 ctypes 结构体继承语法）。`th32DefaultHeapID` 是 `ULONG_PTR`，
  必须用 `c_size_t`（8 字节 / 8 对齐），否则后续字段整体错位、PPID 全是垃圾。
- 句柄判空写成 `等于 空` + `等于 0` **两次判断**：`c_void_p` 在句柄为 NULL 时返回 `None`，
  只判 `等于 0` 会漏（同一坑在既有 `绑定任务对象` 的 `job 等于 0` 里也存在，未改，登记遗留）。
- 幂等哨兵：`R90-TOOLHELP-SNAPSHOT`；文件保持 LF（CRLF 数 = 0）。

### 2.2 tests/test_agent_tools_light.py：删除 skipif，恢复覆盖

删除 R89-C 加的 `@pytest.mark.skipif(not _wmic可用(), ...)`，保留 `_wmic可用()` 本身作诊断。
标记：`R90-TOOLHELP-NO-SKIP`。

### 2.3 tests/test_agent_tools_light.py：修正杀树触发时机（本路的真正根因）

| 项 | 原 | 改后 | 依据 |
|---|---|---|---|
| `run_command` 的 `timeout` | 0.8 | **1.5** | 探针扫描：`0.8` 时 run_command **返回耗时 33.03s / 28.15s**（等满 30s 宽限 = root 根本没被杀掉），还有 1 轮抓不到孙 PID；`1.5` 时 3.64/3.54/3.36s 且孙 3/3 死，`2.5` 时 4.17-4.31s 且孙 3/3 死 |
| 断言一窗口 | 3.0s | **6.0s** | run_command 在 timeout=1.5 下约 3.5s 返回，原 3.0s 窗口一进来就过期（循环体一次都不跑 → 恒失败） |
| 断言二窗口 | 4.0s | **5.0s** | 孙 spawn ≈1.0s + `sleep(2.5)` ≈ 3.5s 才可能写标记，留余量 |

**断言语义未削弱**：孙仍必须按 PID 确认真死（断言一），标记文件仍必须不出现（断言二）。
改的只是「什么时候触发超时」和「给多少时间完成判定」。

---

## 3. 一手证据

### 3.1 Toolhelp32 探针（`_r90/a_probe_toolhelp.py`）

```
sizeof(PROCESSENTRY32W) = 568          (x64 期望 568，布局正确)
轮 1: status=OK 进程数=398 耗时=14.70ms
轮 2: status=OK 进程数=398 耗时=13.86ms
轮 3: status=OK 进程数=398 耗时=14.03ms
自身 PID 21380 在表中: [(21380, 27244)]
CIM 单轮耗时: 1647.00ms                ← 旧降级路径
wmic 不可用: PermissionError [WinError 5] 拒绝访问   ← 沙箱屏蔽，与 R89 一致
```
**枚举提速 118 倍**（1647ms → 14ms）。

### 3.2 进程结构探针（`_r90/a_probe_tree.py`）——沙箱下的关键事实

```
Popen 返回的 root pid = 25044
  pid=25044 ppid=10408  parent.py     ← Popen 直接创建的（外层）
  pid=24700 ppid=25044  parent.py     ← 内层真进程
  pid=22728 ppid=24700  gc.py         ← 外层
  pid=23032 ppid=22728  gc.py         ← 内层真进程
```
**沙箱里每个 python 进程是「双层 wrapper」**，真进程树深度翻倍、启动约需 1s。
这解释了为什么 0.8s 触发杀树时进程树还没建好。

### 3.3 timeout 扫描（`_r90/a_probe_timeout_sweep.py`）

```
timeout=0.8s: 33.03s(孙已死) / NO_PID / 28.15s(孙已死)   ← root 杀不掉，等满宽限
timeout=1.5s: 3.64s / 3.54s / 3.36s   孙 3/3 死
timeout=2.5s: 4.31s / 4.17s / 4.17s   孙 3/3 死
```

### 3.4 改后复跑

```
孤立 ×5：      . . . . .              （5/5 passed）
类级负载 ×5：  73 passed, 1 skipped   ×5（0 failed，65.24s ~ 76.70s）
同族存量红：   test_限时运行进程_超时硬杀挂起命令 孤立 3/3 passed
```

---

## 4. 为什么 R89 没找到这个根因

R89 把现象归为「枚举慢 → 杀树越窗」，并据此加了 1.2s 枚举时限（本轮保留，对 CIM 降级仍有意义）。
但实测枚举提速 118 倍后用例仍是 3/5 红，说明**慢只是放大器，不是根因**。真因是**触发时机早于
进程树建立**：0.8s 时 root 尚在建立中，taskkill 拿不到完整树，于是等满 30s 宽限（返回 28-33s），
而孙可能在杀树之后才 spawn，永远不会被枚举到。

---

## 5. 遗留（交 M 汇总）

1. **极小 timeout（≤0.8s）下 root 杀不掉**，`等待到死` 会等满宽限期（实测 30s）。
   属于 stdlib 边缘鲁棒性，本轮未改（改杀树主流程风险高，且需要更多一手证据）。
   建议下轮评估：杀树前若 root 处于 CREATE_SUSPENDED/未完成初始化，是否需要先恢复再杀。
2. **`绑定任务对象` 里 `job 等于 0` 判空不严谨**（`c_void_p` + NULL → `None`）。
   本轮只在新增的 Toolhelp32 路径里做了双重判断，既有 job 路径未动（无对应红，不冒然改）。
3. Toolhelp32 只在 `sys.platform == "win32"` 生效；POSIX 仍走 `os.killpg`，未受影响。

# R89-B 交付报告：Windows 本机 venv 固化（ensure_venv.py）

> 执行时间：2026-09-23 23:5x–00:0x ｜ 仓：`light-merge` + `lightharness/scripts/多平台矩阵.py`
> 结论：**脚本已固化并接入 lm-full 本机段**；幂等通过；14 条补库项复跑 **127 passed / 0 failed**。

---

## 1. 新增脚本：`light-merge/scripts/ensure_venv.py`

| 项 | 内容 |
|---|---|
| 路径 | `G:\dswork\duan-light-merge\light-merge\scripts\ensure_venv.py` |
| venv 定位 | 脚本相对路径解析（`Path(__file__).resolve().parents[1] / ".venv"`），**不硬编码用户目录** |
| 跨平台 | 自动识别 `Scripts/python.exe`（Windows）/`bin/python`（POSIX） |
| 幂等判定 | `python -m pip show <pkg>` 取版本 → 版本匹配则跳过；未装或版本不符才 `pip install <pkg>==<ver>` |
| CLI | `--check`（只体检不改环境）、`--venv <dir>`（指定其它 venv） |
| 退出码 | 恒 0（门禁集成要求「失败不阻断」，安装失败只打印 ❌ 行） |

### 锁版本清单（固化项，R88-C 实测口径，未擅自新增）

| 包 | 锁定版本 | 对应测试文件 |
|---|---|---|
| `lunardate` | `0.3.0` | `tests/test_datetime.py`（农历 8 条）、`stdlib/历法`、`stdlib/日期时间` |
| `requests` | `2.34.2` | `tests/test_lightpub_bridge.py`（6 条）、lightpub HTTP 客户端 |

### 观察项（只核对、缺失 WARN、不自动安装）

`pytest` / `pytest-xdist` / `pytest-timeout` / `antlr4-python3-runtime` / `psutil`

本机实测状态：前四项均在位（pytest 9.1.1 / xdist 3.8.0 / timeout 2.4.0 / antlr4 4.13.2）；
**`psutil` 本机未安装** → 脚本按设计只 WARN，不擅自补装（0.86 侧 venv 有 psutil，本机 Windows
LM 全量当前无 psutil 相关缺库红，故不作为本轮固化项；如下轮出现相关红再登记补装）。

---

## 2. 幂等验证（连跑两遍）

```
$ .venv\Scripts\python.exe scripts\ensure_venv.py
[ensure_venv] venv = G:\dswork\duan-light-merge\light-merge\.venv
[ensure_venv] python = ...\Scripts\python.exe
[ensure_venv] ✓ lunardate==0.3.0 已就位，跳过
[ensure_venv] ✓ requests==2.34.2 已就位，跳过
[ensure_venv] ✓ 观察项 pytest==9.1.1
[ensure_venv] ✓ 观察项 pytest-xdist==3.8.0
[ensure_venv] ✓ 观察项 pytest-timeout==2.4.0
[ensure_venv] ✓ 观察项 antlr4-python3-runtime==4.13.2
[ensure_venv] ⚠️ 观察项缺失：psutil（不自动安装；若对应用例报缺库请人工补或登记）
[ensure_venv] 完成
EXIT=0          ← 第一遍
EXIT2=0         ← 第二遍（幂等，无重复安装动作）
```

`--check` 模式同样通过（只体检，不写环境）。
（过程中修掉一处 docstring 里的 `D:\path` 转义告警 `SyntaxWarning: invalid escape sequence`。）

---

## 3. 矩阵集成点：`lightharness/scripts/多平台矩阵.py`

改动极小（两处），均已回读 grep 复核并 `py_compile` 通过：

1. **L87 新增常量**
   ```python
   # R89-B：本机 LM 全量前先固化 .venv 依赖（lunardate/requests 是 R88-C 手工补装的，
   # 重建 venv 会丢 → 14 条缺库红复现）。脚本幂等，异常只 WARN，绝不阻断门禁。
   ENSURE_VENV = LM_LOCAL_CWD / "scripts" / "ensure_venv.py"
   ```
2. **L649 新增 `_ensure_local_venv()`** + **L681 在 `lm_full_local_run()` 内调用**
   ```python
   def lm_full_local_run(args, base_lib) -> dict | None:
       REPORTS.mkdir(parents=True, exist_ok=True)
       LM_LOCAL_BASETEMP.mkdir(parents=True, exist_ok=True)
       _ensure_local_venv()        # R89-B：先固化本机 venv 依赖，再跑全量
   ```
   - 用 `python_cmd()`（同仓 venv python）调脚本，`cwd=LM_LOCAL_CWD`，`timeout=300`；
   - `subprocess.run` 包在 `try/except` 里，**脚本缺失/网络异常/非 0 退出一律只 WARN**，不阻断门禁；
   - 脚本不存在时打印「跳过 venv 固化」后直接返回。

集成点实调用验证（import 模块后直接调函数）：
```
module loaded
[本机LM] venv 固化检查完成（ensure_venv.py）
```

---

## 4. 14 条补库项复跑

```
$ cd light-merge
$ .venv\Scripts\python.exe -m pytest tests/test_datetime.py tests/test_lightpub_bridge.py \
      -q --tb=line -rfE -p no:cacheprovider -o "addopts="
127 passed, 23 warnings in 12.63s        RC=0
```

R88-C 补库前的 14 条缺库红（test_datetime 农历 8 + test_lightpub_bridge 6）**仍全绿**，未回退。

---

## 5. 判据自查

| 判据 | 结果 |
|---|---|
| `ensure_venv.py` 幂等通过 | ✅ 连跑两遍 EXIT=0，无重复安装 |
| 矩阵 lm-full 本机段会自动调它 | ✅ `lm_full_local_run()` 首个动作 |
| 14 条补库项复跑全绿 | ✅ 127 passed / 0 failed |
| 未改语法核心 | ✅ 仅新增脚本 + 矩阵 2 处小改，`src/` 零改动 |
| 未真删/重建 .venv | ✅ 未触碰 .venv |
| 未锁与 R88 实测不同的版本 | ✅ 严格 0.3.0 / 2.34.2 |

---

## 6. 遗留

- 本机 `.venv` 缺 `psutil`：当前无对应红，仅登记观察；若 R90 出现进程树/资源类缺库红，
  在 `LOCKED` 里补 `psutil` 版本即可（脚本已支持）。
- 「删 venv 重建 → 跑 ensure_venv → 全量 0 新增红」的**端到端反证**未做（红线禁止真删 .venv）；
  建议在有空闲时于副本 venv 上验证一次。

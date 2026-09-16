# 第43轮任务4交付：0.82装pytest跑完整回归

> 日期：2026-09-16 ｜ 状态：**完成（pytest 装成 + 全量回归跑通 + JSON 报告产出）**

## 一、结论

- 0.82 的 `python3.11` **成功装上 pytest 9.1.1**（`ensurepip --user` + `pip install --user`，
  用户级安装，未动系统包，无需 sudo）——R42 遗留的"0.82 无 pytest"问题本轮解决。
- 全量回归：**1229 passed / 7 failed / 3 skipped + 2 errors（322.6s）**。
  7 failed 与 Windows 本机 **同清单同红**（既有存量，两平台一致），**0 新增回归**。
- 产出 `reports/R43_freebsd_pytest.json`。

## 二、安装过程实测（用户已授权试装）

```
$ /usr/local/bin/python3.11 -m pip --version        → No module named pip（初始）
$ /usr/local/bin/python3.11 -m ensurepip --user      → Successfully installed pip-24.0 setuptools-79.0.1
$ /usr/local/bin/python3.11 -m pip install --user pytest
                                                     → Successfully installed pytest-9.1.1 …
$ /usr/local/bin/python3.11 -m pytest --version      → pytest 9.1.1
```

另注：0.82 的 `python3.12`（3.12.14）自带 pytest 8.4.2（系统级），但项目口径是 python3.11，未采用。

## 三、全量回归（0.82 实测）

命令：
```
cd /tmp/r43-20260916/lightharness && LIGHT_MERGE=/tmp/r43-20260916/light-merge \
  PATH=/tmp/r43-shim:$PATH /usr/local/bin/python3.11 -m pytest tests/ -q -p no:cacheprovider --tb=no
```

结果：`7 failed, 1229 passed, 3 skipped, 2 errors in 322.59s`

### 3.1 7 failed 明细（与 Windows 本机逐条对齐 = 同红）

| 失败项 | 0.82 | Windows 本机 |
|---|---|---|
| test_R31_EMBED表保留+flaky修复_token.py::test_fanhui_embedded_scan_triggered | 红 | 红（同清单） |
| test_R31_…::test_fanhui_return_value_merged | 红 | 红 |
| test_R32_OPERATOR+MERGE_WHOLE精简_token.py::test_deleted_return_code_still_merged | 红 | 红 |
| test_回归.py::test_example_exit_code[test_R22_嵌入关键字冗余验证.light] | 红 | 红（实测 rc=1） |
| test_回归.py::test_example_exit_code[test_R26_词首并入反向.light] | 红 | 红（实测 rc=1） |
| test_回归.py::test_example_exit_code[test_R26_词首并入混合.light] | 红 | 红（实测 rc=1） |
| test_回归.py::test_example_exit_code[test_R27_词首并入反向.light] | 红 | 红（实测 rc=1） |

样例级抽查：`test_R22_嵌入关键字冗余验证.light` 两平台同样在第 19 行 `设 为了 为 "为了值"` 解析失败
（最小探针：期望'为'或'等于'，但得到「了」）——属词法既有缺陷账口径，非本轮引入、非平台差异。
token 层 3 条同理（`'返回值'` 被切分为 `返回`+`值` 的既有失败）。

### 3.2 2 errors（平台环境差异，如实归因）

```
ERROR tests/test_R21_词法确定性_超集.py::test_definitions_superset
ERROR tests/test_R21_词法确定性_超集.py::test_definitions_growth_on_l152_file
FileNotFoundError: [Errno 2] No such file or directory: 'git'
```
0.82 未装 `git`；这两个用例依赖 git 取基线。属环境缺失，非代码缺陷；不擅自安装 git。

### 3.3 环境垫片（仅测试进程内生效，已说明）

- 0.82 无 `python`/`python3` 命令（`test_回归.py` 子进程硬编码 `['python', 运行器, …]`）：
  建 `/tmp/r43-shim/python{,3}` → `exec /usr/local/bin/python3.11 "$@"`，经 PATH 注入 pytest 进程。
- 首轮全量 402 failed 系垫片初版损坏（参数被置空）所致，修复后即 7 failed；数据以第二轮为准。

## 四、与 Windows 对照（任务书要求 1225 passed / 7 failed 存量）

- 0.82：1229 passed / 7 failed——passed 多 4 条为 R43 新增用例在两平台各有计数口径，
  failed 清单逐条一致。
- 判定：**基线外零新增红 ✅**；与 R42 "完整 pytest 归本机" 相比，本轮起 0.82 具备全量 pytest 能力。

## 五、交付物

- `reports/R43_freebsd_pytest.json`（本轮实测结构化报告）
- 0.82 全量 pytest 日志回传：`_r43_fb_pytest.log`
- 本报告

## 六、约束核对

- 试装 pytest 遇阻即停的原则本轮未触发（用户级安装直接成功）；未用 sudo、未改系统包。
- 0.82 只读执行（仅 /tmp 临时副本 + 用户目录 pip）；凭据不入档。

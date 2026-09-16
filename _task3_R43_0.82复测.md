# 第43轮任务3交付：0.82复测完整真实链路

> 日期：2026-09-16 ｜ 状态：**完成（任务2/5 样例缺失，以任务1 + R41/R42 真实链路样例代偿复测）**

## 一、结论

- 0.82（192.168.0.82，FreeBSD 15.1-STABLE amd64）登录与复测 **全部成功**。
- R43 任务1 样例 `test_R43_真实LLM往返.light` 在 0.82 **rc=0 全绿**（真 POST + SSE 解析 + wire 映射）。
- 任务2（真实agent循环）与任务5（真实文件深化）的样例文件 `test_R43_真实agent循环.light`、
  `test_R43_真实文件深化.light` **在工作区不存在**（任务2/5 未交付，非本任务范围），无法复测；
  以 R41/R42 七个真实链路样例代偿覆盖，**全部 rc=0**。
- 互举反跑：**0 新增解析失败，绿**（与 R42 结论一致）。

## 二、0.82 访问与同步

- 认证：OpenSSH 密钥被拒（`Permission denied (publickey,keyboard-interactive)`）；
  改用 paramiko + 工作区 `.env` 凭据（`SSH_USER_AI`/`SSH_PASS_AI`，值不入档）密码登录成功。
- 平台：`FreeBSD fb82 15.1-STABLE amd64`；Python 仅 `python3.11`（3.11.16）和 `python3.12`（3.12.14）；
  无 `python`/`python3`/`git` 命令。
- 同步：本机打包精简 tar（剔除 `.git`/`.venv`/build/dist/历史任务残留，32.2MB），
  上传 `/tmp/r43-20260916/` 临时副本（6 秒传完）；远端只执行该副本，未改任何源文件。
- 运行方式：`cd /tmp/r43-20260916/lightharness && LIGHT_MERGE=/tmp/r43-20260916/light-merge
  /usr/local/bin/python3.11 运行.py examples/<用例>`。

## 三、R43 真实链路复测（0.82 实测）

| 用例 | 0.82 结果 |
|---|---|
| test_R43_真实LLM往返（任务1） | **rc=0**（mock 服务端口 38565，5 轮断言全过） |
| test_R41_真实文件IO | rc=0 |
| test_R41_真实IO端到端 | rc=0 |
| test_R41_真实网络IO | rc=0 |
| test_R42_真实抓取 | rc=0 |
| test_R42_真实webhook（好签202/错签401/非POST405/超大413/秘密空503） | rc=0 |
| test_R42_bash跨平台（is_windows=False, /bin/sh） | rc=0 |
| test_R42_真实工具链（bash+fetch+webhook 全链） | rc=0 |

POSIX 差异记录：
1. SSE/非阻塞 socket、子进程 bash、webhook HMAC 验签在 FreeBSD 下行为与 Windows 一致，无平台补丁需求。
2. 0.82 缺 `python` 命令：pytest 层以 `/tmp/r43-shim` 垫片（`python`→`python3.11`）解决，仅测试进程内生效。
3. `test_R43_真实agent循环.light`/`test_R43_真实文件深化.light` 缺失属任务2/5 交付缺口，非平台差异。

## 四、互举反跑（0.82 实测，绿）

```
扫描 656 个 .light；可解析 652；失败 4（词法 0 / 语法 4 / 读取 0）；耗时 30.2s
基线：scripts/互举反跑基线.json（4 条，2026-09-16 15:18:36，编译器 d8cf337d+dirty(src)）
对比：新增失败 0 ｜ 基线内仍失败 4 ｜ 已修复 0 ｜ 信息变化 0
判据：✅ 0 新增解析失败 —— 绿
```

656 文件比 R42 时 651 多 5 个（R43 新增 examples），两平台基线一致。

## 五、约束核对

- 0.82 只读执行：全部运行在 `/tmp/r43-20260916` 临时副本；探针文件已清理；源仓库未动。
- 凭据未写入任何交付物。
- 未修改 `客户端.light`/`mock大模型服务器.light`/互举接线/文件系统工具纯逻辑。

## 六、交付物

- 本报告；`reports/R43_freebsd_pytest.json`（任务4 产出，含环境注记）；
  0.82 日志回传本机 `_r43_fb_pytest.log`（全量 pytest）与 `_r43_fb_antirun.log`（互举反跑）。

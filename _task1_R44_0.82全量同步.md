# 第44轮 任务1 交付报告 —— 0.82 全量重同步

> 日期：2026-09-16 ｜ 优先级 P0 ｜ 修改区域：`scripts/` + 0.82（远端只读）
> 0.82：192.168.0.82（FreeBSD 15.1-STABLE，ai/ai2026，`/tmp` 临时副本）

## 一、结论

全量重同步完成：本机打包 **97.4 MB** → SFTP 上传 0.82 **4.9s** → 解压至
`/tmp/r44-20260916-232020`；远端 `examples` = **402**，与本机一致，**替换掉了 R43 的增量副本**。
新增可复用脚本 `scripts/同步0.82.py`（打包/上传/解压/校验/远端执行 五位一体）。

## 二、做法与踩坑固化

| 坑 | 处置 |
|---|---|
| Git-Bash `tar`(GNU 1.35) 把 `C:\` 当远程主机 → exit 128 | **不用 shell tar**，改用 Python `tarfile` 打包 |
| `--force-local` FreeBSD bsdtar 不认 | 不依赖该参数（本就不走 tar 命令） |
| OpenSSH 密钥被拒（`Permission denied (publickey,keyboard-interactive)`），本机无 `sshpass` | 用 **paramiko 5.0.0 + `.env` 密码认证**（`SSH_USER_AI`/`SSH_PASS_AI`） |
| `.env` 的 `SSH_HOST=192.168.0.88` 是**门禁机不是 0.82** | 0.82 主机 `192.168.0.82` 在脚本内显式常量，不复用 `SSH_HOST` |
| 远端无 `python`/`python3` 命令（`test_回归.py` 子进程硬编码 `['python', 运行器, …]`） | 建 `/tmp/r44-shim/python{,3}` → `exec /usr/local/bin/python3.11 "$@"`，经 PATH 注入 |
| 运行需 `light-merge`（`LIGHT_MERGE` 指向它） | 两个仓库**一起打包**，不只是 lightharness |

## 三、脚本 `scripts/同步0.82.py`

```
python scripts/同步0.82.py sync      # 打包+上传+解压+建垫片+校验 examples 数量
python scripts/同步0.82.py verify    # 只校验远端副本
python scripts/同步0.82.py run CMD   # 远端执行（自动注入 LIGHT_MERGE + PATH 垫片）
```

要点：
- 凭据只从 `G:/dswork/duan-light-merge/.env` 读，**值不落日志、不入档**。
- 排除 `.git/__pycache__/.venv/build/dist/node_modules/.pytest_cache/.mypy_cache` 与 `*.pyc` 等。
- 远端副本路径写入 `lightharness/_r44_remote_dir.txt` 供后续任务复用（临时指针文件）。
- 远端执行为增量回显 + 超时保护（默认 3000s），长跑 pytest 不会假死。

## 四、实测

```
[同步0.82] 打包完成：41787 文件，97.4 MB，耗时 46.1s
[同步0.82] 垫片就绪 /tmp/r44-shim/python -> /usr/local/bin/python3.11
[同步0.82] 上传 → /tmp/r44-20260916-232020/sync.tar.gz
[同步0.82] 上传完成，耗时 4.9s
[同步0.82] 远端 examples 数量 = 402
[同步0.82] ✅ 完成：远程副本 /tmp/r44-20260916-232020
```

远端目录结构校验通过：`/tmp/r44-20260916-232020/{lightharness,light-merge}`。

## 五、约束核对

- 0.82 **只读执行**，上传的是**副本**，未改远端任何源文件。
- 排除 `.git` 与大日志；`__pycache__`/`.pytest_cache` 一并排除以缩小包体。
- 凭据不入档（报告只提键名）。

## 六、给任务2 的交接

- 远端副本：`/tmp/r44-20260916-232020`（已由任务2 用于完整 pytest 回归）。
- 标准运行命令：
  ```
  cd /tmp/r44-20260916-232020/lightharness \
    && LIGHT_MERGE=/tmp/r44-20260916-232020/light-merge \
       PATH=/tmp/r44-shim:$PATH /usr/local/bin/python3.11 -m pytest tests/ -q --tb=no
  ```
  或等价地：`python scripts/同步0.82.py run /usr/local/bin/python3.11 -m pytest tests/ -q --tb=no`

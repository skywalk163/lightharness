# R90-C · fork FreeBSD 目标机构建验证（`--frozen-lockfile` 真机）

> 承接 R89 §6 遗留 4；执行顺序 C
> 结论：**R89-A 补的 pnpm-lock 在 FreeBSD 真机上自洽，无需再改 lock、无需再 push。**

---

## 1. 判据与结果

| 判据 | 结果 |
|---|---|
| `pnpm install --frozen-lockfile --ignore-scripts` rc | **0**（`Done in 6m 5.8s using pnpm v11.7.0`） |
| 是否 `ERR_PNPM_OUTDATED_LOCKFILE` | **否** → lock 自洽 |
| 装完 lock 是否被改动 | `git status --porcelain pnpm-lock.yaml` 为空 → **未被改** |
| HEAD / lock 条目 | `23288644c9`（R89-A 提交）；`grep -c freebsd-x64` = **36**（期望 36） |

## 2. 环境与取证链（一手，脚本 `_r90/c_082_fork_build.py`）

```
目标机：FreeBSD fb82 15.1-STABLE amd64
        node v24.19.0 / pnpm 11.7.0 / git /usr/local/bin/git
        packageManager（仓内）= pnpm@11.7.0  ← 与本机 R89-A 用的版本一致，故选 0.82 而非 192.168.1.5(10.28.0)

内网 gitea 可达：git ls-remote → 23288644c9c07e67dced78787e99d113d73787d9  refs/heads/master
clone：git clone --depth 1 http://192.168.1.5:3000/skywalk/deepseek-harness /tmp/r90-fork
       Updating files: 100% (13285/13285)
HEAD：2328864 R89-A: 重算 pnpm-lock 补回 fork 独有的 freebsd-x64 workspace 条目
```

核心命令输出尾部：
```
+ typescript 6.0.3
+ vitest 4.1.8
Done in 6m 5.8s using pnpm v11.7.0
>>> 核心判据 rc = 0
>>> 结论：LOCK 自洽（frozen-lockfile 通过）
```

## 3. 判定

- **R89-A 的 lock 补回是有效的**：FreeBSD 真机上 `--frozen-lockfile` 不报过期/不自洽，
  说明 fork 独有的 `native/system/packages/freebsd-x64` workspace 条目与 `node-pty` patch_hash
  都已正确写进 lock。
- **本轮不需要动 fork 仓** → 不产生新提交、不 push（与任务书预判一致）。
- 副本全程在 `/tmp/r90-fork`，未碰系统环境与原仓。

## 4. 未做与遗留

1. **完整 `pnpm install --frozen-lockfile`（带 scripts）未跑** —— 核心判据已达成且耗时已 6m，
   带 scripts 会触发 native 编译（node-pty / sharp 等），在 FreeBSD 上失败点多且**失败也不改变
   lock 自洽性**的结论。留作 R91 可选项。
2. **未跑构建**（`pnpm build` / `pnpm build:native-system`）—— 同上，属可选第三步。
   建议在需要真正产 FreeBSD 产物时再跑（那时要连完整 install 一起做）。
3. 192.168.1.5（FreeBSD 14.3 / pnpm 10.28.0）未用：版本低于仓 `packageManager` 要求，
   用它验证反而会引入版本噪音。

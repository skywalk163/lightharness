# R88 A 路交付：内网 fork 追平 gitcode alpha.2 —— 162 提交差量甄别 + 合入验证 + 移植评估

> 轮次：R88 A 路 ｜ 2026-09-23
> 仓库：`G:/github/deepseek-harness`（origin=内网 fork 192.168.1.5:3000；upstream=gitcode 镜像）
> 差量：`origin/master`(877717787c) .. `upstream/master`(00102833df = dsh-v0.1.7-alpha.2) = **162 commits**
> 红线遵守：❌ 未 push；❌ 未 commit 到 fork；仅在本地新建 `r88-fork-sync` 分支做合入验证；lightharness 仅新增 2 个文件（模块+测试），显式文件。

---

## 0. 结论速览

| 项 | 结果 |
|---|---|
| 差量全貌 | 162 commits / 943 files / +21450 −15929 |
| **本地合入验证** | ✅ **通过**：merge commit `6bf98a4370`，冲突仅 2 文件，全部解决；`HEAD..upstream/master=0`；status CLEAN |
| 冲突解决 | ① `native/system/packages/entry/package.json`：保留 fork 的 freebsd-x64 条目 + 采用 upstream 的 `workspace:~` 范围；② `pnpm-lock.yaml`：接受 upstream 版本（M 合入后需重新 `pnpm install` 重生成） |
| fork 三处 FreeBSD 对齐 | settings-controller / process-inspector.foregroundPgid / resolver.internalModules —— **三方自动合并成功，零冲突**，完整保留 |
| 纯逻辑面移植 | ✅ **1 项已移植**：`spill-policy/src/retention.ts`（多模态 token 预算保留算法）→ 新增 `lightharness/src/溢出保留.light` + 回归用例，本机 Windows 全绿 |
| 其余 161 条 | release/vendor 流程 / UI/desktop 前端 / 宿主面 —— 登记不移植 |
| fork push 权 | ⛔ 在 M 路；A 路仅本地验证 |

---

## 1. 合入验证一手证据

```
$ git checkout -b r88-fork-sync origin/master        # → 877717787c
$ git merge upstream/master --no-edit
Auto-merging native/system/packages/entry/package.json   ← CONFLICT (content)
Auto-merging package.json / pnpm-workspace.yaml / scripts/gen-cordis-catalog.ts
CONFLICT (content): pnpm-lock.yaml
Automatic merge failed; fix conflicts and then commit.

# 解决冲突后：
$ git add native/system/packages/entry/package.json pnpm-lock.yaml
$ git commit --no-edit
[6bf98a4370] Merge remote-tracking branch 'upstream/master' into r88-fork-sync

$ git status --porcelain        # (空) → CLEAN
$ git rev-list --count HEAD..upstream/master   # 0 → upstream 已完全合入
$ git log --oneline -3
6bf98a4370 Merge remote-tracking branch 'upstream/master' into r88-fork-sync
877717787c fix(build): FreeBSD branch in resolver.internalModules
b6ec71f962 fix(build): merge SettingsController options ...   ← fork 三处对齐之一
```

**冲突详情与处置**：
1. `native/system/packages/entry/package.json`：HEAD(fork) 有 5 平台 optionalDeps（含 freebsd-x64）用 `workspace:*`；upstream 删 freebsd-x64 并把全部范围改 `workspace:~`（vendor 4.0.4 tilde 约定）。**合并为：保留 freebsd-x64 + 统一 `workspace:~`**。freebsd-x64 包目录在 merge 后仍在工作区（fork 独有新增，upstream 无操作，三方合并不冲突）。
2. `pnpm-lock.yaml`：vendor 4.0.4 连带 7155 行重算。接受 upstream 版本（`--theirs`）。**M 路合入 push 前必须在 fork 上重新 `pnpm install` 以补 freebsd-x64 的 workspace lock 条目**。

---

## 2. 162 提交三分类落表

> 类别：**逻**=纯逻辑面（消息/协议/序列化/状态机/令牌计量/编排语义）；**宿**=宿主面（原生插件/系统调用/shell/CI/平台实现/UI）；**架**=架构面（模块拆分/装配/生命周期）；**rel**=release/vendor/merge 流程（无新逻辑）。
> 处置：**移植** / 登记 / 暂缓。

| # | SHA | 主题（oneline 摘要） | 类别 | lightharness 现状 | 处置 |
|---|---|---|---|---|---|
| 1 | 00102833df | Merge PR #4978 release alpha.2 | rel | — | 登记 |
| 2 | 10ea83bcc3 | release(dsh): 0.1.7-alpha.2 | rel | — | 登记 |
| 3 | 178ee3a9eb | Merge PR #4975 release vendor 4.0.4 | rel | — | 登记 |
| 4 | d0dca04e22 | release(vendor): cordis 4.0.4 / cosmokit 1.8.5 ... | rel | vendor 版本号 | 登记 |
| 5 | 3950647caa | Merge PR #4954 exact-workspace-deps | rel | — | 登记 |
| 6 | 3889e97de0 | Merge PR #4947 chat-groups-followup | rel | — | 登记 |
| 7 | 08c0e8e71b | fix(chat): deduplicate admitted local steering | 宿 | client/ui-chat React | 登记 |
| 8 | 43a8a22824 | fix(chat): turn rail width + scroll gestures | 宿 | UI 几何 | 登记 |
| 9 | f6966f8fab | test(client): resize fixtures | 宿 | 测试 | 登记 |
| 10 | fad9e27706 | test(web): resize/scroll fixtures | 宿 | 测试 | 登记 |
| 11 | 838eff14eb | fix(chat): reading intent around group scroll | 宿 | UI | 登记 |
| 12 | 4e6028a604 | build: tilde ranges for vendor/native workspaces | 宿 | 构建约定 | 登记（冲突已采用） |
| 13 | b9b5f7c58e | fix: exact DSH ranges in manifests | 宿 | 构建 | 登记 |
| 14 | 7021420f29 | fix: validate dependency ranges | 宿 | 构建脚本 | 登记 |
| 15 | 37372101b5 | build: pin internal workspace deps | 宿 | 构建 | 登记 |
| 16 | c92d5ebe18 | perf(ui): fit tooltips from observed sizes | 宿 | UI | 登记 |
| 17 | 820824edd7 | fix(chat): input echo admission/ordering | 宿 | UI | 登记 |
| 18 | 50ba2c8bb2 | fix(session): history pagination with turn boundaries | 逻 | 会话冷读有分页；turnWindow 为协议新参数 | **见 §3** |
| 19 | 2251b6189b | fix(chat): sticky headers overflow clipping | 宿 | UI | 登记 |
| 20 | 13dfae20c3 | fix(chat): native scroll follow before retarget | 宿 | UI | 登记 |
| 21 | fb02779a26 | fix(chat): turn rail container queries | 宿 | UI | 登记 |
| 22 | 1f029fc442 | docs(chat): scroll ownership | 宿 | docs | 登记 |
| 23 | 633cf7394e | fix(chat): independent scroll follow | 宿 | UI | 登记 |
| 24 | 6b4055bf32 | fix(chat): floating controls outside clipping | 宿 | UI | 登记 |
| 25 | 3dcfbf2094 | Merge PR #4964 fix-reconnect | rel | — | 登记 |
| 26 | 37e4dc2dee | Merge PR #4961 model-discovery-name | rel | — | 登记 |
| 27 | a44ced5b96 | fix(web): gate Remote WebSockets on readiness | 宿 | web 宿主 | 登记 |
| 28 | d4b109f439 | Merge PR #4907 plugin-install-country | rel | — | 登记 |
| 29 | bef0869d14 | test(web): select models by display name | 宿 | 测试 | 登记 |
| 30 | 84394b818c | Merge PR #4919 fatal-diagnostics | rel | — | 登记 |
| 31 | ec852793b5 | Merge origin/master into fatal-diagnostics | rel | — | 登记 |
| 32 | bdbf1fe339 | Merge origin/master into registry selection | rel | — | 登记 |
| 33 | 3c50bf6b6c | feat(plugin-manager): first responsive public registry | 宿 | 插件管理.light 无网络 registry 选择 | 登记（宿主网络） |
| 34 | c22b226b18 | fix: review threads on fatal-diagnostics | 宿 | desktop 宿主 | 登记 |
| 35 | af28c551f3 | Merge PR #4913 windows-installer | rel | — | 登记 |
| 36 | b34b5d33a1 | fix(web): discovered model names in picker | 宿 | UI | 登记 |
| 37 | 603a8fc7d3 | Merge origin/master into fatal-diagnostics | rel | — | 登记 |
| 38 | 505559b03b | Merge PR #4955 settings-link-copy | rel | — | 登记 |
| 39 | 30a7f8f787 | Merge master into windows-installer | rel | — | 登记 |
| 40 | 7c296b3f08 | Merge PR #4951 teammate-lead-guidance | rel | — | 登记 |
| 41 | b2ec54159f | docs(client): Sidebar Browser prose | 宿 | docs | 登记 |
| 42 | 108f767a89 | Merge PR #4949 voice-language-settings | rel | — | 登记 |
| 43 | 7b2094d04d | fix(desktop): Host diagnostic in crash reports | 宿 | desktop 宿主 | 登记 |
| 44 | d8924486ad | fix(desktop): cordis peer declaration | 宿 | desktop 宿主 | 登记 |
| 45 | a79e3a2a5f | fix(agent-team): explain teammate discovery | 逻 | 代理团队.light 已有；文案提示 | 登记（文案，非协议） |
| 46 | c81adc2569 | Merge PR #4948 agent-experience-skill | rel | — | 登记 |
| 47 | a294fc55d0 | Merge PR #4930 unbounded-completion-wakes | rel | — | 登记 |
| 48 | aba3472b1d | fix(client): chat link-opening copy | 宿 | UI 文案 | 登记 |
| 49 | d257fa4af7 | fix(agent-team): reminder limited to lead | 逻 | 代理团队；编排默认值 | 见 §3 |
| 50 | b980fdf5df | Merge PR #4950 release-rc.3-history | rel | — | 登记 |
| 51 | e420c44d60 | Merge PR #4857 unify-code-block-ui | rel | — | 登记 |
| 52 | bada62b50b | docs(skills): agent-experience skill | 宿 | docs | 登记 |
| 53 | 6ec97fa124 | fix(agent-team): tell teammates how to message lead | 逻 | 代理团队；文案 | 登记（文案） |
| 54 | 9c6c407da2 | Merge master into unify-code-block-ui | rel | — | 登记 |
| 55 | 7c84d9d790 | fix(voice-input): persist recognition language | 宿 | 语音宿主 | 登记 |
| 56 | 3ae2f687f1 | merge: record rc.3 history on master | rel | — | 登记 |
| 57 | d3c5f959aa | Merge PR #4921 excel-preview-resize | rel | — | 登记 |
| 58 | 58651b8359 | fix(web): resize Excel previews | 宿 | UI | 登记 |
| 59 | 2d653be7b0 | fix(tool-jobs): review on unbounded wake default | 逻 | tool-jobs wake 默认值 | 见 §3 |
| 60 | 5929af046c | Merge master into unify-code-block-ui | rel | — | 登记 |
| 61 | 780e07b8ed | test(web): boot assertions | 宿 | 测试 | 登记 |
| 62 | 32ca127565 | Merge PR #4898 contact-form-url | rel | — | 登记 |
| 63 | 536b444f36 | Merge origin/master into unbounded-wakes | rel | — | 登记 |
| 64 | f5d7de2a01 | Merge PR #4807 pwsh-prompt-readiness | rel | — | 登记 |
| 65 | 4777947b6c | fix(client): UID out of questionnaire URLs | 宿 | web 宿主 | 登记 |
| 66 | 930d187e04 | Merge origin/master into contact-form-url | rel | — | 登记 |
| 67 | 34a0a8e81d | fix(web): Excel previews OPC/XML encodings | 宿 | UI/excel 解析 | 登记 |
| 68 | e76a5eba21 | Merge PR #4903 platform-login-theme | rel | — | 登记 |
| 69 | 785a92ab03 | fix(client): contact menu → Feedback | 宿 | UI | 登记 |
| 70 | 3b6a5399e8 | docs(desktop): login theme ownership | 宿 | docs | 登记 |
| 71 | fd8bed1ad0 | Merge master into unify-code-block-ui | rel | — | 登记 |
| 72 | 62f816f3a5 | feat(web): code card spacing/thinking blocks | 宿 | UI | 登记 |
| 73 | ab7cdbee75 | Merge origin/master into registry | rel | — | 登记 |
| 74 | 41fd0baf91 | Merge origin/master into pwsh | rel | — | 登记 |
| 75 | f50059e425 | fix(desktop): theme sign-in links | 宿 | desktop | 登记 |
| 76 | 5ca6d34ac6 | Merge PR #4924 queued-edit-newline | rel | — | 登记 |
| 77 | 8cf07ea76c | fix(plugin-manager): preserve remembered registries | 宿 | 插件管理；网络 | 登记 |
| 78 | b6775f6d4f | fix(tool-jobs): wake idle owner every completion | 逻 | tool-jobs wake 默认 3→无界 | 见 §3 |
| 79 | 2c098434b9 | Merge origin/master into platform-login | rel | — | 登记 |
| 80 | 13fe312e15 | test(desktop): login theme CI fixtures | 宿 | 测试 | 登记 |
| 81 | 753df93b85 | test(web): multiline queued edit | 宿 | 测试 | 登记 |
| 82 | 8ae7631861 | Merge PR #4916 settings-provider-docs | rel | — | 登记 |
| 83 | b1c084e769 | Merge PR #4904 web-account-client-platform | rel | — | 登记 |
| 84 | 13d9606675 | test(voice-input): idle cleanup | 宿 | 测试 | 登记 |
| 85 | c74e36acfc | fix(web): line breaks in queued message re-edit | 宿 | UI | 登记 |
| 86 | e950c8bea4 | Merge PR #4838 message-overflow-review-menu | rel | — | 登记 |
| 87 | a19a48edea | Merge PR #4837 desktop-update-ui-2 | rel | — | 登记 |
| 88 | cafb9b93b4 | fix: adversarial review fatal-diagnostics | 宿 | desktop | 登记 |
| 89 | 5f1a524f61 | docs(credentials): private platform headers | 宿 | docs | 登记 |
| 90 | 6a133a02b8 | Merge origin/master into web-account | rel | — | 登记 |
| 91 | 43bd7010d0 | test(llm): isolate idle timeout from HTTP timing | 宿 | 测试 | 登记 |
| 92 | bed4a2b565 | fix(desktop): extraction failure report | 宿 | desktop | 登记 |
| 93 | dbd34bcc0d | Merge origin/master into pwsh | rel | — | 登记 |
| 94 | c9591d9445 | Merge origin/master into registry | rel | — | 登记 |
| 95 | d459183f32 | docs(settings): provider paths | 宿 | docs | 登记 |
| 96 | ce2ba9b216 | Merge master into unify-code-block-ui | rel | — | 登记 |
| 97 | ee4458f6d0 | Merge PR #4802 multimodal-tool-retention | rel | — | 登记 |
| 98 | d407a6ce90 | test(credentials): concurrent account order | 宿 | 测试 | 登记 |
| 99 | 4544874d62 | Merge master into windows-installer | rel | — | 登记 |
| 100 | a4c74a91e0 | Merge PR #4909 release-rc.3 | rel | — | 登记 |
| 101 | 6530130ffa | docs(agent-notes): fatal diagnostics | 宿 | docs | 登记 |
| 102 | e38cca76fd | feat(desktop): crash report before fatal dialog | 宿 | desktop 宿主 | 登记 |
| 103 | 8e7cca22ca | release(dsh): 0.1.5-rc.3 | rel | — | 登记 |
| 104 | 943af81a18 | fix(release): pin vendor for 0.1.5 | rel | 构建 | 登记 |
| 105 | 5864a6f6f1 | fix(desktop): drop connection headers forwarding | 宿 | desktop | 登记 |
| 106 | afde35880f | feat(client-modules): recover from failed batch script | 宿 | 客户端模块加载宿主 | 登记 |
| 107 | 9f52c6401e | docs(ip-geolocation): dependency graph | 宿 | docs | 登记 |
| 108 | 22be805026 | fix(ip-geolocation): align package | 宿 | 构建 | 登记 |
| 109 | 9f9a50e553 | feat(app-boot): uncaught exceptions → fatal | 宿 | app-boot 宿主启动 | 登记 |
| 110 | cfa84ed4e3 | fix(subprocess-local): contain spill failures not kill host | 宿 | Node fs 错误处理宿主 | 登记（见 §3） |
| 111 | ab62f09c22 | fix(desktop): Windows extraction 7-Zip evidence | 宿 | desktop | 登记 |
| 112 | dccf989cd8 | feat(plugin-manager): CN mainland mirror | 宿 | 插件管理；网络宿主 | 登记 |
| 113 | c5ca36387b | Merge origin/master into multimodal | rel | — | 登记 |
| 114 | f5c96b6340 | fix(credentials): client platform header | 宿 | HTTP 头宿主 | 登记 |
| 115 | 670a903237 | test: parallel recovery fixture | 宿 | 测试 | 登记 |
| 116 | b74bef5d40 | test: image recovery/PTC retention | 宿 | 测试 | 登记 |
| 117 | 817623750a | fix(desktop): Platform login theme | 宿 | desktop | 登记 |
| 118 | 8aff71863b | Merge origin/master into pwsh | rel | — | 登记 |
| 119 | 9d91bb01c9 | fix(desktop): About copy from live locale | 宿 | desktop | 登记 |
| 120 | 3305bb1938 | Merge origin/master into update-ui | rel | — | 登记 |
| 121 | 5ac920e50c | chore: merge master into message/review fixes | rel | — | 登记 |
| 122 | adbb0e0dc4 | fix(client): contact form URL / drop UID | 宿 | UI | 登记 |
| 123 | de45804084 | test: tool projection API snapshot | 宿 | 测试 | 登记 |
| 124 | 091db6c8c3 | Merge origin/master into pwsh | rel | — | 登记 |
| 125 | 94728ebd23 | fix: multimodal retention CI resolution | 宿 | 测试 | 登记 |
| 126 | 06923b8868 | Merge origin/master into multimodal | rel | — | 登记 |
| 127 | 6b227a81a7 | docs: sync plugin inventory | 宿 | docs | 登记 |
| 128 | 4137d1d628 | Merge origin/master into multimodal | rel | — | 登记 |
| 129 | f114233545 | fix(web): code-card overflow | 宿 | UI | 登记 |
| 130 | 8d2cd0cf72d | feat(web): unify code block styling | 宿 | UI | 登记 |
| 131 | 53abf11bdd | fix(desktop): Windows About on startup locale | 宿 | desktop | 登记 |
| 132 | f384ee7418 | Merge master into message-overflow | rel | — | 登记 |
| 133 | 89251dde83 | Merge origin/master into update-ui | rel | — | 登记 |
| 134 | 7ebbd370cd | test(web): quoted file reference coverage | 宿 | 测试 | 登记 |
| 135 | 719cc56276 | Merge master into message-overflow | rel | — | 登记 |
| 136 | 894f25b91e | fix(desktop): About product name from locale | 宿 | desktop | 登记 |
| 137 | bc4e8bafe6 | Merge origin/master into update-ui | rel | — | 登记 |
| 138 | 5aa21749b9 | fix(web): long file refs / floating menus | 宿 | UI | 登记 |
| 139 | c1edda8a37 | fix(desktop): Windows About in update dialog | 宿 | desktop | 登记 |
| 140 | 1566f3f5ad | fix(desktop): round Windows icon corners | 宿 | desktop | 登记 |
| 141 | 481b6b57e5 | fix(desktop): update restart notice | 宿 | desktop | 登记 |
| 142 | 754733d5d1 | test: shell spill snapshot for token budget | 宿 | 测试（spill 配套） | 登记 |
| 143 | f3c6d0c0df | test: multimodal catalog after master | 宿 | 测试 | 登记 |
| 144 | 68b44d78ba | Merge origin/master into pwsh | rel | — | 登记 |
| 145 | 575dc9add0 | Merge origin/master into multimodal | rel | — | 登记 |
| 146 | b0be6e79c2 | fix: failed PTC image result forwarding | 逻 | spill 多模态保留配套 | **见 §3（已随 retention 移植）** |
| 147 | 14c1fec958 | test: mixed-content retention headless | 宿 | 测试 | 登记 |
| 148 | 79468e26dd | test: multimodal spill recovery locators | 宿 | 测试 | 登记 |
| 149 | 4694540e2a | Merge origin/master into multimodal | rel | — | 登记 |
| 150 | e52209da40 | test: share multimodal snapshot | 宿 | 测试 | 登记 |
| 151 | 5c1d966c3f | test: image recovery failures | 宿 | 测试 | 登记 |
| 152 | 74f4c438de | test(pty): pin pwsh fast path | 宿 | pty/pwsh 宿主 | 登记 |
| 153 | c4c18ef0d4 | test: retention checks with token budgets | 宿 | 测试（配套） | 登记 |
| 154 | ab102138c8 | **fix: retain ordered tool text/images within token budget** | **逻** | **新增 溢出保留.light** | **✅ 已移植** |
| 155 | b900840784 | Merge origin/master into pwsh | rel | — | 登记 |
| 156 | 4f74f956ec | Merge origin/master into pwsh | rel | — | 登记 |
| 157 | 4e47ba6c1d | chore: start multimodal retention | 逻 | spill 多模态 | 见 §3 |
| 158 | 97545d9c8f | fix(pty): controlled prompt pwsh settles fast | 宿 | pwsh 宿主 | 登记 |
| 159 | 4df3de2075 | fix(desktop): installer brand art | 宿 | desktop | 登记 |
| 160 | c2be3d9a0b | test(web): desktop update palette | 宿 | 测试 | 登记 |
| 161 | 5015426866 | fix(ui): desktop update badge colors | 宿 | UI | 登记 |
| 162 | 422ded6f7a | fix(ui): desktop update tag styling | 宿 | UI | 登记 |

**统计**：rel/merge 流程 ≈ 45 条；宿主面（desktop/web/UI/pwsh/插件网络/测试）≈ 112 条；纯逻辑面 = 5 条（#18 session turnWindow、#49/#59/#78 tool-jobs wake、#146/#154/#157 multimodal retention）。

---

## 3. 纯逻辑面移植评估（5 条逻）

### 3.1 ✅ 已移植：多模态工具结果 token 预算保留（#154 ab102138c8，含 #146/#157 配套）

- **上游**：`packages/spill/spill-policy/src/retention.ts`（新增 104 行）+ `index.ts` 重写（maxInlineBytes→maxInlineTokens）+ `notice.ts`。
- **算法**：有序 text/image 块 head/tail 双端保留；文本可二分截断（fitText）；图片整块不可分割，放不下则跳过空位留空；头/尾各拿一半预算；UTF-16 surrogate 保护。
- **lightharness 现状**：`src/溢出.light` 是 alpha.1 时代的**字节预算纯文本**模型（`扁平化纯文本`遇非 text 块即返回空，不支持 image，无 token 估算）。
- **移植决策**：**只移植纯算法核心**（`保留内容`），不替换现有 `溢出.light` 接口（避免 bytes→tokens breaking change 冲击三平台门禁）。
  - 新增 `src/溢出保留.light`：`保留内容(内容, 预算)` + 内置近似计价（文本=字符数单调；图片=固定 1000）。
  - 光明字符串按码点索引，天然不劈代理对，**无需**原版 textSlice 的 surrogate 回退。
  - omittedBytes 复用 `溢出.light::字节长度`（UTF-8），与原版 Buffer.byteLength 同口径。
  - 后续接入真实 token-meter 时替换 `计价()` 即可；集成进 spill-policy 由后续轮决定。
- **回归用例**：`examples/test_R88_A_溢出保留.light`，6 组断言（预算0/够放原样/长文本头尾各半+省略80字节/图片整块省略/够放图片/多块依次填预算）。
- **本机验证**：`python 运行.py examples/test_R88_A_溢出保留.light` → exit=0，"全部用例通过"。
- **改动文件**（显式）：`lightharness/src/溢出保留.light`（新增）、`lightharness/examples/test_R88_A_溢出保留.light`（新增）。

### 3.2 ⏸ 登记不移植：tool-jobs wake 默认无界（#78 b6775f6d4f，含 #59/#49）

- **上游变更**：`maxConsecutiveWakes` 默认从 3 改为 undefined（无界）；idle owner 每次 completion 都 followup 开 turn。
- **lightharness 现状**：R87 B3 只移植了 jobs 的**数据结构/渲染层**（任务视图/输出环/事件总线/拉取泵/不变式），**未搬 wake/followup 编排机制**——那是 agent 宿主运行时行为（依赖 owner.status/followup/inject），非纯数据/协议。
- **决策**：登记不移植。wake 机制本身属宿主编排，lightharness 复刻时未实现该链路；默认值变更（3→无界）无对应落点。

### 3.3 ⏸ 登记不移植：session history turnWindow 分页（#18 50ba2c8bb2）

- **上游变更**：`SessionPageRequest` 新增 `turnWindow{minMessages, minTurns}`，历史分页对齐 turn 边界；`paginate` 按 turn/start 事件计数。
- **lightharness 现状**：`会话冷读.light` 有历史分页，但未实现 turnWindow 协议参数。该参数是**客户端↔服务端会话协议**的新增字段，深度耦合 session-controller 的 host/client 双端与 RemoteError 校验。
- **决策**：暂缓登记。属会话协议演进，建议随下一轮会话协议对齐一并处理（与 R87 已移植的会话域增量合并评估），不在本轮单独立项。

### 3.4 ⏸ 登记不移植：subprocess spill 失败 containment（#110 cfa84ed4e3）

- **上游变更**：subprocess-local output.ts 新增 SpillOptions.onFailure 回调；spill 文件 open/write 失败时降级为内存 tail，不 kill host；privateSpillDir 失败可恢复。
- **本质**：Node.js `node:fs` 层错误处理 + 进程退出钩子。lightharness 子进程是光明 stdlib 复刻，错误模型不同；该修复是 Node 宿主面健壮性。
- **决策**：登记不移植（宿主面）。

### 3.5 运行时管线钩子 projectContent（#154 配套，core/tools）

- 上游给 ToolDefinition 加 `projectContent?` 钩子（post-execute 前投影 ContentBlock），与多模态 retention 配套。这是 Cordis ToolRuntime/WeakMap/post-execute 瀑布的内部机制，lightharness 工具执行模型不同。**算法侧已随 §3.1 移植，管线钩子登记不移植。**

---

## 4. 架构面观察（单列建议，不移植）

| 架构点 | 观察 | 建议 |
|---|---|---|
| spill-policy 重写 | bytes→tokens + 多模态，是上游 0.1.7 后期的方向性演进 | 本轮已搬算法；配置语义切换（maxInlineTokens）建议后续轮随 token-meter 集成统一做 |
| vendor 4.0.4 | cordis/cosmokit/group/hmr/include/loader/logger-console/schemastery/timer 全升；workspace 范围改 tilde | lightharness 无 vendor Node 层，不涉及；合入时 entry/package.json 已对齐 tilde |
| freebsd/ 目录 | upstream 删了 freebsd/ 全套脚本；fork 独有保留 | merge 后 fork 的 freebsd/ 完整保留（fork 新增 vs upstream 无操作，三方不冲突）；M push 后 fork 仍持有 |

---

## 5. M 路注意事项

1. **push 前必做**：在 `r88-fork-sync` 分支上重新 `pnpm install`，重算 `pnpm-lock.yaml`（当前接受 upstream 版本，缺 freebsd-x64 workspace 条目）。
2. **push 命令**（M 路执行）：
   ```
   cd G:/github/deepseek-harness
   git checkout r88-fork-sync
   git push origin HEAD:master        # 内网 fork
   git ls-remote origin HEAD          # 复核新 HEAD
   ```
3. **lightharness 新增 2 文件**需 M 合流入 lightharness 仓：
   - `src/溢出保留.light`
   - `examples/test_R88_A_溢出保留.light`
   （均为新增，不改动任何现有文件，三平台门禁不受影响。）
4. **未做的事**：未联网拉取上游（以本地对象 diff 为准）；未 push；未 commit fork。

---

## 6. 判据核对

- [x] 162 提交 100% 落表（§2，逐条 SHA+主题+类别+处置）
- [x] 本地合入验证通过（merge commit `6bf98a4370`，CLEAN，`HEAD..upstream/master=0`）
- [x] 移植项本机全绿（`溢出保留.light` 6 断言通过）
- [x] 不 push（fork push 权在 M）
- [x] git add 显式文件（未 add 任何东西；lightharness 新增文件由 M 合流）

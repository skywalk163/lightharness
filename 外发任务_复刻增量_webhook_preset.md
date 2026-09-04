# 外发任务：lightharness 复刻增量（webhook / agent-presets / interaction 纯逻辑）

> 定位：lightharness（G:\dswork\duan-light-merge\lightharness）已用光明语言 1:1 复刻
> DeepSeek Harness（G:\github\deepseek-harness）的可提取纯逻辑核心，`docs/功能对标/对标清单.json`
> 70 张标卡全部 done。本批补三个**仍可提取纯逻辑但尚未建卡**的子模块，并按既定流程
> （建功能对标卡 + 光明 .light 实现 + 反跑测试用例 + 无缝自包含门禁）交付。
>
> 铁律（协作规程，与历批一致）：
>
> 1. **不许碰别人的文件。** 本批只许新建/修改本任务书列出的白名单文件。
> 2. **新增 stdlib 能力一律** **`.light`，一律不许建同名** **`.py`**（`_light_import_hook.py` 会让 `.py` 完全遮蔽 `.light`）。
> 3. **不许用** **`引 Python`** **绕过语言缺陷。** 绕不过就登记进语言缺陷账交给语言团队。
> 4. 只跑自己的定向测试 + 模块反跑测试，**不跑全量**。全量回归由主线独占机器时统一跑。
> 5. 临时文件用 `_taskXXX_` 前缀，PowerShell 中文输出落盘再读，不用 `&&` 与 heredoc。
> 6. 每个落地模块必须带：功能对标卡（对标清单.json 新增条目）+ `.light` 实现 + 反跑测试（改反必红）。

## 一句判定

原版这三个子包虽整体含宿主 Cordis / octokit 绑定，但核心纯逻辑可剥出，与历批口径一致：

- **webhook**：会话构建 / 消息注入 / 错误链 / 会话校验（node:crypto/path 属系统边界，可对齐）

- **agent-presets**：发现 / specifier 解析 / 挂载 / 元数据 / 作者面（纯逻辑，829 行主体）

- **interaction 剩余**：commands / user-questions / permission-presets（纯逻辑状态机与过滤）

***

## 白名单文件（只改这些）

### A. webhook（对齐 packages/webhook/webhook/src/{index,session,types,invariant,brand}.ts）

- 新建 `src/webhook会话.light`（核心会话构建纯逻辑；github 特有 octokit handler 不可复用，剥离）

- 新建 `examples/test_webhook会话.light`（反跑测试）

- 对标清单.json 新增 1 条（编号 71）

### B. agent-presets（对齐 packages/preset/agent-presets/src/{discovery,mount,specifier,metadata,authoring,preset,session,types,invariant}.ts）

- 新建 `src/预设.light`

- 新建 `examples/test_预设.light`

- 对标清单.json 新增 1 条（编号 72）

### C. interaction 剩余（对齐 packages/interaction/{commands,user-questions,permission-presets,user-approval 之外}/src）

- 补入现有 `src/审批.light`（新增命令/问题/权限预设纯逻辑），或新建 `src/交互命令.light`

- 新建 `examples/test_交互命令.light`

- 对标清单.json 新增 1 条（编号 73）

***

## 验收判据（每条都必须立得住反跑）

1. **功能对标卡**：在 `docs/功能对标/对标清单.json` 追加 3 条，状态=done/partial 必须给证据文件；只认 编号+功能 双字段匹配改状态。
2. **光明实现**：`.light` 真实现（有 设/当/遍历/返回 算法体），非导出清单壳，禁同名 `.py`。
3. **反跑判据**：每个模块的测试用例，把判据行为改反（抛↔不抛、值改错、分支取反）必须立红。
4. **门禁**：`python 运行.py examples/test_XXX.light` 退出码=0 且断言全过。
5. **对齐原版**：逐一对应原版 ts 的输入→输出（建议抄一张对照表进对标卡「本轮目标」）。

## 语言坑提醒（历批踩过，直接规避）

- 断言一律用 `断言相等`（L-037 曾是 no-op）；缺键用 `字典包含键` 守卫（L-036/L-041）。

- 函数用 `接收`；跨作用域可变状态用对象属性或可变容器兜。

- 除语义（裁决B，2026-09-04）：`/` 对 int/int 是**向零截断**，需要真除（如 ceil(len/4)）时用浮点字面量触发（如 `4.0`），不要想当然当 Python `/` 用。

- 发现语言"写不出/写错/绕不过"的地方 → 填进 `docs/功能对标/语言缺陷账.md`，别顺手改编译器。

## 交付物

- 三个 `.light` + 三个反跑测试 + 对标清单 3 条。

- 一份交付报告：每模块「原版文件 → 光明模块 → 对齐度 → 证据」对照表 + 反跑验证截图式日志。

## 运行通道

```powershell
cd G:\dswork\duan-light-merge\lightharness
python 运行.py examples/test_XXX.light     # 逐个绿
# 全量门禁由主线统一跑（本批新增后应为 181 + 新增通过数）
```


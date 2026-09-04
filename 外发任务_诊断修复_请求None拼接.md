# 外发任务：诊断并修复 lightharness 请求时报 `str + None` 拼接错误

> 定位：lightharness（G:\dswork\duan-light-merge\lightharness）—— 用自研「光明 / Light」中文编程语言
> 1:1 复刻 DeepSeek Harness 的纯逻辑核心。本任务排查 CLI 单轮/交互调用时**必现**的
> `can only concatenate str (not "NoneType") to str` 错误并修复。
> 门禁：`python 运行.py examples/test_XXX.light` 退出码=0 且断言全过；只跑定向+回归，不跑全量；
> 全程**不** commit/merge/push；`.env` 密钥绝不打印、绝不入库。

***

## 一、现象

在项目根目录运行（Windows PowerShell，cwd 必须是 `G:\dswork\duan-light-merge\lightharness`）：

```powershell
Remove-Item Env:HARNESS_REPL -ErrorAction SilentlyContinue
$env:HARNESS_MSG="你好，介绍一下你自己"
python 运行.py examples/运行CLI.light
```

输出（已修复失败原因打印，但只显示异常消息、**没有 traceback**）：

```
--- 轮次结束: error ---
--- 失败原因: can only concatenate str (not "NoneType") to str ---
--- 助手最终回复 ---

--- 已持久化(增量): sessions\--G-dswork-duan-light-merge-lightharness--\cli_xxx\session.jsonl ---
```

`can only concatenate str (not "NoneType") to str` 是 Python 层 `"字符串" + None` 的拼接错误。
当前被 `src/代理.light` 的 `执行步骤` 内 `捕获 异常` 吞掉，`转字符串(异常)` 只给出这条消息，
拿不到调用栈 → 必须自行定位到精确的文件:行。

## 二、已排查结论（直接复用，勿重复踩坑）

1. **密钥读取正常**：`src/总入口.light` 支持项目根 `.env` 读取（键 `OPENAI_API_KEY`）。
   已验证当把端点指向本地拒绝端口（`$env:HARNESS_ENDPOINT="http://127.0.0.1:65530/chat/completions"`）时，
   流程能走到 HTTPPost 并报 `URL 错误: 目标计算机积极拒绝`，说明 `.env` 密钥已读到、
   `"Bearer " + 己.密钥` 的请求头**没有炸**（密钥非 None）。
2. **端点在总入口已补全**：`.env` 的 `OPENAI_BASE_URL=https://api.deepseek.com` 会被自动拼成
   `https://api.deepseek.com/chat/completions`（`总入口.light` 的 `查找子串(端点, "chat/completions") == -1` 判定）。
3. **推断**：本地拒绝连接测试（请求未发出）不报 str+None；只有**真实请求成功发出并收到响应**时才报。
   → 高度怀疑错误发生在**响应解析 / 消息映射 / 会话持久化**阶段（`增量`、`块["text"]`、`消息["content"]`、
   `消息["role"]`、`工具["name"]` 等某个键缺失或为 `空` 时被 `+` 拼接），而非请求构造。
4. **`src/客户端.light`** **中已知 str+None 候选拼接点**（重点审查，但不限于这些）：

   - `L31`: `"模型停止: " + 原因`（`翻译完成原因`）

   - `L216`: `"网络错误: " + 文本`（`翻译异常`）

   - `L247 / L267`: `"Bearer " + 己.密钥`（已排除：本地拒绝测试未炸，但请复核）

   - `L95 / L102`: `推理块["文本"] + 增量["reasoning_content"]` / `文本块["文本"] + 增量["content"]`

   - `L173 / L175 / L193`: `文本 + 块["text"]`（`块文本拼接` 期望每块有 `"text"` 键，缺键即 None 拼接）
5. **`翻译流`（客户端.light L64-127）对增量缺键已有守卫**：`增量.包含("content") 且 增量["content"] != ""`。
   → 若根因在增量，需检查守卫**未覆盖**的路径（如 `调用["index"]`、`调用["id"]`、`调用["function"]["name"]`、
   `选择["delta"]` 本身为 None 等）。
6. **运行链**：`运行.py` → 委托 `light-merge` 编译器 `cli.light run` → 转译光明为 Python 执行
   （`_light_import_hook` 支持 `.light` 模块 import）。可用 `LIGHT_MERGE` 环境变量覆盖编译器路径。

## 三、任务步骤

1. **拿到精确 traceback（首要）**：任选其一，尽快定位到文件:行：

   - 临时在 `src/代理.light` 的 `执行步骤` 捕获处打印更详细错误（含 Python traceback），或

   - 审查转译产物 / 直接用 Python 复现真实请求（注意：真实调用消耗 token，最多 2 次），或

   - 用**不消耗 token** 的方式：写临时脚本 mock `HTTPPost` 返回一段真实形态的 SSE（含
     `reasoning_content` / `content` / `usage` / `[DONE]` 的 deepseek 推理响应），走通整条
     `对话响应 → 翻译流 → 代理循环 → 消息映射 → 会话持久化` 链路来触发/复现。
2. **定位并修复根因**：修正缺失键/`空` 值的拼接（补 `.包含` 守卫、`!= 空` 判空、或安全取值）。
   只在光明 `.light` 源文件中修复。
3. **回归验证**（定向，勿跑全量）：

   - `python 运行.py examples/test_总入口.light`

   - `python 运行.py examples/test_联调CLI.light`

   - `python 运行.py examples/test_cli深化.light`

   - 以及你认为相关的单元测试（`examples/test_客户端*.light`、`examples/test_消息*.light` 等，先 `ls examples/` 找）
4. **如实交付**：若根因确实无法用假 SSE 复现、必须真实 API 验证，最多允许 2 次真实调用，
   且**绝不在输出/日志/报告里打印** **`.env`** **密钥值**（可用 `sk-***` 打码）。

## 四、约束

- 仅允许修改 `lightharness/src/` 下的光明 `.light` 文件（如 `客户端.light`、`代理.light`、
  `消息.light`、`会话.light`、`持久化.light`、`总入口.light`）。禁止修改 `.env`、`运行.py`、`stdlib/`。

- 语言：光明（Light）中文编程语言；禁止创建同名 `.py` 文件、禁止用 Python 改逻辑。

- 临时文件一律 `_taskD_` 前缀，收尾时清理干净（spill/探针/临时脚本都要删）。

- 禁止跑全量测试（会拖慢且可能触发无关失败）；只跑上列定向测试。

- 禁止 commit / merge / push；交付后工作树保持「未提交」状态。

- 交付前 grep 检查：`password`、`api_key`、`sk-`、密钥值等不得出现在新增/改动内容里。

## 五、交付物（写回你的最终消息）

1. **根因**：`src/xxx.light:行号` + 触发条件（哪个响应字段为 None、为何缺键）+ 一句话解释。
2. **修复内容**：改了哪些文件、各改了哪几行、改成什么（贴关键 diff 片段）。
3. **验证证据**：定向测试输出（PASS + 退出码 0）；若用了假 SSE mock，给出 mock 片段与触发/修复前后对比；
   若用了真实 API，给出打码后的成功/失败现象。
4. **遗留**：任何无法在此任务内解决的次生问题。

## 六、运行通道

```powershell
cd G:\dswork\duan-light-merge\lightharness
python 运行.py examples/运行CLI.light
# 定向测试：
python 运行.py examples/test_总入口.light
# .env 位于项目根，需在项目根运行；密钥键名 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL
```


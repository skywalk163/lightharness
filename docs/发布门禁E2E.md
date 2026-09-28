# lightharness 发布门禁 E2E Skill

> 每次发版前必须通过此门禁。三层测试：单元 → 回归 examples → Playwright WebUI。

## 何时触发

- 发版前（版本号变更、打 tag、合并 main 前）
- 改了 webui/、src/、运行.py、examples/ 下任何文件后
- 用户说"跑测试"/"验证"/"放行"时

## 三层测试命令

在 `lightharness/` 目录下依次执行：

### 第一层：单元测试（快，~2分钟）
```
python -m pytest tests/unit/ -o addopts="" -q
```
覆盖 33 个核心业务模块，574 个用例。失败必须修。

### 第二层：examples 回归（中，~5分钟）
```
python -m pytest tests/test_回归.py -o addopts="" -q
```
523 个 examples/*.light 端到端退出码门禁。失败必须修。

### 第三层：Playwright WebUI E2E（慢，~3分钟，需 .env 有真 key）
```
python .e2e_full.py
```
19 个场景，覆盖：
- 真实 API 聊天（发消息→等 deepseek 回复→token 统计更新）
- 会话 CRUD（新建/切换/重命名/删除/刷新持久化）
- 权限预设三档切换
- 工具面板开/关
- 审批面板开/关/刷新/审批闭环
- 设置面板开/X关/Esc关/未保存保护
- 输入区行为（Enter/Shift+Enter/空消息）
- 移动端视口
- 无 JS 错误

输出 `19/19 通过` 才算过。

## 环境要求

- `.env` 配好真实 `OPENAI_API_KEY`（第三层需要）
- Playwright + 系统 Edge（`pip install --target=.e2e_libs playwright`，用 `channel="msedge"`）
- Python 3.10+

## 已知可接受的失败

- **F2 工具审批闭环**：如果模型选择不调工具，或"按类别"权限自动放行 bash，会打印"无待批准项"但不算失败。这是模型行为不确定，不是 bug。
- **网络依赖**：第三层需要访问 api.deepseek.com，离线环境跳过此层但需人工标注。

## 快速冒烟（只跑第三层）

如果只改了 webui/，可只跑：
```
python .e2e_full.py
```

## 产物

- 截图在 `.e2e_shots_full/`（每轮自动清空重建）
- 测试脚本：`.e2e_full.py`（真实模式）、`.e2e_test.py`（mock 模式，无 key 时用）

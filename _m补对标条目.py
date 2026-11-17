# -*- coding: utf-8 -*-
import json

p = '/home/skywalk/dswork/lightharness/docs/功能对标/对标清单.json'
d = json.load(open(p, encoding='utf-8'))
items = d['条目']

# 幂等：若已补到 358+ 则不重复
if max(i['编号'] for i in items) >= 358:
    print('已存在 #358+，跳过')
else:
    new = [
    {"编号":358,"功能":"HarnessError 基类（稳定机器码 code + cause 链 + name 取子类名）",
     "原版包":"packages/util/error/src/index.ts（dsh-v0.2.2-rc.3=38a6a5c965，rc.2 起 20+ 包新错误类统一继承）",
     "光明模块":"src/错误增强.light（本轮扩展）",
     "状态":"done（R221-Bf2 T-0367）：稳定机器码与人类消息分离、cause 链、name 取子类名。作为 rc.2 起错误码分类地基。",
     "证据":["packages/util/error/src/index.ts（git show dsh-v0.2.2-rc.3）","src/错误增强.light","examples/test_R221_Bf2错误与清理.light（69 断言）"],
     "本轮目标":"69 断言全绿","反跑判据":"code/name/cause 任一改反即红","语言缺陷":[]},
    {"编号":359,"功能":"llm-deepseek 凭据来源与模型/凭据增补",
     "原版包":"packages/llm/llm-deepseek/src/credential.ts + 模型目录增补（rc.3=38a6a5c965）",
     "光明模块":"src/模型目录.light / src/模型列表缓存.light（扩展）",
     "状态":"done（R221-B7 T-0364）：新增 credential.ts + 模型/凭据增补。R220 漏项补做。",
     "证据":["packages/llm/llm-deepseek/src/credential.ts（git show dsh-v0.2.2-rc.3）","src/模型目录.light","src/模型列表缓存.light","examples/test_R221_B7模型增补.light（119 断言）"],
     "本轮目标":"119 断言全绿","反跑判据":"增补的模型/凭据字段任一改反即红","语言缺陷":[]},
    {"编号":360,"功能":"forge 变更请求三条：快照概览 / diff 定 head / 评审读取码",
     "原版包":"packages/experimental/forge + forge-github/src（rc.3=38a6a5c965）",
     "光明模块":"src/变更请求.light（扩展）",
     "状态":"done（R221-Bf1 T-0366）：#9 快照概览、#10 diff 定 head、#11 评审读取码。gh 调用与客户端 UI 属宿主登记不移植。",
     "证据":["packages/experimental/forge/src/、forge-github/src/（git show dsh-v0.2.2-rc.3）","src/变更请求.light","examples/test_R221_Bf1变更请求快照.light（76 断言）"],
     "本轮目标":"76 断言全绿","反跑判据":"快照/diff 定 head/评审读取码任一改反即红","语言缺陷":[]},
    {"编号":361,"功能":"工作树清理判定（retainOnArchive / 未归档引用 / 只读）",
     "原版包":"packages/experimental/worktree/src（rc.3=38a6a5c965）",
     "光明模块":"src/工作区变更.light（扩展）",
     "状态":"done（R221-Bf2 T-0367）：retainOnArchive 保留、未归档引用保护、只读判定。worktree 服务宿主面登记不移植。",
     "证据":["packages/experimental/worktree/src/（git show dsh-v0.2.2-rc.3）","src/工作区变更.light","examples/test_R221_Bf2错误与清理.light（69 断言）"],
     "本轮目标":"69 断言全绿","反跑判据":"retainOnArchive/未归档引用/只读任一改反即红","语言缺陷":[]},
    {"编号":362,"功能":"插件更新方式（registry / git）与安装结果核对",
     "原版包":"packages/boot/plugin-manager/src（rc.3=38a6a5c965）",
     "光明模块":"src/插件注册表.light（扩展）",
     "状态":"done（R221-Bf3 T-0368）：#12 更新方式 registry/git 双通道、安装结果核对。宿主注册部分登记不移植。",
     "证据":["packages/boot/plugin-manager/src/（git show dsh-v0.2.2-rc.3）","src/插件注册表.light","examples/test_R221_Bf3更新与计费.light（67 断言）"],
     "本轮目标":"67 断言全绿","反跑判据":"更新方式分支或结果核对改反即红","语言缺陷":[]},
    {"编号":363,"功能":"搜索按计费三态选凭据 + credential 来源与延迟失败",
     "原版包":"packages/web/web-search-deepseek/src（rc.3=38a6a5c965）",
     "光明模块":"src/网页搜索.light（扩展）",
     "状态":"done（R221-Bf3 T-0368）：#18 按计费三态选凭据、credential 来源、延迟失败语义。exa/perplexity provider 删除后收敛到单一 deepseek。",
     "证据":["packages/web/web-search-deepseek/src/（git show dsh-v0.2.2-rc.3）","src/网页搜索.light","examples/test_R221_Bf3更新与计费.light（67 断言）"],
     "本轮目标":"67 断言全绿","反跑判据":"三态选凭据或延迟失败改反即红","语言缺陷":[]},
    {"编号":364,"功能":"会话批量追加 + 运行时上下文提醒",
     "原版包":"packages/core/session + core/tools/src（rc.3=38a6a5c965）",
     "光明模块":"src/会话.light / src/会话日志深化.light（扩展）",
     "状态":"done（R221-Bf4 T-0369）：#14 批量追加、#13 运行时上下文提醒（提醒完整模型）。",
     "证据":["packages/core/session/src/、core/tools/src/（git show dsh-v0.2.2-rc.3）","src/会话.light","src/会话日志深化.light","examples/test_R221_Bf4会话与子代理.light（117 断言）"],
     "本轮目标":"117 断言全绿","反跑判据":"批量追加去重或提醒注入位改反即红","语言缺陷":[]},
    {"编号":365,"功能":"子代理中断默认关 + 插件面板造卡片透传工具表",
     "原版包":"packages/core/agent-loop/src（rc.3=38a6a5c965）；插件面板为 lightharness 自有",
     "光明模块":"src/子代理预设选择.light / src/代理团队.light / src/插件面板.light / src/web服务器.light",
     "状态":"done（R221-Bf4 T-0369 + T-0385）：#15 中断默认关（两层次）；插件面板异常修复——造卡片透传工具表、MCP 桥接补只读原因，前端不再显示「不包含任何组件」。",
     "证据":["packages/core/agent-loop/src/（git show dsh-v0.2.2-rc.3）","src/插件面板.light","src/web服务器.light","examples/test_R221_Bf4会话与子代理.light（117 断言）","examples/test_r221插件面板e2e.light（10 断言）"],
     "本轮目标":"Bf4 117 + 面板 e2e 10 断言全绿","反跑判据":"中断默认值或工具表透传改反即红","语言缺陷":[]},
    ]
    items.extend(new)
    out = json.dumps(d, ensure_ascii=False, indent=2)
    if not out.endswith('\n'):
        out += '\n'
    open(p, 'w', encoding='utf-8').write(out)
    print('已补', len(new), '条；新条目数', len(items), '最大编号', max(i['编号'] for i in items))

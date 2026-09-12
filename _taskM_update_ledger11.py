# -*- coding: utf-8 -*-
"""第11轮路M回填对标清单：#4/#48/#65/#66 状态 + 新增 #74~#79。"""
import json, os, sys

PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'docs', '功能对标', '对标清单.json')
with open(PATH, 'r', encoding='utf-8') as f:
    d = json.load(f)

items = d['条目']
by_no = {it['编号']: it for it in items}

# 1) 更新 #4/#48/#65/#66 状态为已跟随
updates = {
    4: "done(v2 多媒体块)；0.1.5第11轮任务1已跟随：造系统消息(createSystemMessage)逐字段对齐上游 message.ts:238（空文本->content=[]，非空->单text块，source=plugin，id新鲜唯一，content经深拷贝脱钩）；本轮补独立测试 test_消息_System.light（10断言）",
    48: "done；0.1.5第11轮任务1已跟随：判定规范base64按策略(空串reject/accept参数化)/解码校验(Image/File文案分流)/规整文件名/存文件输入/造文件引用/准入编码文件 与上游 admission.ts 逐函数对齐；文件无大小限额（对齐 saveFile 注释）；本轮补独立测试 test_附件_通用文件.light（18断言）",
    65: "done；0.1.5第11轮任务2已跟随：4个事件构造段 version 1->2 早已对齐；本轮补「v2事件信封包装」四导出（包装成员记录/包装任务记录/包装排队记录/包装送达记录），把内层载荷包成 #67 折叠期望的外层信封 {type,data:{version:2,...},seq}；test_团队事件v2.light（≥18断言）互操作通过",
    66: "done；0.1.5第11轮任务2已跟随：中文事件汇原样保留；本轮补「v2事件投影桥接」四段（映射看板状态/投影v2任务/投影v2记录/投影全部v2记录），中文记录->上游v2 TeamTaskSnapshot（id/revision/subject/description/status英文枚举/blockedBy/writeScopes），满足 #67 校验任务载荷",
}
for n, new_state in updates.items():
    by_no[n]['状态'] = new_state
    # 补充证据
    extra_evidence = {
        4: 'examples/test_消息_System.light',
        48: 'examples/test_附件_通用文件.light',
        65: 'examples/test_团队事件v2.light',
        66: 'examples/test_团队工具.light',
    }
    ev = by_no[n].get('证据', [])
    if extra_evidence[n] not in ev:
        ev.append(extra_evidence[n])

# 2) 新增 #74~#79
new_items = [
    {
        "编号": 74,
        "功能": "sdk/protocol NDJSON JSON-RPC 2.0 传输层（JsonRpcLineTransport 行分隔端点：请求/响应/通知帧编码+判别+分派+增量行解码+错误码）",
        "原版包": "packages/sdk/protocol/src/{transport.ts,types.ts,index.ts}",
        "光明模块": "src/JSONRPC传输.light",
        "状态": "done(纯逻辑层)；0.1.5第11轮任务4已跟随：帧编码(造请求/响应/通知/错误帧+帧编码NDJSON)+帧判别(id+method请求/仅id响应/仅method通知/非法)+NDJSON行解码器(半行合并/多行切分/收尾)+JSONRPC终端(无处理器-32601/处理器失败-32603/成功回result)+ID生成(req_前缀+三段随机整数)；pending请求表/AbortSignal/flush/流挂接 未移植（依赖node:stream+Promise，留后续轮宿主包）",
        "证据": [
            "src/JSONRPC传输.light",
            "examples/test_JSONRPC传输.light"
        ],
        "本轮目标": "done：40+断言覆盖请求/响应/通知帧编码与params省略、错误帧code/message/data形状、帧编码以\\n结尾往返、三类帧判别(含数字id/非字典/非法)、归一化参数、增量解码(半行合并/多行一次入/多行同批出/收尾丢弃残行)、终端分派(-32601/-32603/成功回result)、通知分派与丢弃、非法行静默忽略、入站响应记录、ID req_前缀/两次不同/100个全唯一",
        "反跑判据": "_antirun_jsonrpc.py 3/3 PASS：A响应帧判别提前->id+method误判为响应红；B非法行忽略改外抛->坏JSON行红；C增量半行合并改无\\n残块当完整行吐红",
        "语言缺陷": []
    },
    {
        "编号": 75,
        "功能": "boot/app-boot profile 解析 + patch 层组合 + cmdline launcher flags（PROFILES_DIR/PROFILE_PATCH_FILENAME/resolveProfileDir/initProfile/readProfileManifest/writeProfileManifest/composeEntries + parseDshArgs 三态）",
        "原版包": "packages/boot/app-boot/src/profile.ts + packages/boot/cmdline/src/index.ts + apps/cli/src/args.ts",
        "光明模块": "src/启动配置.light",
        "状态": "done(纯逻辑层)；0.1.5第11轮任务5已跟随：解析profile目录(名称合法性校验+profiles段拼接)/读取profile清单(JSON对象校验)/写入profile清单(2空格缩进+尾换行)/初始化profile(幂等建目录+manifest+空patch)/加载补丁层/组合条目(id浅覆盖+insert追加)/解析启动参数(--profile/--from-default-profile/--patch可重复/--dump-config/--dump-default-config/-V/-h + web别名 + desktop保留 + dump互斥 + inner args透传)；patch层用JSON替代YAML；未接入总入口命令面",
        "证据": [
            "src/启动配置.light",
            "examples/test_启动配置.light"
        ],
        "本轮目标": "done：32断言覆盖目录解析(7非法名)/manifest读写往返/manifest校验(数组+缺失)/initProfile幂等/patch组合顺序覆盖/insert追加/用户patch覆盖/flags收集/inner args透传/校验抛错(缺profile/空patch/desktop)/dump三态与互斥/--from-default-profile",
        "反跑判据": "_antirun_boot.py 3/3 PASS：A组合条目layers倒序叠加红；B解析profile目录去掉profiles段红；C --patch收集改覆盖而非追加红",
        "语言缺陷": []
    },
    {
        "编号": 76,
        "功能": "test-support/llm-mock-server 可脚本化 OpenAI 兼容 mock LLM 服务器（24行为表+默认随机权重+播种随机+加权选择+文本切块+SSE帧+行为队列FIFO+守卫次序）",
        "原版包": "packages/test-support/llm-mock-server/src/{index.ts,cli.ts,bin.ts}",
        "光明模块": "src/mock大模型服务器.light",
        "状态": "done(纯逻辑核心)；0.1.5第11轮任务6已跟随：24种行为(success/流式分片/7错误码族/语义空回复族/畸形流/传输退化族/reasoning_success/tool_call_success/max_tokens/slow_success)+默认随机权重13键+最大定时延迟2147483647+播种随机(整数LCG替代mulberry32)+加权选择+文本切块+SSE帧(data:{json}\\n\\n + data:[DONE]\\n\\n)+行为队列FIFO消费(越界循环末位/脚本耗尽500)+守卫次序(非POST405/路径错404/API密钥401/坏JSON400且不消费脚本)；cli.ts/bin.ts/部分延时未移植",
        "证据": [
            "src/mock大模型服务器.light",
            "examples/test_mock大模型服务器.light",
            "examples/_repro_L084.light"
        ],
        "本轮目标": "done：49断言覆盖行为队列FIFO顺序/流式SSE帧形状(3片+终止+DONE)/7错误状态码+rate_limit Retry-After向上取整/语义空回复族(empty/empty_body/stream_eof)/随机权重种子确定性(同种子同序列/异种子异序列)/耗尽500与循环末位复用/守卫401(无错令牌)/405(非POST)/404(路径错)/坏JSON400且不消耗脚本/reasoning_success含reasoning_content/tool_call_success含tool_calls/启动Mock服务真实端口>0",
        "反跑判据": "_antirun_mockllm.py 3/3 PASS：A FIFO->LIFO取末项红；B完成帧体去[DONE]红；C忽略种子(状态恒0)红",
        "语言缺陷": ["L-084"]
    },
    {
        "编号": 77,
        "功能": "experimental/tool-agent-team 9 个团队工具纯逻辑（spawn_teammate/send_message/list_agents/wait_agent/interrupt_agent/team_task_create/team_task_list/team_task_update + 工具声明表 + 参数校验 + wait纯逻辑 + list过滤分页 + jsonOutput呈现）",
        "原版包": "packages/experimental/tool-agent-team/src/index.ts",
        "光明模块": "src/团队工具.light",
        "状态": "done(纯逻辑层)；0.1.5第11轮任务2已跟随：9个工具parameters JSON Schema(参数键名对齐上游英文snake_case)+团队工具声明表()+wait_agent纯逻辑(解析等待超时默认30000/判等待超时合法[10000,3600000]/是否活跃等待running/provisioning/有无活跃等待伙伴/无进展等待结果no-active-peer)+team_task_list纯逻辑(过滤status精确/owner==unowned/ready精确 + 判分页cursor>=0 limit1..100默认50 + 分页切片[cursor,cursor+limit)未取尽附nextCursor)+渲染JSON文本(jsonOutput->text块)；团队工具面通过注入能力字典桥接宿主agentTeams，真实宿主挂载留后续轮",
        "证据": [
            "src/团队工具.light",
            "examples/test_团队工具.light"
        ],
        "本轮目标": "done：≥30断言覆盖9工具定义/参数校验×6/wait纯逻辑×9/wait执行面×3/列任务过滤分页×7/判分页×3/呈现×2",
        "反跑判据": "_antirun_team_v2.py C项：判等待超时合法下限10000->1000(参数校验放宽)红",
        "语言缺陷": []
    },
    {
        "编号": 78,
        "功能": "util 8 小包批量复刻（chunked-list分块列表/deque双端队列/crypto加密/values值工具/brand品牌/time时间/package-manifest包清单/workspace-path工作区路径）",
        "原版包": "packages/util/{chunked-list,deque,crypto,values,brand,time,package-manifest,workspace-path}/src/index.ts",
        "光明模块": "src/分块列表.light + src/双端队列.light + src/加密.light + src/值工具.light + src/品牌.light + src/时间工具.light + src/包清单.light + src/工作区路径.light",
        "状态": "done；0.1.5第11轮任务3已跟随：分块列表(不可变追加链表块容量64+遍历正展平+校验分块非空≤64替代zod)/双端队列(环形缓冲最小容量16+摊销O(1)+1/4收缩下限16+严格不补popBack)/加密(字节转Base64+随机UUID v4版本位+摘要SHA-256hex)/值工具(是JSON值拒绝NaN与-0+快照JSON值先判后深复制+深相等JSON结构递归+断言永不+深冻结语义占位)/品牌(打品牌字符串/数字运行期恒等)/时间工具(规范客户端时区复用既有IANA正则+去空白+UTC捷径)/包清单(读包清单DSH+校验Bundle/Profile/Client/配置树声明)/工作区路径(盘符UNC判定+主目录~缩写+末段标题+路径分部+file-address编解码dsh-resource://file/...)",
        "证据": [
            "src/分块列表.light",
            "src/双端队列.light",
            "src/加密.light",
            "src/值工具.light",
            "src/品牌.light",
            "src/时间工具.light",
            "src/包清单.light",
            "src/工作区路径.light",
            "examples/test_工具_小工具.light"
        ],
        "本轮目标": "done：59断言覆盖分块边界/跨越块容量64、队列FIFO与回绕与清空、base64/UUID v4版本位/SHA-256确定性、JsonValue真假例、深相等与快照解耦、品牌恒等、IANA/UTC/空白拒绝、包清单读出与各角色合法/非法、盘符/UNC/POSIX绝对判定、主目录缩写、file-address会话/绝对域往返",
        "反跑判据": "_antirun_util8.py 3/3 PASS：A双端队列队尾推入尾址计算改固定写队首->FIFO顺序错乱红；B值工具深相等JSON两处递归拒判改如果假->退化成浅比较红；C工作区路径是Windows风格路径UNC前缀判定改如果假红",
        "语言缺陷": []
    },
    {
        "编号": 79,
        "功能": "第11轮登记缺口收口汇总（#4 System词表 + #48 通用文件附件 + #65/#66 事件v2 四路补漏闭环）",
        "原版包": "llm/llm/message.ts + attachment/admission.ts + experimental/agent-team/types.ts+task-board.ts",
        "光明模块": "src/消息.light + src/附件准入.light + src/团队依赖图.light + src/团队看板.light",
        "状态": "done；0.1.5第11轮收口：#4 System词表(造系统消息createSystemMessage)、#48 通用文件附件(EncodedFileAttachment/admitEncodedFile)、#65 事件v2信封包装、#66 看板v2投影桥接 四路缺口全部闭合；新增测试 test_消息_System.light(10断言)+test_附件_通用文件.light(18断言)+test_团队事件v2.light(≥18断言) 覆盖原上游缺口",
        "证据": [
            "src/消息.light",
            "src/附件准入.light",
            "src/团队依赖图.light",
            "src/团队看板.light",
            "examples/test_消息_System.light",
            "examples/test_附件_通用文件.light",
            "examples/test_团队事件v2.light"
        ],
        "本轮目标": "done：#4/#48/#65/#66 四条历史缺口登记全部转为已跟随；反跑 _antirun_msg_attach.py 2/2 PASS(role system大小写错/空串accept改reject红)、_antirun_team_v2.py A/B 两项(送达通知version 2->1红/投影v2记录data.version 2->1红)",
        "反跑判据": "见 #4/#48/#65/#66 各卡",
        "语言缺陷": []
    },
]

# 确保编号不冲突
existing_nos = set(by_no.keys())
for it in new_items:
    assert it['编号'] not in existing_nos, f"编号 {it['编号']} 已存在"
    items.append(it)

# 按编号排序
items.sort(key=lambda x: x['编号'])
d['条目'] = items

with open(PATH, 'w', encoding='utf-8') as f:
    json.dump(d, f, ensure_ascii=False, indent=2)

print(f"OK: 条目数 {len(items)}; 更新 #4/#48/#65/#66; 新增 #74~#79")

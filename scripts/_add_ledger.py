# -*- coding: utf-8 -*-
import json, os

p = r'G:/dswork/duan-light-merge/lightharness/docs/功能对标/对标清单.json'
d = json.load(open(p, encoding='utf-8'))
e = d['条目']
ids = [x['编号'] for x in e]
print('现有编号:', ids)

new_entries = [
    {
        "编号": 47,
        "功能": "本地 HTTP(S) 抓取提供方 URL 校验与内容类型分类纯逻辑核心（web-fetch-http policy：validateFetchUrl 四判定 + parseCharset + 主类型归类 + 同源比较）",
        "原版包": "packages/web/web-fetch-http/src/policy.ts",
        "光明模块": "src/抓取策略.light",
        "状态": "done",
        "证据": [
            "src/抓取策略.light",
            "examples/test_抓取策略.light"
        ],
        "本轮目标": "done：手工切分 scheme://authority[/path] 等价复刻原版 new URL() 四条判定（长度上限/协议白名单/authority 非空/无凭据@）；字符扫描复刻 parseCharset 正则（\\s 近似为 空格/制表/换行/回车）；提供 取MIME/分类内容类型/解析字符集/比较同源/校验抓取地址 纯函数。已剔除 decoderForCharset（纯光明无编码库，登记缺口）。",
        "反跑判据": "test_抓取策略.light：把任一 断言相等 期望值改反即红；把 校验抓取地址 超长/非法协议/含@ 用例期望改反即红；把 检查抛错 用例改为不抛即红。",
        "语言缺陷": [
            "L-036(缺键下标抛 键错误，可选字段先 字典包含键 守卫)",
            "L-043(布尔链拆多行 如果，禁 且/或+行内 否则 返回)",
            "L-004(\\s 元字符无，正则不返回捕获组，字符扫描绕开)"
        ]
    },
    {
        "编号": 48,
        "功能": "附件准入纯逻辑核心（attachment admission：decodeBase64 规范校验 + saveInput / AttachmentStore.saveImages 批次限额）",
        "原版包": "packages/attachment/attachment/src/admission.ts + index.ts",
        "光明模块": "src/附件准入.light",
        "状态": "done",
        "证据": [
            "src/附件准入.light",
            "examples/test_附件准入.light"
        ],
        "本轮目标": "done：复刻 是规范base64（尾比特零校验 + 长度4倍数 + 填充≤2）/解码字节长度/列表包含/存输入/校验图片批次/准入编码图片，并对超限批次抛错（等价原版硬上限）。",
        "反跑判据": "test_附件准入.light：把任一 断言相等 期望值改反即红；把 校验图片批次/准入编码图片 超限抛错用例改为不抛即红。",
        "语言缺陷": [
            "L-036(缺键下标抛 键错误)",
            "L-040(函数定义用 接收)",
            "L-045(写 语句只吃字面量串，诊断走 抛出 新建 错误)"
        ]
    },
    {
        "编号": 50,
        "功能": "bash 工具面向模型的执行结果渲染纯逻辑核心（tool-bash render：streamText / renderResult / renderProcessRead + 沙箱拒绝/升级标记文案）",
        "原版包": "packages/shell/tool-bash/src/render.ts + @deepseek-ai/dsh-sandbox/escalation.ts",
        "光明模块": "src/bash渲染.light",
        "状态": "done（修复 #50 渲染进程读取 两处源码 bug + 根因解析器缺陷 L-048）",
        "证据": [
            "src/bash渲染.light",
            "examples/test_bash渲染.light",
            "examples/test_L048.light"
        ],
        "本轮目标": "done：复刻 streamText/渲染结果/渲染进程读取 三纯函数 + 沙箱拒绝/升级标记内联（em-dash 用 \\u2014）。渲染进程读取 修复：①`读取[\"lossy\"]` 动词名变量下标被误当动词调用（L-048 解析器修复，惠及全语言）；②`字典包含键(沙箱)` 缺键参数笔误→`沙箱 != 空`；③ 沙箱 runnerFailed/denied 下标访问未 字典包含键 守卫→补全守卫。",
        "反跑判据": "test_bash渲染.light：把 流内容/渲染结果/渲染进程读取/沙箱标记 任一 断言相等 期望值改反即红；把 渲染进程读取 沙箱 runnerFailed/denied 用例期望改反即红。",
        "语言缺陷": [
            "L-048(动词名变量[下标] 误当调用，'dict' object is not callable)",
            "L-036(缺键下标抛 键错误，访问可选字段先 字典包含键 守卫)",
            "L-044(含 文本 的函数名会被拆名，模块内用 流内容/取可选值 规避)",
            "L-045(写 语句只吃字面量串，诊断走 抛出 新建 错误)"
        ]
    },
]

for ne in new_entries:
    if ne['编号'] in ids:
        print('跳过已存在编号', ne['编号'])
        continue
    e.append(ne)
    ids.append(ne['编号'])

e.sort(key=lambda x: x['编号'])
d['条目'] = e
json.dump(d, open(p, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('写入完成，条目数=', len(e), '编号=', [x['编号'] for x in e])

# -*- coding: utf-8 -*-
"""流式推流接线契约回归测试（2026-11-18）。

背景：web chat 从「跑完整轮再一次性发 SSE」改造成「边跑边推」时，
引入过三类运行期 NameError/TypeError，均不在语法检查覆盖范围内：

  1) 造流式响应 用到 实时队列/编码SSE帧/流块转增量帧/线程/流发送，
     却漏了对应的「从 … 导入」，导致流式请求一进来就 NameError。
  2) 后台跑一轮 读 载具["服务"]，但 造流式响应 构造载具时没放 "服务" 键 → KeyError。
  3) HTTP服务端 调 响应["流响应"](...) 的实参数量，与 推流实现 的形参数量
     必须一致，否则 TypeError（契约漂移）。

这些错误只有真正 import/调用时才暴露，check 语法检查抓不到。故此文件
对**源码文本**做契约断言，任何一处接线被改断，测试立即变红。
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


WEB = _read(os.path.join('src', 'web服务器.light'))
HTTP_SRV = _read(os.path.join('stdlib', 'HTTP服务端.light'))
RT = _read(os.path.join('src', '实时流.light'))
CLIENT = _read(os.path.join('src', '客户端.light'))
PROXY = _read(os.path.join('src', '代理.light'))


def test_流式依赖全部已导入():
    """造流式响应/推流实现用到的外部符号必须在 web服务器 顶层导入。"""
    # 实时流三件套 + 线程 + 流发送
    assert re.search(r'从\s+实时流\s+导入[^\n]*实时队列[^\n]*编码SSE帧[^\n]*流块转增量帧', WEB), \
        'web服务器 必须导入 实时队列/编码SSE帧/流块转增量帧'
    assert re.search(r'从\s+线程\s+导入[^\n]*线程', WEB), 'web服务器 必须导入 线程'
    assert re.search(r'从\s+HTTP服务端\s+导入[^\n]*流发送', WEB), 'web服务器 必须导入 流发送'


def test_载具与响应都携带服务对象():
    """后台线程读 载具["服务"]，HTTP 层读 响应["服务"]，两处都必须存在。"""
    assert '载具["服务"]' in WEB
    # 造流式响应内必须把 己 作为 "服务" 放进载具
    assert re.search(r'"服务"\s*:\s*己', WEB), '载具缺少 "服务": 己'
    # 响应字典也必须带 "服务" 供 HTTP 层取用（否则 HTTP 层 KeyError）
    assert re.search(r'响应\["服务"\]\s*为\s*己', WEB), '响应字典缺少 服务 键'


def test_流响应回调实参与形参一致():
    """HTTP 层调用 流响应 传 3 参，推流实现 必须恰好 3 参。"""
    m = re.search(r'异步\s+段落\s+推流实现\(([^)]*)\)', WEB)
    assert m, '找不到 推流实现 定义'
    params = [p.strip() for p in m.group(1).split(',') if p.strip()]
    # 允许带默认值参数，但必填参数（无 = 号）必须恰好 3 个
    required = [p for p in params if '=' not in p]
    assert len(required) == 3, f'推流实现 必填形参应为 3 个，实际 {required}'

    calls = re.findall(r'响应\["流响应"\]\(([^)]*)\)', HTTP_SRV)
    assert calls, 'HTTP服务端 未调用 流响应'
    argc = len([a for a in calls[0].split(',') if a.strip()])
    assert argc == len(required), \
        f'流响应 调用实参({argc}) 与 推流实现 形参({len(required)}) 不一致'


def test_实时流模块导出齐全():
    for name in ('实时队列', '编码SSE帧', '文本增量帧', '结束帧', '流块转增量帧'):
        assert re.search(rf'导出\s+{name}\s*$', RT, re.MULTILINE), f'实时流 未导出 {name}'


def test_增量回调链贯通():
    """代理 把 增量回调 透传给 客户端.对话响应；客户端走 HTTPPost流式。"""
    assert '增量回调' in PROXY and '对话响应' in PROXY, '代理 未透传 增量回调'
    assert re.search(r'从\s+HTTP\s+导入[^\n]*HTTPPost流式', CLIENT), '客户端 未导入 HTTPPost流式'
    assert 'HTTPPost流式' in CLIENT, '客户端 未使用 HTTPPost流式'

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

# =====================================================================
# T-0407 收口接线后的契约（2026-11-20）
#   流式路径从「跑一轮」升级为「当 循环（续跑决策 → 队列/插话）」，但三条老契约
#   必须原样成立：仍在 web服务器 内、载具/响应带 服务、推流实现 3 必填形参。
#   这里把新接线也钉住：轮末才关队列、续跑/出队都在这条循环里。
# =====================================================================

def test_后台跑一轮仍是单参且含续跑与出队():
    m = re.search(r'段落\s+后台跑一轮\(([^)]*)\)', WEB)
    assert m, '后台跑一轮 必须留在 web服务器（类体不能放线程目标）'
    params = [p.strip() for p in m.group(1).split(',') if p.strip()]
    assert params == ['载具'], f'后台跑一轮 应只收 载具，实际 {params}'

    body_start = WEB.index('段落 后台跑一轮(')
    body_end = WEB.index('# 推流实现：HTTP 协程侧边取边发', body_start)
    body = WEB[body_start:body_end]
    assert '续续跑决策' in body, '流式路径必须与同步路径共用续跑决策'
    assert '队出队' in body and '队取插话' in body, '轮末必须出队/取插话（同一条循环）'
    assert body.count('队列.关闭()') >= 2, '失败与成功路径都要关闭队列'
    # 关闭必须发生在循环之后：最后一个 队列.关闭 之前不能出现「跳出」之外的退出
    assert body.rindex('队列.关闭()') > body.index('跳出'), '循环未结束就关队列会截断续跑帧'


def test_本轮选项携带压缩配置与计划模式():
    assert '字典设置(本轮选项, "压缩配置"' in WEB, '压缩配置未进入代理选项（自动压缩仍是死代码）'
    assert '"计划模式"' in WEB, '计划模式未从会话模式表接线'
    assert re.search(r'段落\s+造压缩配置[\(:]', WEB), '缺少统一压缩配置构造'


def test_SSE收尾带压缩帧():
    assert '生成压缩事件' in WEB
    # 生成SSE 与 推流实现 各推一帧
    assert WEB.count('生成压缩事件(') >= 3, '生成SSE/推流实现/命令入口 都应能发压缩帧'

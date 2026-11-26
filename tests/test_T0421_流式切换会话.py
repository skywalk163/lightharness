# -*- coding: utf-8 -*-
"""T-0422 流式输出时允许切换会话（先中止当前流，再切换）。

语义选定：**先中止当前流 → 切到目标会话**，与既有「停止」按钮一致——
abort 后 finalizeTurn 保留已渲染内容，不丢已收到的文本；绝不走 rollbackTurn
（那是「请求失败回滚」用的）。

前端交互（真浏览器点一遍）靠手工冒烟；pytest 这里用源码结构断言 + node --check
钉住本次的行为变化与红线（与 T-0398 同一套 `_read` / `_fn_body` 手法）：

  1. `selectSession` 的 streaming 分支不再「弹提示 + return」；
  2. 切会话前先停流（abortActiveTurnForSwitch：finalizeTurn + setStreaming(false) + controller.abort()）；
  3. abort 的异步竞态有世代号（turnEpoch/isTurnAlive）校验，老轮次晚到的回调不打到新会话；
  4. `new-session-btn` 的 streaming 分支同一套收口，不再拦人；
  5. 切走时清空 localQueue（老会话的排队消息不发到新会话），且不静默吞字（放回输入框）；
  6. 红线：停止按钮语义不变、abort 不重复注册、侧边栏协议不动、两个 js 可被 node 解析。

反证（旧 app.js 下必须红）：
  - 第 1 组：旧 `selectSession` 以「正在流式输出中，请稍后再切换会话。」+ return 拦人；
  - 第 2/3 组：旧实现没有 abortActiveTurnForSwitch、没有 turnEpoch，全部断言落空；
  - 第 4 组：旧 new-session-btn 同样以「请稍后再新建会话」拦人；
  - 第 5 组：旧实现切会话时不清 localQueue。
"""
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(name):
    with open(os.path.join(ROOT, 'webui', name), encoding='utf-8') as fh:
        return fh.read()


def _fn_body(src, header, stop_headers):
    """截一个函数/代码块的函数体（从 header 起到 stop_headers 里最早出现处）。"""
    start = src.index(header)
    end = len(src)
    for stop in stop_headers:
        idx = src.find(stop, start)
        if idx != -1:
            end = min(end, idx)
    return src[start:end]


# --------------------------------------------------------------------------- #
# 1. selectSession 不再「提示 + return」拦人
# --------------------------------------------------------------------------- #
def test_切换会话不再拦人():
    app = _read('app.js')
    sel = _fn_body(app, 'function selectSession(id)', ['function renameCurrentSession()'])

    assert '请稍后再切换会话' not in sel, 'selectSession 还在用「请稍后再切换会话」拦人'
    assert '正在流式输出中' not in sel, 'selectSession 还在流式期直接 return'
    # 拦人式的写法（streaming → addSystem(..., true) → return）必须消失
    assert 'addSystem("正在流式输出中，请稍后再切换会话。", true)' not in app

    # 同会话（刷新/重选）仍是早返回，不触发停流（不误伤正在跑的同会话）
    assert 'if (id === sessionId)' in sel, '同会话早返回分支被拆掉'
    assert 'if (!id) return;' in sel, '空 id 守卫被拆掉'
    same = sel[:sel.index('if (streaming)')]
    assert 'abortActiveTurnForSwitch' not in same, '同会话路径也停了流'


# --------------------------------------------------------------------------- #
# 2. 流式中切换 = 先停流（收口 UI + abort 底层请求），再走原来的拉历史路径
# --------------------------------------------------------------------------- #
def test_流式中切换先停流():
    app = _read('app.js')
    assert 'function abortActiveTurnForSwitch()' in app, '缺少切会话停流的统一收口'

    helper = _fn_body(app, 'function abortActiveTurnForSwitch()',
                      ['// 切换后给一句中文交代'])
    # 收口语义：保留已渲染内容（finalizeTurn），不丢已收到的文本；不删气泡、不回滚
    assert 'finalizeTurn()' in helper, '停流没有走 finalizeTurn（已渲染内容会丢）'
    assert 'rollbackTurn' not in helper, '切会话误用了失败回滚（会撤掉已收到的文本）'
    # 结束本地计时/streaming class 由 setStreaming(false) 一并收口
    assert 'setStreaming(false)' in helper, '没有结束本地计时/streaming 态'
    # abort 由 stream 自己的 controller 发起，不重复注册、不新造通道
    assert 'controller.abort()' in helper, '没有真正 abort 当前流'
    assert 'new AbortController' not in helper, '切会话新造了一个 controller（应复用当前流）'

    sel = _fn_body(app, 'function selectSession(id)', ['function renameCurrentSession()'])
    assert 'if (streaming) abortedQueue = abortActiveTurnForSwitch();' in sel, \
        'selectSession 没有先停流'
    assert sel.index('abortActiveTurnForSwitch') < sel.index('fetch("/api/sessions/"'), \
        '停流动作晚于拉历史（会先切过去再收口，UI 串味）'
    # 停流后仍走原来的「拉完整历史 + 回放」路径（没有另造端点）
    for keep in ('fetch("/api/sessions/" + encodeURIComponent(id)', 'Messages.renderHistory(list)'):
        assert keep in sel, f'切换会话的原路径被拆掉：{keep}'

    # 中文交代存在，且放在新会话渲染之后发（renderHistory 会清屏，先发会被吃掉）
    assert 'function announceStreamAborted(' in app, '没有切会话的中文交代'
    assert '已停止当前输出并切换会话' in app, '缺少「已停止当前输出并切换会话」提示'
    assert sel.index('Messages.renderHistory(list)') < sel.index('announceStreamAborted(abortedQueue)'), \
        '切换提示早于渲染，会被清屏带走'


# --------------------------------------------------------------------------- #
# 3. abort 异步竞态：世代号（epoch）校验，老轮次晚到的回调不落到新会话
# --------------------------------------------------------------------------- #
def test_abort竞态有世代号校验():
    app = _read('app.js')
    assert 'var turnEpoch = 0;' in app, '没有轮次世代号'
    assert 'function isTurnAlive(epoch)' in app, '没有 epoch 判定函数'

    helper = _fn_body(app, 'function abortActiveTurnForSwitch()',
                      ['// 切换后给一句中文交代'])
    assert 'turnEpoch += 1' in helper, '切走时没有作废老轮次'

    send = _fn_body(app, 'function sendMessage(overrideText)', ['function handleHttpError('])
    assert 'var myEpoch = turnEpoch;' in send, '本轮没有快照 epoch'
    # 响应/收尾/异常/收口四条路径都要先比对轮次存活。
    # T-0490 把裸 isTurnAlive(myEpoch) 收敛成 serialAlive()（= mySerial === sendSerial &&
    #   isTurnAlive(myEpoch)，多一道「被新轮接管」判定），语义只强不弱；两种写法都接受，
    #   但覆盖处数仍必须 ≥ 4（不许为了过判据删守卫）。
    guard = send.count('serialAlive()') + send.count('isTurnAlive(myEpoch)')
    assert guard >= 4, \
        '竞态校验没覆盖 resp.ok / then / catch / finally：%d 处' % guard
    if 'serialAlive()' in send:
        # 收敛形式必须真的把 epoch 与 serial 都算进去，不能退化成只看其中一个
        assert re.search(r'function serialAlive\(\)\s*\{\s*return\s+[^}]*isTurnAlive\(myEpoch\)', app), \
            'serialAlive 没有把 isTurnAlive(myEpoch) 算进去（等于丢了 epoch 守卫）'
        assert re.search(r'function serialAlive\(\)\s*\{\s*return\s+mySerial\s*===\s*sendSerial', app), \
            'serialAlive 没有把 mySerial === sendSerial 算进去（等于丢了轮次接管守卫）'
    assert 'readStream(resp, myEpoch)' in send, 'SSE 读取没带上 epoch（残留帧会写进新会话）'
    assert ('if (!isTurnAlive(myEpoch)) return;   // T-0422：切会话后老请求的失败不落到新会话' in send
            or 'if (!serialAlive()) return;   // T-0490/T-0422：切会话或被新轮接管后，老请求失败不落到新会话' in send), \
        'catch 没有 epoch/轮次守卫（AbortError 晚到会 finalize 新会话）'
    assert ('if (!isTurnAlive(myEpoch)) return;\n      setStreaming(false);' in send
            or 'if (!serialAlive()) return;\n      setStreaming(false);' in send), \
        'finally 没有 epoch/轮次守卫（老轮次收尾会关掉新会话的流）'

    stream = _fn_body(app, 'function readStream(resp, epoch)',
                      ['// ---------- T-0398：一键压缩'])
    assert stream.count('isTurnAlive(epoch)') >= 2, 'readStream 的帧处理/泵没有按 epoch 停手'
    assert 'if (!isTurnAlive(epoch)) { finished = true; return; }' in stream, \
        '残留 SSE 帧没有丢弃（会往新会话追加文本）'
    # 自动补的 controller 清理不能把新会话的 controller 置空（helper 里已置空）
    assert 'controller = null;' in helper


# --------------------------------------------------------------------------- #
# 4. new-session-btn 的 streaming 分支同一套收口（不拦人、不漂移）
# --------------------------------------------------------------------------- #
def test_新建会话同样先停流():
    app = _read('app.js')
    btn = _fn_body(app, 'var newSessionBtn = document.getElementById("new-session-btn")',
                   ['// E3：会话侧边栏'])

    assert '请稍后再新建会话' not in btn, 'new-session-btn 还在流式期拦人'
    assert 'if (streaming) abortedQueue = abortActiveTurnForSwitch();' in btn, \
        '新建会话没有走同一套停流收口（两处会漂移）'
    assert btn.index('abortActiveTurnForSwitch') < btn.index('newChatState()'), \
        '先清了空状态才停流（顺序反了）'
    assert 'newChatState()' in btn, '新建会话的空状态路径被拆掉'
    assert 'announceStreamAborted(abortedQueue)' in btn, '新建会话没有中文交代'
    # 捕获阶段拦点击、不动 sidebar.js 的既有协议
    assert 'e.stopPropagation()' in btn and 'e.preventDefault()' in btn, '捕获阶段拦截被拆掉'
    assert '}, true);' in btn, '监听不再是捕获阶段'


# --------------------------------------------------------------------------- #
# 5. 队列取舍：切走时清空老会话的排队消息，并把文本放回输入框（不静默吞字）
# --------------------------------------------------------------------------- #
def test_切会话清空本地队列():
    app = _read('app.js')
    helper = _fn_body(app, 'function abortActiveTurnForSwitch()',
                      ['// 切换后给一句中文交代'])

    assert 'var droppedQueue = localQueue.slice();' in helper, '没有摘下老会话的排队消息'
    assert 'localQueue.length = 0;' in helper, '没有清空 localQueue（会发到新会话去）'
    assert 'renderQueueChip()' in helper, '清队列后没有刷新排队角标'
    # 队列清空必须早于 setStreaming(false)：后者会 setTimeout(flushLocalQueue) 把队列发出去
    assert helper.index('localQueue.length = 0;') < helper.index('setStreaming(false);'), \
        '先 setStreaming(false) 再清队列（flushLocalQueue 会把老消息发到新会话）'
    # 文本放回输入框，不静默丢掉用户写下的字
    assert 'inputEl.value = lost.join(' in helper, '排队消息被静默丢弃，没有放回输入框'
    assert '条排队消息已放回输入框' in app, '缺「排队消息已放回输入框」的中文交代'


# --------------------------------------------------------------------------- #
# 6. 红线：停止按钮语义不变、abort 不重复注册、侧边栏协议不动、不新增端点
# --------------------------------------------------------------------------- #
def test_停止按钮与红线():
    app = _read('app.js')

    # 停止按钮仍绑 stopStreaming，且只注册一次
    assert 'stopBtn.addEventListener("click", stopStreaming);' in app, '停止按钮绑定被改'
    assert app.count('addEventListener("click", stopStreaming)') == 1, 'abort 入口被重复注册'
    stop = _fn_body(app, 'function stopStreaming()', ['// ---------- 输入框'])
    assert 'controller.abort()' in stop, '停止按钮不再 abort 当前流'
    # 停止按钮路径不新增 UI 清屏动作（保留已渲染内容的语义不变）
    assert 'Messages.clear' not in stop and 'rollbackTurn' not in stop, '停止按钮被改成回滚语义'

    # 用户主动中止仍走 AbortError → finalizeTurn（与「发送失败回滚」区分开）
    send = _fn_body(app, 'function sendMessage(overrideText)', ['function handleHttpError('])
    catch = send[send.index('.catch(function (err)'):]
    abort_seg = catch[:catch.index('} else if (started)')]
    assert 'err.name === "AbortError"' in abort_seg, 'AbortError 分支被拆掉'
    assert 'finalizeTurn()' in abort_seg, '主动中止没有保留已渲染内容'
    assert 'rollbackTurn' not in abort_seg, '主动中止误走了失败回滚'

    # 侧边栏协议不动：仍只是 onSelect → selectSession（不改列表/新建协议）
    assert 'onSelect: function (id) { selectSession(id); }' in app, '侧边栏 onSelect 协议被改'
    # 不新增端点（判「不含」而不是集合相等，避免并行卡假红）
    assert '/api/sessions/stream' not in app, '新增了流式会话端点（红线）'


# --------------------------------------------------------------------------- #
# 7. 两个 node --check 靶子可解析（verify 跑的是同一条命令）
# --------------------------------------------------------------------------- #
def test_前端两个js可被node解析():
    for name in ('app.js', 'messages.js'):
        path = os.path.join(ROOT, 'webui', name)
        p = subprocess.run(['node', '--check', path], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=60)
        assert p.returncode == 0, f'node --check webui/{name} 失败：\n{p.stdout}\n{p.stderr}'

# -*- coding: utf-8 -*-
"""T-0398 输入区增强：空会话附件暂存 + 上下文用量/一键压缩入口。

前端行为（chip 保留/清空、压缩确认弹窗）靠浏览器手工冒烟（清单见 .hive/summary.md），
pytest 这里判的是**能机器验证的两端**：

  1. 服务端对 `attachments` 的接收面：任意形状（正常三元组 / 空数组 / 多带键 /
     不是数组 / 条目缺键 / 条目不是对象）都必须被稳健接收——不 500、不改答复；
     且 `attachments` 不能绕过既有的 `messages` 必填校验（缺用户消息仍 400）。
  2. 上送协议形状不动（红线）：前端只投影 {name, type, dataUrl} 三个键，
     仍挂在 body.attachments 上，不新增上传端点。
  3. 附件上限落在前端（服务端当前不校验数量/体积）：20 个 / 单文件 10MB，
     超限中文提示并跳过；发送成功才清 chips（400/网络失败要能重试）。
  4. 暂存语义：newChatState 不清空；切换到别的已有会话才清空且有中文提示。
  5. 压缩入口：输入区「上下文 xx%」+「压缩」按钮，走既有 /compact 通道
     （同一条 POST /v1/chat/completions），不自造算法、不新增端点、不动阈值默认值；
     斜杠面板 /compact 双入口保留，文案与按钮一致。
  6. 两个 node --check 靶子可解析（verify 的同一条命令，这里给 pytest 侧兜底）。

反证（旧实现下必须红）：
  - 第 3 组：旧 sendMessage 在请求发出前就 clearAttachments() → 找不到「受理后才清」的锚点 → 红；
  - 第 4 组：旧 selectSession 既不清空待发附件、也没有切会话中文提示 → 红；
  - 第 5 组：旧 index.html 没有 ctx-usage / compact-btn，斜杠面板 /compact 文案也不一致 → 红。

防回归（旧实现本来就满足，这里用断言锁住，别让后续改造回退）：
  - newChatState 不清空附件（本次只在它后面补了「已保留 N 个待发附件」的中文提示）。
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240


def _lp(p) -> str:
    """把宿主路径写成 .light 字符串字面量：用正斜杠，避免反斜杠被当转义。"""
    return str(p).replace('\\', '/')


def _find_sibling(name):
    """运行时依赖的兄弟仓定位（沿祖先逐级找，判据按仓区分——T-0395/T-0396 踩过的坑）。"""
    key = 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'
    marker = '插件' if name == 'LIGHTPLUGIN' else 'src'
    names = [key] if name == 'LIGHTPLUGIN' else ['light', 'light-merge']
    here = ROOT
    candidates = []
    explicit = os.environ.get(name, '')
    if explicit:
        candidates.append(explicit)
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        for nm in names:
            candidates.append(os.path.join(here, nm))
            candidates.append(os.path.join(here, 'duan-light-merge', nm))
    candidates.append('/home/skywalk/dswork/' + key)
    candidates.append('/home/skywalk/dswork/light-merge')
    for c in candidates:
        if c and os.path.isdir(os.path.join(c, marker)):
            return os.path.normpath(c)
    return ''


def _run(src: str, tmp_path):
    """在独立子进程里跑一段光明驱动脚本，返回 (rc, 合并输出, {键: 值})。"""
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(tmp_path), env=env,
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return p.returncode, p.stdout + p.stderr, kv


def _read(name):
    with open(os.path.join(ROOT, 'webui', name), encoding='utf-8') as fh:
        return fh.read()


def _fn_body(src, header, stop_headers):
    """截一个函数的函数体（从 header 起到 stop_headers 里最早出现处）。"""
    start = src.index(header)
    end = len(src)
    for stop in stop_headers:
        idx = src.find(stop, start)
        if idx != -1:
            end = min(end, idx)
    return src[start:end]


BOOT = '''
从 web服务器 导入 Web服务端, 全局服务, 路由处理器
从 总入口 导入 组装注册表
从 JSON 导入 序列化JSON
从 字符串处理 导入 编码
从 流 导入 造块开始, 造文本增量, 造块结束, 造结束, 造停止原因
'''

MOCK = '''
类 模拟客户端:
  属性 模型名 等于 "deepseek-chat"
  属性 回应表 等于 空
  属性 应答序号 等于 0

  段落 构造(回应清单):
    设 己.模型名 为 "deepseek-chat"
    设 己.回应表 为 回应清单
    设 己.应答序号 为 0

  段落 对话响应(消息表, 选项表, 工具表):
    如果 己.应答序号 >= 长(己.回应表):
      设 己.应答序号 为 长(己.回应表) - 1
    设 回应文本 为 己.回应表[己.应答序号]
    设 己.应答序号 为 己.应答序号 + 1
    返回 [造块开始(0, "text"), 造文本增量(0, 回应文本), 造块结束(0, ["type": "text", "text": 回应文本]), 造结束(造停止原因())]
'''

# 统一请求构造：一次 POST，返回 {状态, 体, 含回复}
#   路由处理器是异步段落 → 这里的助手也必须是 async，调用点写 `等待 发(...)`
POST = '''
异步 段落 发(载荷):
  设 体 为 编码(序列化JSON(载荷))
  设 应 为 等待 路由处理器(["方法": "POST", "路径": "/v1/chat/completions", "头": {}, "体": 体])
  设 文本 为 ""
  如果 应["体"] != 空:
    设 文本 为 转字符串(应["体"])
  返回 ["状态": 应["状态"], "体": 文本, "含回复": (文本.查找("T0398-OK") >= 0)]
'''

PROBE = '''
# ① 正常三元组（协议既有形状）
设 正 为 等待 发(["messages": [["role": "user", "content": "带附件"]], "attachments": [["name": "a.txt", "type": "text/plain", "dataUrl": "data:text/plain;base64,QUJD"]]])
# ② 空数组
设 空表 为 等待 发(["messages": [["role": "user", "content": "空附件"]], "attachments": []])
# ③ 多带一个键（体积等前端自有字段本不该上送；上送了也不该炸）
设 多 为 等待 发(["messages": [["role": "user", "content": "多带键"]], "attachments": [["name": "b.png", "type": "image/png", "dataUrl": "data:image/png;base64,QUJD", "size": 123]]])
# ④ 不是数组（形状错）
设 非表 为 等待 发(["messages": [["role": "user", "content": "不是数组"]], "attachments": ["name": "x"]])
# ⑤ 条目缺 dataUrl
设 缺键 为 等待 发(["messages": [["role": "user", "content": "缺键"]], "attachments": [["name": "c.bin", "type": "application/octet-stream"]]])
# ⑥ 条目根本不是对象（字符串）
设 怪项 为 等待 发(["messages": [["role": "user", "content": "怪条目"]], "attachments": ["不是对象"]])
# ⑦ attachments 在场也不能绕过 messages 必填
设 缺消息 为 等待 发(["attachments": [["name": "d.txt", "type": "text/plain", "dataUrl": "data:text/plain;base64,QUJD"]]])
'''

REPORT = '''
打印("正状态=" + 转字符串(正["状态"]))
打印("正含回复=" + 转字符串(正["含回复"]))
打印("空表状态=" + 转字符串(空表["状态"]))
打印("多状态=" + 转字符串(多["状态"]))
打印("多含回复=" + 转字符串(多["含回复"]))
打印("非表状态=" + 转字符串(非表["状态"]))
打印("缺键状态=" + 转字符串(缺键["状态"]))
打印("怪项状态=" + 转字符串(怪项["状态"]))
打印("缺消息状态=" + 转字符串(缺消息["状态"]))
打印("缺消息体=" + 缺消息["体"])
'''


def _main(body):
    return '异步 段落 主():\n' + ''.join(
        ('  ' + line if line.strip() else line) + '\n' for line in body.strip('\n').split('\n')
    ) + '\n异步 运行 主()\n'


# --------------------------------------------------------------------------- #
# 1. 服务端接收面：任意 attachments 形状都不能把请求打崩，也不能绕过校验
# --------------------------------------------------------------------------- #
def test_服务端稳健接收附件形状(tmp_path):
    src = BOOT + MOCK + POST + (
        '\n异步 段落 主():\n'
        f'  设 注册表 为 组装注册表()\n'
        f'  设 客户端 为 新建 模拟客户端(["T0398-OK"])\n'
        f'  全局服务.配置(客户端, 注册表, "{_lp(tmp_path)}", 30.0, "")\n'
        + ''.join('  ' + line + '\n' for line in PROBE.strip('\n').split('\n'))
        + ''.join('  ' + line + '\n' for line in REPORT.strip('\n').split('\n'))
        + '  全局服务.停止()\n'
        '\n异步 运行 主()\n'
    )
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'

    # 正常三元组：200 且答复不受附件影响（服务端目前只接收、不消费 content 之外的字段）
    assert kv['正状态'] == '200', f'带合法 attachments 的请求被拒了\n{out}'
    assert kv['正含回复'] == 'True', f'答复里没有 mock 文本，链路没走通\n{out}'
    # 空数组：200
    assert kv['空表状态'] == '200', out
    # 多带键：200（形状之外的键不改请求语义，也不该 500）
    assert kv['多状态'] == '200', f'多带键的附件让服务端崩了（不该 500）\n{out}'
    assert kv['多含回复'] == 'True', out
    # 形状错（不是数组 / 缺键 / 条目不是对象）：仍然 200，不 500
    assert kv['非表状态'] == '200', f'attachments 不是数组时服务端 5xx/4xx：{kv["非表状态"]}\n{out}'
    assert kv['缺键状态'] == '200', f'条目缺 dataUrl 时服务端 5xx/4xx：{kv["缺键状态"]}\n{out}'
    assert kv['怪项状态'] == '200', f'条目不是对象时服务端 5xx/4xx：{kv["怪项状态"]}\n{out}'
    # 红线：attachments 不能把「必须有用户消息」的校验绕过去
    assert kv['缺消息状态'] == '400', f'缺 messages 却没 400：{kv["缺消息状态"]}\n{out}'
    assert 'messages' in kv['缺消息体'], f'400 不说原因：{kv["缺消息体"]}\n{out}'


# --------------------------------------------------------------------------- #
# 2. 上送协议形状不动：只投影三个键，仍挂 body.attachments，不新增端点
# --------------------------------------------------------------------------- #
def test_上送协议形状不变():
    app = _read('app.js')

    # 投影只出 name/type/dataUrl 三个键
    proj = _fn_body(app, 'function projectAttachments(list)', ['function formatSize('])
    for key in ('name:', 'type:', 'dataUrl:'):
        assert key in proj, f'projectAttachments 少了协议键 {key}'
    for extra in ('size:', 'lastModified:', 'path:'):
        assert extra not in proj, f'projectAttachments 上送了协议外的键 {extra}（红线：形状不变）'

    # 仍挂在 body.attachments 上（老协议名，一个字没改）
    assert 'body.attachments = sentAttachments' in app, '附件没挂到 body.attachments'
    # 不新增上传/压缩端点：app.js 里所有 /api 路径都不许带 attach/upload/file/compact 字样
    #   （判「不含」而不是判「集合相等」——并行卡 T-0397 等还会往这里加端点，等价断言会假红）
    api_paths = set(re.findall(r'"/api/[^"]*"', app))
    for p in api_paths:
        assert not re.search(r'attach|upload|file|compact', p, re.I), \
            f'新增了附件/压缩专用端点（红线）：{p}'
    # 既有端点一个都没被拆掉
    for keep in ('"/api/approvals"', '"/api/config"', '"/api/models"',
                 '"/api/permissions"', '"/api/sessions/"', '"/api/sessions/current?session="'):
        assert keep in api_paths, f'既有端点被改掉了：{keep}'
    assert '/v1/attachments' not in app and '/api/upload' not in app, '新增了文件上传端点（红线）'


# --------------------------------------------------------------------------- #
# 3. 附件上限与「成功后才清 chips」：都在前端，都不写 localStorage
# --------------------------------------------------------------------------- #
def test_附件上限与清空时机():
    app = _read('app.js')

    assert 'MAX_ATTACHMENTS = 20' in app, '数量上限不是 20'
    assert 'MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024' in app, '单文件上限不是 10MB'
    # 超限必须给中文理由并跳过该文件
    on_files = _fn_body(app, 'function onFiles(fileList)', ['function clearAttachments('])
    assert '超过单文件上限 10MB，已跳过该文件' in on_files, '单文件超限没有中文提示'
    assert '个待发附件，「' in on_files, '数量超限没有中文提示'
    assert 'MAX_ATTACHMENTS' in on_files, '数量上限没在选文件路径上判'

    # 发送成功（服务端受理）之后才清 chips；失败分支不得出现 clearAttachments
    send = _fn_body(app, 'function sendMessage(overrideText)', ['function handleHttpError('])
    assert 'if (sentAttachments) clearAttachments();' in send, 'chips 不是在服务端受理后才清'
    assert send.index('resp.ok') < send.index('if (sentAttachments) clearAttachments();'), \
        'clearAttachments 早于 resp.ok 判定（400/网络失败会丢 chips）'
    # 请求前不再有裸 clearAttachments()（旧实现的反跑点）
    pre = send[:send.index('return fetch(API_PATH')]
    assert 'clearAttachments()' not in pre, '请求发出前就清了 chips（失败无法重试）'

    # 附件只存内存：不写 localStorage（体积与隐私红线）
    assert 'lh.attachments' not in app, '附件进了 localStorage（红线）'
    for line in app.splitlines():
        if 'localStorage' in line and 'setItem' in line:
            assert 'attach' not in line.lower(), '往 localStorage 写附件：' + line.strip()


# --------------------------------------------------------------------------- #
# 4. 暂存语义：新建不清空；切到别的已有会话才清空且有中文提示
# --------------------------------------------------------------------------- #
def test_暂存语义():
    app = _read('app.js')

    new_chat = _fn_body(app, 'function newChatState()', ['function selectSession(id)'])
    assert 'clearAttachments' not in new_chat, 'newChatState 还在清空附件（红线：空白页先挂文件）'
    assert '保留 ' in new_chat and '待发附件' in new_chat, '新建会话没说明附件被保留'

    sel = _fn_body(app, 'function selectSession(id)', ['function renameCurrentSession()'])
    assert 'clearAttachments()' in sel, '切到已有会话没清空待发附件'
    assert '已切换到别的会话，清空了' in sel, '切会话清空时没有中文提示'
    assert '未发送的附件' in sel, '提示没说清是「未发送的附件」'
    # 同会话早返回分支不能有清空动作（刷新/重选同一会话不该丢草稿）
    same = sel[:sel.index('fetch("/api/sessions/" + encodeURIComponent(id)')]
    assert 'clearAttachments' not in same, '同会话路径也会清空附件'

    # index.html 既有附件锚点一个都没动
    index = _read('index.html')
    for keep in ('attach-chips', 'attach-input', 'attach-btn', 'input', 'send-btn', 'messages'):
        assert ('id="%s"' % keep) in index, f'index.html 动了既有 id：{keep}'


# --------------------------------------------------------------------------- #
# 5. 压缩入口：用量展示 + 一键压缩走既有 /compact 通道（双入口、文案一致）
# --------------------------------------------------------------------------- #
def test_压缩入口与双入口():
    app = _read('app.js')
    index = _read('index.html')
    style = _read('style.css')
    palette = _read('slash-palette.js')
    messages = _read('messages.js')

    # DOM 锚点
    assert 'id="ctx-usage"' in index, 'index.html 缺上下文用量锚点'
    assert 'id="compact-btn"' in index, 'index.html 缺压缩按钮'
    assert 'id="attach-chips"' in index, '附件 chips 容器被动了'

    # 用量渲染：同一个「上下文使用率」字段，统计帧与压缩帧都要刷新
    assert 'function renderContextUsage(' in app, '没有用量渲染函数'
    assert 'renderContextUsage(pct);' in app, '统计帧没刷新输入区用量'
    assert 'function handleCompactionEvent(' in app, '压缩帧没有专门处理'
    assert 'handleCompactionEvent(json);' in app, '种类=压缩 帧没走 handleCompactionEvent'
    assert 'renderContextUsage(' in _fn_body(app, 'function handleCompactionEvent(', ['// ---------- E4：审批 UI']), \
        '压缩事件到达后没有刷新用量'

    # 一键压缩：确认弹窗 + 走既有通道（"/compact" 作为消息发到同一条 completions 端点）
    assert 'function requestCompaction(' in app, '没有一键压缩入口'
    confirm = _fn_body(app, 'var COMPACT_CONFIRM_TEXT', ['function requestCompaction('])
    assert '摘要' in confirm, '确认文案没说明旧消息进摘要'
    assert '保留最近' in confirm, '确认文案没说明保留最近 N 条'
    assert 'window.confirm(COMPACT_CONFIRM_TEXT)' in app, '压缩前没有二次确认'
    assert 'sendMessage("/compact")' in app, '没走既有 /compact 通道'
    assert 'compactBtn.addEventListener("click", requestCompaction)' in app, '压缩按钮没绑上'
    # 不自造压缩算法、不动阈值默认值
    assert 'HARNESS_COMPACTION_THRESHOLD' not in app, '前端动了自动压缩阈值（红线）'

    # 双入口：斜杠面板 /compact 项保留，且选中后与按钮走同一条路
    assert '"/compact"' in palette, '斜杠面板的 /compact 被删了（双入口红线）'
    assert '压缩上下文：旧消息进摘要，保留最近消息' in palette, '/compact 文案与按钮不一致'
    assert "cmd === '/compact'" in app.replace('"', "'"), '/compact 面板项没有接到 requestCompaction'
    assert 'requestCompaction();' in app, '面板项 /compact 没触发压缩'

    # 样式钩子：压缩提示 + 用量/按钮（不引第三方 UI 库）
    for rule in ('.compact-btn', '.ctx-usage', '.ctx-usage.danger', '.sys.compaction', '.composer-right'):
        assert rule in style, f'style.css 缺 {rule} 规则'
    assert 'addCompaction: addCompaction' in messages, 'messages.js 没导出压缩提示钩子 addCompaction'
    assert 'Messages.addCompaction' in app, 'app.js 没走 messages.js 的压缩提示样式钩子'
    assert '<script src="http' not in index and 'cdn' not in index.lower(), 'index.html 引了外部脚本（红线）'


# --------------------------------------------------------------------------- #
# 6. 两个 node --check 靶子可解析（verify 跑的是同一条命令）
# --------------------------------------------------------------------------- #
def test_前端两个js可被node解析():
    for name in ('app.js', 'messages.js'):
        path = os.path.join(ROOT, 'webui', name)
        p = subprocess.run(['node', '--check', path], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=60)
        assert p.returncode == 0, f'node --check webui/{name} 失败：\n{p.stdout}\n{p.stderr}'

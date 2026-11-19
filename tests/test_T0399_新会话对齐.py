# -*- coding: utf-8 -*-
"""T-0399 对齐验收：新会话「五件事」整链 E2E（HTTP 层）。

T-0395（会话 cwd）、T-0396（新会话面板 + 只读目录校验）、T-0397（会话模式/权限）、
T-0398（附件暂存 / 用量+压缩入口）单卡 verify 各自的绿，只证明各自那一段；
本卡判的是**串起来**还能不能用：

  1. `POST /api/sessions{标题,工作目录}` → `GET current` 的 cwd 正确；
  2. 首条 `/v1/chat/completions` 带 `preset` + 权限预设 + `attachments`
     → 会话记录四键（工作目录/模式/权限预设/模型）齐全，且附件字段不打断首条落库；
  3. 两个会话不同目录 + 不同权限**并发** → 目录/权限互不串，工具判定各按各会话；
  4. 触发压缩后会话仍能继续发消息（压缩遮蔽旧事件后，续聊/落库/重读都不炸）；
  5. 切回旧会话 → 模式/权限/目录按会话恢复（API 层断言）。

每个用例起一个独立 Light 子进程，走真实 `Web服务端` 的**路由处理器方法**
（与 T-0395/T-0396/T-0397 同一套「web server 测试模式」），不依赖外网与真实大模型。
反证（中间态必红）：只合入 T-0395 时，本文件第 1/2/3/5 组都会因为
「详情 / current 没有 模式、权限预设 键」「创建期不带模式权限」「会话级权限不生效」而失败——
证明这些用例真的串了 T-0395~T-0397 的链路，而不是只测单卡。

已知边界（不在本卡改业务代码，已登记新卡）：
  - 文件类工具仍是零参 `取根目录()`（HARNESS_ROOT/进程 cwd），**没有**按会话 cwd 取根；
    故第 3 组「路径安全」按「会话详情里的 cwd 作为根」判，真机工具执行仍走进程根。
  - `/v1/chat/completions` 目前不消费 `attachments`（前端 best-effort 上送），
    故第 1 组只判「附件在场不打断首条消息」，不判附件落库。
  - Web 层尚无压缩触发端点（`/compact` 只作为一条消息），第 4 组用 `压缩.light`
    的公共入口 `压缩到最近` 在服务实例上触发，其余动作仍走 HTTP 处理器。
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180


@pytest.fixture
def work():
    """短基准目录：Windows 上 projectKey 编码会把会话目录撑到 MAX_PATH 之外，
    用 pytest 默认的长临时目录会让「新建会话」本身 500（与本卡判据无关的环境限制）。"""
    p = pathlib.Path(tempfile.mkdtemp(prefix='lt'))
    try:
        yield p
    finally:
        shutil.rmtree(p, ignore_errors=True)


def _lp(p) -> str:
    """把宿主路径写成 .light 字符串字面量：一律正斜杠，避免反斜杠被当转义。"""
    return str(p).replace('\\', '/')


def _find_repo(env_name, dir_name):
    """沿祖先逐级探测兄弟仓（worktree 深度不固定，口径同 运行.py / T-0396）。"""
    cands = []
    explicit = os.environ.get(env_name, '')
    if explicit:
        cands.append(explicit)
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        cands.append(os.path.join(here, dir_name))
        cands.append(os.path.join(here, 'duan-light-merge', dir_name))
    cands.append('/home/skywalk/dswork/' + dir_name)
    for c in cands:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _env():
    # 关键：清掉 HARNESS_ROOT，否则工具取根被强制覆盖成仓根，工具用例失去意义；
    # 同时清掉会改变会话/权限默认值的宿主变量，保证子进程只看本用例给的输入。
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_COMPACTION_THRESHOLD', 'HARNESS_COMPACTION_KEEP_ROUNDS')}
    for key, repo in (('LIGHTPLUGIN', 'lightplugin'), ('LIGHT_MERGE', 'light-merge')):
        found = _find_repo(key, repo)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _run(src, work):
    f = work / 'driver.light'
    f.write_text(src, encoding='utf-8')
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(work), env=_env(),
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return p.returncode, p.stdout + p.stderr, kv


def _norm(s) -> str:
    return os.path.normcase(os.path.normpath(str(s).strip()))


def _same(a, b) -> bool:
    return _norm(a) == _norm(b)


BOOT = r'''
从 web服务器 导入 Web服务端
从 会话存储 导入 会话存储
从 字符串处理 导入 编码
从 JSON 导入 解析JSON, 序列化JSON
从 文件系统 导入 路径连接, 创建目录, 写入文件
从 编码解码 导入 URL编码
从 认证 导入 初始化认证
从 总入口 导入 组装注册表
从 权限 导入 预设全放行, 预设全拒绝, 预设按类别
从 工具_路径安全 导入 解析安全路径
从 内置核心判型 导入 是字典
从 内置核心字典 导入 字典包含键, 字典设置
从 线程 导入 线程
从 压缩 导入 压缩到最近
从 流 导入 造块开始, 造文本增量, 造块结束, 造结束, 造停止原因, 造工具调用增量, 造工具调用原因
初始化认证()
'''

TEXT_MOCK = r'''
类 文本客户端:
  属性 模型名 等于 "mock"
  段落 构造:
    设 己.模型名 为 "mock"
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    设 文本 为 "ok"
    返回 [造块开始(0, "text"), 造文本增量(0, 文本),
      造块结束(0, ["type": "text", "text": 文本]), 造结束(造停止原因())]
'''

TOOL_MOCK = r'''
类 工具客户端:
  属性 模型名 等于 "mock"
  段落 构造:
    设 己.模型名 为 "mock"
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    # 只在「还没出现过工具调用」时发一次 读文件；续轮（含被拒绝的续轮）回文本，
    # 保证一轮最多两次调用、不会把用例拖成死循环。
    设 已调 为 假
    遍历 消息 之 消息表:
      如果 是字典(消息):
        如果 字典包含键(消息, "tool_calls"):
          设 已调 为 真
    如果 已调:
      设 文本 为 "完成"
      返回 [造块开始(0, "text"), 造文本增量(0, 文本),
        造块结束(0, ["type": "text", "text": 文本]), 造结束(造停止原因())]
    设 参数 为 序列化JSON(["路径": "own.txt"])
    返回 [造块开始(0, "tool-call"), 造工具调用增量(0, "c1", "读文件", 参数),
      造块结束(0, ["type": "tool-call", "id": "c1", "name": "读文件", "arguments": 参数]),
      造结束(造工具调用原因())]
'''


def _service(root):
    """起一个 Web服务端 实例（不真监听端口；直接走处理器方法）。"""
    return f'''
设 根 为 "{_lp(root)}"
设 库 为 新建 会话存储(路径连接(根, "sessions"))
设 服 为 新建 Web服务端()
服.设置会话库(库)
服.根 为 根
'''


def _create(ident, title, pairs=()):
    """POST /api/sessions：多于两个键就用 字典设置 逐键塞，避开内联字典的解析上限。"""
    lines = [f'设 {ident}入参 为 ["标题": "{title}"]']
    for k, v in pairs:
        lines.append(f'字典设置({ident}入参, "{k}", {v})')
    lines.append(
        f'设 {ident} 为 服.处理新建会话(["方法": "POST", "路径": "/api/sessions", '
        f'"头": {{}}, "体": 编码(序列化JSON({ident}入参))], "")'
    )
    return '\n'.join(lines) + '\n'


def _chat_body(name, sid, text, pairs=()):
    lines = [f'设 {name}入参 为 ["model": "mock"]',
             f'字典设置({name}入参, "messages", [["role": "user", "content": "{text}"]])',
             f'字典设置({name}入参, "session_id", {sid})']
    for k, v in pairs:
        lines.append(f'字典设置({name}入参, "{k}", {v})')
    lines.append(f'设 {name} 为 序列化JSON({name}入参)')
    return '\n'.join(lines) + '\n'


# --------------------------------------------------------------------------- #
# 1. 建会话带目录 → 首条消息带 preset/权限/附件 → 四键齐全 + 重启可恢复
# --------------------------------------------------------------------------- #
def test_新建会话五件事串成一条链路(work):
    target = work / '对齐目录'
    target.mkdir()
    d = _lp(target)

    src = BOOT + TEXT_MOCK + _service(work) + f'''
服.配置(新建 文本客户端(), 组装注册表(), 根, 30.0, "", 空)
''' + _create('建应', '对齐', [('工作目录', f'"{d}"')]) + f'''
设 元 为 解析JSON(建应["体"])
设 标识 为 元["id"]
打印("建状态=" + 转字符串(建应["状态"]))
# GET current（面板「新建后先看当前会话」的就地取数）
设 当应 为 服.处理当前会话("", "session=" + 标识)
设 当体 为 解析JSON(当应["体"])
打印("当状态=" + 转字符串(当应["状态"]))
打印("当cwd=" + 当体["工作目录"])
# GET /api/cwd/check（面板 chip 的只读校验）
设 查应 为 服.处理校验工作目录("工作目录=" + URL编码("{d}"))
设 查体 为 解析JSON(查应["体"])
打印("查状态=" + 转字符串(查应["状态"]))
打印("查可读=" + 转字符串(查体["可读"]))
打印("查绝对=" + 查体["绝对路径"])
# 首条消息：preset + 权限预设 + attachments 三者同时在场
设 附件表 为 []
设 附件项 为 ["name": "a.txt", "type": "text/plain", "dataUrl": "data:text/plain;base64,QQ=="]
附件表.追加(附件项)
''' + _chat_body('聊体', '标识', '你好', [
        ('preset', '"ptc"'), ('权限预设', '预设全放行'), ('attachments', '附件表'),
    ]) + f'''
设 聊应 为 服.处理对话(["方法": "POST", "路径": "/v1/chat/completions",
  "头": {{}}, "体": 编码(聊体)], "", "")
打印("聊状态=" + 转字符串(聊应["状态"]))
设 详应 为 服.处理会话详情(标识)
设 详体 为 解析JSON(详应["体"])
打印("详cwd=" + 详体["工作目录"])
打印("详模=" + 详体["模式"])
打印("详权=" + 详体["权限预设"])
打印("详模型=" + 详体["模型"])
打印("消息数=" + 转字符串(长度(详体["消息"])))
设 首条文本 为 序列化JSON(详体["消息"])
打印("含用户文本=" + 转字符串(首条文本.查找("你好") >= 0))
# 重启（新实例 + 新存储对象）后，四键仍能从磁盘读回
设 重启库 为 新建 会话存储(路径连接(根, "sessions"))
设 重启服 为 新建 Web服务端()
重启服.设置会话库(重启库)
重启服.根 为 根
设 重启当应 为 重启服.处理当前会话("", "session=" + 标识)
设 重启体 为 解析JSON(重启当应["体"])
打印("重启cwd=" + 重启体["工作目录"])
打印("重启模=" + 重启体["模式"])
打印("重启权=" + 重启体["权限预设"])
设 重启详应 为 重启服.处理会话详情(标识)
设 重启详 为 解析JSON(重启详应["体"])
打印("重启模型=" + 重启详["模型"])
'''
    rc, out, kv = _run(src, work)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['建状态'] == '200', f'新建会话失败\n{out}'
    assert _same(kv['当cwd'], str(target)), f'GET current 的 cwd 不对：{kv["当cwd"]}\n{out}'
    assert kv['查状态'] == '200' and kv['查可读'] == 'True', f'cwd/check 没接上\n{out}'
    assert _same(kv['查绝对'], str(target)), f'cwd/check 绝对路径回显不对\n{out}'
    assert kv['聊状态'] == '200', f'首条消息（preset+权限+附件）失败\n{out}'
    # 四键齐全：工作目录 / 模式 / 权限预设 / 模型
    assert _same(kv['详cwd'], str(target)), f'会话详情 cwd 不对\n{out}'
    assert kv['详模'] == 'ptc', f'首条消息的 preset 没写进会话\n{out}'
    assert kv['详权'] == '全放行', f'首条消息的权限预设没写进会话\n{out}'
    assert kv['详模型'] == 'mock', f'首条消息的模型没写进会话\n{out}'
    assert int(kv['消息数']) >= 2, f'首条消息没有落库（附件字段打断了？）\n{out}'
    assert kv['含用户文本'] == 'True', f'用户正文丢了（附件字段把 messages 顶掉？）\n{out}'
    # 重启恢复
    assert _same(kv['重启cwd'], str(target)), f'重启后 cwd 丢失\n{out}'
    assert kv['重启模'] == 'ptc' and kv['重启权'] == '全放行', f'重启后模式/权限丢失\n{out}'
    assert kv['重启模型'] == 'mock', f'重启后模型丢失\n{out}'


# --------------------------------------------------------------------------- #
# 2. 面板预选（目录+模式+权限）随创建落库（T-0396/T-0397 的交界）
# --------------------------------------------------------------------------- #
def test_面板预选目录模式权限在创建时落库(work):
    target = work / '预选目录'
    target.mkdir()
    d = _lp(target)

    src = BOOT + TEXT_MOCK + _service(work) + f'''
服.配置(新建 文本客户端(), 组装注册表(), 根, 30.0, "", 空)
''' + _create('建应', '预选', [
        ('工作目录', f'"{d}"'), ('模式', '"minimal"'), ('权限预设', '预设全拒绝'),
    ]) + f'''
设 元 为 解析JSON(建应["体"])
设 标识 为 元["id"]
打印("建状态=" + 转字符串(建应["状态"]))
设 当应 为 服.处理当前会话("", "session=" + 标识)
设 当体 为 解析JSON(当应["体"])
打印("当cwd=" + 当体["工作目录"])
打印("当模=" + 当体["模式"])
打印("当权=" + 当体["权限预设"])
设 详应 为 服.处理会话详情(标识)
设 详体 为 解析JSON(详应["体"])
打印("详cwd=" + 详体["工作目录"])
打印("详模=" + 详体["模式"])
打印("详权=" + 详体["权限预设"])
打印("生效权=" + 服.取会话权限预设(标识))
'''
    rc, out, kv = _run(src, work)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['建状态'] == '200', out
    assert _same(kv['当cwd'], str(target)), f'current 的 cwd 不对\n{out}'
    assert kv['当模'] == 'minimal' and kv['当权'] == '全拒绝', f'面板预选没在创建时落库\n{out}'
    assert _same(kv['详cwd'], str(target)), out
    assert kv['详模'] == 'minimal' and kv['详权'] == '全拒绝', out
    assert kv['生效权'] == '全拒绝', f'创建期预设没生效\n{out}'


# --------------------------------------------------------------------------- #
# 3. 两会话不同目录 + 不同权限并发：目录/权限互不串，工具判定各按各会话
# --------------------------------------------------------------------------- #
def test_两会话不同目录不同权限并发隔离(work):
    a = work / '甲项目'
    b = work / '乙项目'
    a.mkdir()
    b.mkdir()
    (a / 'own.txt').write_text('A', encoding='utf-8')
    (b / 'own.txt').write_text('B', encoding='utf-8')
    # 工具仍按进程根取根：把被读文件放在子进程 cwd（work）下
    (work / 'own.txt').write_text('OWN-CONTENT', encoding='utf-8')

    src = BOOT + TOOL_MOCK + _service(work) + f'''
服.配置(新建 工具客户端(), 组装注册表(), 根, 30.0, "", 空)
''' + _create('甲建', '甲', [('工作目录', f'"{_lp(a)}"'), ('权限预设', '预设全放行')]) \
        + _create('乙建', '乙', [('工作目录', f'"{_lp(b)}"'), ('权限预设', '预设全拒绝')]) + r'''
设 甲id 为 解析JSON(甲建["体"])["id"]
设 乙id 为 解析JSON(乙建["体"])["id"]
打印("甲建状态=" + 转字符串(甲建["状态"]))
打印("乙建状态=" + 转字符串(乙建["状态"]))

段落 跑聊天(服务对象, 标识, 文本):
  设 入参 为 ["model": "mock", "messages": [["role": "user", "content": 文本]], "session_id": 标识]
  设 体 为 序列化JSON(入参)
  设 应 为 服务对象.处理对话(["方法": "POST", "路径": "/v1/chat/completions",
    "头": {}, "体": 编码(体)], "", "")
  返回 转字符串(应["状态"])

# 真并发：两个会话各自一条消息，同一进程同一服务实例
设 甲线 为 新建 线程(跑聊天, 服, 甲id, "读甲的目录")
设 乙线 为 新建 线程(跑聊天, 服, 乙id, "读乙的目录")
甲线.开始()
乙线.开始()
甲线.等待()
乙线.等待()
打印("甲聊状态=" + 甲线.获取结果())
打印("乙聊状态=" + 乙线.获取结果())

设 甲会 为 服.取会话(甲id)
设 乙会 为 服.取会话(乙id)
打印("甲调数=" + 转字符串(长度(甲会.查询事件("tool/call", 0, 0))))
打印("甲果数=" + 转字符串(长度(甲会.查询事件("tool/result", 0, 0))))
打印("乙调数=" + 转字符串(长度(乙会.查询事件("tool/call", 0, 0))))
打印("乙果数=" + 转字符串(长度(乙会.查询事件("tool/result", 0, 0))))
设 甲果 为 序列化JSON(甲会.查询事件("tool/result", 0, 0))
打印("甲果体=" + 甲果)

设 甲详应 为 服.处理会话详情(甲id)
设 乙详应 为 服.处理会话详情(乙id)
设 甲详 为 解析JSON(甲详应["体"])
设 乙详 为 解析JSON(乙详应["体"])
打印("甲cwd=" + 甲详["工作目录"])
打印("乙cwd=" + 乙详["工作目录"])
打印("甲权=" + 甲详["权限预设"])
打印("乙权=" + 乙详["权限预设"])
# 路径安全：各按各会话根（自读放行、跨会话越界拒绝）
打印("甲自读=" + 转字符串(解析安全路径(甲详["工作目录"], "own.txt")["ok"]))
打印("乙自读=" + 转字符串(解析安全路径(乙详["工作目录"], "own.txt")["ok"]))
打印("甲越界=" + 转字符串(解析安全路径(甲详["工作目录"], "../乙项目/own.txt")["ok"]))
打印("乙越界=" + 转字符串(解析安全路径(乙详["工作目录"], "../甲项目/own.txt")["ok"]))
'''
    rc, out, kv = _run(src, work)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['甲建状态'] == '200' and kv['乙建状态'] == '200', out
    assert kv['甲聊状态'] == '200' and kv['乙聊状态'] == '200', f'并发对话失败\n{out}'
    # 全放行：工具真的执行了，结果里带进程根下的文件内容
    assert int(kv['甲调数']) >= 1 and int(kv['甲果数']) >= 1, f'全放行会话的工具没执行\n{out}'
    assert 'OWN-CONTENT' in kv['甲果体'], f'工具结果没带文件内容\n{out}'
    # 全拒绝：只有调用记录，没有结果记录（被会话闸门拒掉）
    assert int(kv['乙调数']) >= 1, f'全拒绝会话连调用记录都没有（闸门没接上？）\n{out}'
    assert int(kv['乙果数']) == 0, f'全拒绝会话的工具被执行了（会话级权限没生效）\n{out}'
    # 目录/权限互不串
    assert _same(kv['甲cwd'], str(a)) and _same(kv['乙cwd'], str(b)), f'两会话 cwd 串了\n{out}'
    assert kv['甲权'] == '全放行' and kv['乙权'] == '全拒绝', f'两会话权限串了\n{out}'
    assert kv['甲自读'] == 'True' and kv['乙自读'] == 'True', f'各自根下自读被拒\n{out}'
    assert kv['甲越界'] == 'False' and kv['乙越界'] == 'False', f'跨会话越界没被拒\n{out}'


# --------------------------------------------------------------------------- #
# 4. 压缩后会话仍能继续发消息（遮蔽旧事件后 续聊/落库/重读 都不炸）
# --------------------------------------------------------------------------- #
def test_压缩后会话仍可继续发消息(work):
    target = work / '压缩目录'
    target.mkdir()

    src = BOOT + TEXT_MOCK + _service(work) + f'''
服.配置(新建 文本客户端(), 组装注册表(), 根, 30.0, "", 空)
''' + _create('建应', '压缩', [('工作目录', f'"{_lp(target)}"')]) + r'''
设 标识 为 解析JSON(建应["体"])["id"]
设 转 为 0
当 转 < 3:
  设 入参 为 ["model": "mock", "messages": [["role": "user", "content": "第" + 转字符串(转) + "句"]], "session_id": 标识]
  设 体 为 序列化JSON(入参)
  设 应 为 服.处理对话(["方法": "POST", "路径": "/v1/chat/completions",
    "头": {}, "体": 编码(体)], "", "")
  打印("轮" + 转字符串(转) + "状态=" + 转字符串(应["状态"]))
  设 转 为 转 + 1
# 触发压缩（Web 层暂无触发端点：用 压缩.light 的公共入口在服务实例上触发）
设 会话 为 服.取会话(标识)
设 整理前 为 长度(会话.整理消息())
设 压缩后 为 压缩到最近(会话, 1)
打印("整理前数=" + 转字符串(整理前))
打印("整理后数=" + 转字符串(长度(压缩后)))
设 续入参 为 ["model": "mock", "messages": [["role": "user", "content": "压缩后继续"]], "session_id": 标识]
设 续体 为 序列化JSON(续入参)
设 续应 为 服.处理对话(["方法": "POST", "路径": "/v1/chat/completions",
  "头": {}, "体": 编码(续体)], "", "")
打印("续状态=" + 转字符串(续应["状态"]))
打印("续体=" + 截取(转字符串(续应["体"]), 0, 160))
设 详应 为 服.处理会话详情(标识)
设 详体 为 解析JSON(详应["体"])
打印("详状态=" + 转字符串(详应["状态"]))
打印("消息数=" + 转字符串(长度(详体["消息"])))
设 整理文本 为 序列化JSON(服.取会话(标识).整理消息())
打印("含摘要=" + 转字符串(整理文本.查找("压缩摘要") >= 0))
# 落盘后重读：压缩不能把 JSONL 写坏
设 重读库 为 新建 会话存储(路径连接(根, "sessions"))
设 重读 为 重读库.获取会话(标识)
打印("重读数=" + 转字符串(长度(重读)))
设 重读详应 为 服.处理会话详情(标识)
打印("重读详状态=" + 转字符串(重读详应["状态"]))
'''
    rc, out, kv = _run(src, work)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    for i in range(3):
        assert kv[f'轮{i}状态'] == '200', f'第 {i} 轮对话失败\n{out}'
    assert int(kv['整理前数']) > int(kv['整理后数']), f'压缩没生效（整理前后一样长）\n{out}'
    assert kv['续状态'] == '200', f'压缩后继续发消息失败\n{out}'
    assert 'ok' in kv['续体'], f'压缩后续轮没有拿到模型回复\n{out}'
    assert kv['详状态'] == '200' and kv['重读详状态'] == '200', f'压缩后详情读不出来\n{out}'
    assert kv['含摘要'] == 'True', f'压缩摘要没进模型可见消息\n{out}'
    assert int(kv['消息数']) >= 8, f'压缩后消息数不对（落库断档？）{kv["消息数"]}\n{out}'
    assert int(kv['重读数']) >= 8, f'压缩后 JSONL 重读缺行：{kv["重读数"]}\n{out}'


# --------------------------------------------------------------------------- #
# 5. 切回旧会话：模式/权限/目录按会话恢复，续聊不吃默认值
# --------------------------------------------------------------------------- #
def test_切回旧会话恢复模式权限目录(work):
    a = work / '旧会话目录'
    b = work / '新会话目录'
    a.mkdir()
    b.mkdir()

    src = BOOT + TEXT_MOCK + _service(work) + f'''
服.配置(新建 文本客户端(), 组装注册表(), 根, 30.0, "", 空)
''' + _create('甲建', '旧', [('工作目录', f'"{_lp(a)}"'), ('模式', '"minimal"'), ('权限预设', '预设全拒绝')]) \
        + _create('乙建', '新', [('工作目录', f'"{_lp(b)}"'), ('模式', '"cordis"'), ('权限预设', '预设全放行')]) + r'''
设 甲id 为 解析JSON(甲建["体"])["id"]
设 乙id 为 解析JSON(乙建["体"])["id"]
设 甲入参 为 ["model": "mock", "messages": [["role": "user", "content": "甲一"]], "session_id": 甲id]
设 甲体 为 序列化JSON(甲入参)
设 甲应 为 服.处理对话(["方法": "POST", "路径": "/v1/chat/completions", "头": {}, "体": 编码(甲体)], "", "")
设 乙入参 为 ["model": "mock", "messages": [["role": "user", "content": "乙一"]], "session_id": 乙id]
设 乙体 为 序列化JSON(乙入参)
设 乙应 为 服.处理对话(["方法": "POST", "路径": "/v1/chat/completions", "头": {}, "体": 编码(乙体)], "", "")
打印("甲聊=" + 转字符串(甲应["状态"]))
打印("乙聊=" + 转字符串(乙应["状态"]))
# 切回旧会话：current 就地还原（前端 applySessionMode 的数据源）
设 回当应 为 服.处理当前会话("", "session=" + 甲id)
设 回当体 为 解析JSON(回当应["体"])
打印("回cwd=" + 回当体["工作目录"])
打印("回模=" + 回当体["模式"])
打印("回权=" + 回当体["权限预设"])
# 续聊只带消息、不再带 preset/权限：旧会话必须保住自己的设置
设 甲续入参 为 ["model": "mock", "messages": [["role": "user", "content": "甲二"]], "session_id": 甲id]
设 甲续 为 序列化JSON(甲续入参)
设 甲续应 为 服.处理对话(["方法": "POST", "路径": "/v1/chat/completions", "头": {}, "体": 编码(甲续)], "", "")
打印("甲续=" + 转字符串(甲续应["状态"]))
设 甲详应 为 服.处理会话详情(甲id)
设 甲详 为 解析JSON(甲详应["体"])
打印("甲续模=" + 甲详["模式"])
打印("甲续权=" + 甲详["权限预设"])
打印("甲续cwd=" + 甲详["工作目录"])
# 乙会话不受影响
设 乙详应 为 服.处理会话详情(乙id)
设 乙详 为 解析JSON(乙详应["体"])
打印("乙模=" + 乙详["模式"])
打印("乙权=" + 乙详["权限预设"])
打印("乙cwd=" + 乙详["工作目录"])
打印("乙消息数=" + 转字符串(长度(乙详["消息"])))
'''
    rc, out, kv = _run(src, work)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['甲聊'] == '200' and kv['乙聊'] == '200', out
    assert _same(kv['回cwd'], str(a)), f'切回旧会话 cwd 没恢复\n{out}'
    assert kv['回模'] == 'minimal' and kv['回权'] == '全拒绝', f'切回旧会话 模式/权限 没恢复\n{out}'
    assert kv['甲续'] == '200', f'旧会话续聊失败\n{out}'
    assert kv['甲续模'] == 'minimal' and kv['甲续权'] == '全拒绝', f'续聊把旧会话设置抹了\n{out}'
    assert _same(kv['甲续cwd'], str(a)), f'续聊把旧会话 cwd 抹了\n{out}'
    assert kv['乙模'] == 'cordis' and kv['乙权'] == '全放行', f'乙会话被旧会话的切回污染\n{out}'
    assert _same(kv['乙cwd'], str(b)), f'乙会话 cwd 被改\n{out}'
    assert int(kv['乙消息数']) >= 2, f'乙会话消息被动了\n{out}'


# --------------------------------------------------------------------------- #
# 6. 文档/对标登记的自检（防止「只在 summary 里说登记了」而文件没动）
# --------------------------------------------------------------------------- #
def test_文档与对标登记到位():
    import json

    quick = open(os.path.join(ROOT, 'docs', '快速开始.md'), encoding='utf-8').read()
    api = open(os.path.join(ROOT, 'docs', 'API参考.md'), encoding='utf-8').read()
    change = open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8').read()

    # 快速开始：五件事 checklist（目录/模式/权限/附件/压缩）
    for word in ('新建会话', '/api/cwd/check', '模式', '权限', '附件', '压缩'):
        assert word in quick, f'docs/快速开始.md 缺「{word}」（冒烟 checklist 不完整）'
    assert '排查' in quick, 'docs/快速开始.md 的 checklist 必须给「失败时怎么排查」'

    # API 参考：三个接口/新键
    for word in ('POST /api/sessions', 'GET /api/cwd/check', 'GET /api/sessions/current',
                 '工作目录', '权限预设'):
        assert word in api, f'docs/API参考.md 缺「{word}」'

    # CHANGELOG 有一条本卡的记录
    assert 'T-0399' in change, 'CHANGELOG.md 没有 T-0399 条目'

    # 对标清单：只在末尾追加（编号升序、无重复、旧编号一个不删）
    path = os.path.join(ROOT, 'docs', '功能对标', '对标清单.json')
    data = json.load(open(path, encoding='utf-8'))
    entries = data['条目']
    nums = [e['编号'] for e in entries]
    assert nums == sorted(nums), '对标清单编号乱序（旧条目被重排）'
    assert len(nums) == len(set(nums)), '对标清单编号重复'
    assert nums[-5:] == [366, 367, 368, 369, 370], (
        f'本卡应在末尾追加 366~370，实际尾部：{nums[-5:]}'
    )
    assert 365 in nums, '旧末号 365 被删了（只增不改）'
    tail_text = json.dumps(entries[-5:], ensure_ascii=False)
    for num in ('T-0395', 'T-0396', 'T-0397', 'T-0398', 'T-0399'):
        assert num in tail_text, f'对标清单新增条目没登记 {num}'

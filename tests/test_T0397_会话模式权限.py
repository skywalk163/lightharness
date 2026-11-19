# -*- coding: utf-8 -*-
"""T-0397 会话级模式与权限（后端 + 前端静态契约）判据。

每个后端用例起一个独立 Light 子进程，走真实的 Web服务端 / 会话存储 / 权限管理器。
关键反证（旧实现必红）：
  - 旧实现会话不记录模式/权限 → 详情/current 没有两个键、重启丢失；
  - 旧实现 权限管理器 是全局单例，POST /api/permissions 改全场 → 两会话并发隔离必有一个方向错；
  - 旧实现 /api/permissions 改默认会连带改掉「已绑定会话」→ 改默认不影响会话必红；
  - 旧实现 检查() 只认全局预设，没有会话覆盖入参 → 会话级判定必红。
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 120


def _lp(p) -> str:
    return str(p).replace('\\', '/')


def _find_repo(env_name, dir_name):
    """沿祖先逐级探测兄弟仓（worktree 深度不固定），与 运行.py 口径一致。"""
    cands = []
    explicit = os.environ.get(env_name, '')
    if explicit:
        cands.append(explicit)
    cur = ROOT
    for _ in range(5):
        cands.append(os.path.join(cur, '..', dir_name))
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    cands += [
        os.path.join(ROOT, '..', 'duan-light-merge', dir_name),
        os.path.join('G:/dswork/duan-light-merge', dir_name),
        '/home/skywalk/dswork/' + dir_name,
    ]
    for c in cands:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _env():
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE')}
    for key, repo in (('LIGHTPLUGIN', 'lightplugin'), ('LIGHT_MERGE', 'light-merge')):
        found = _find_repo(key, repo)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _run(src, tmp_path):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(tmp_path), env=_env(),
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    combined = p.stdout + p.stderr
    return p.returncode, combined, kv


BOOT = r'''
从 web服务器 导入 Web服务端
从 会话存储 导入 会话存储
从 字符串处理 导入 编码
从 JSON 导入 解析JSON, 序列化JSON
从 文件系统 导入 路径连接
从 权限 导入 预设全放行, 预设全拒绝, 预设按类别
从 认证 导入 初始化认证
从 内置核心字典 导入 字典键列表
初始化认证()
'''


def _service(root):
    return f'''
设 根 为 "{_lp(root)}"
设 库 为 新建 会话存储(路径连接(根, "sessions"))
设 服 为 新建 Web服务端()
服.设置会话库(库)
服.根 为 根
'''


def _new(body_expr):
    """生成一条 POST /api/sessions 调用的 Light 表达式。body_expr 为 Light 序列化JSON(...) 表达式串。"""
    return (f'服.处理新建会话(["方法":"POST","路径":"/api/sessions","头":{{}},'
            f'"体":编码({body_expr})], "")')


def _body(title, mode=None, perm=None):
    parts = [f'"标题": "{title}"']
    if mode is not None:
        parts.append(f'"模式": {mode}')
    if perm is not None:
        parts.append(f'"权限预设": {perm}')
    return '序列化JSON([' + ','.join(parts) + '])'


# --------------------------------------------------------------------------- #
# 1. 建两会话分别指定「全放行 / 全拒绝」——同一工具分别得到 放行 / 拒绝，且全局不变
# --------------------------------------------------------------------------- #
def test_两会话并发权限隔离同一工具分别放行拒绝(tmp_path):
    src = (BOOT + _service(tmp_path)
           + f'''
设 甲应 为 {_new(_body('甲', '"standard"', '预设全放行'))}
设 乙应 为 {_new(_body('乙', '"minimal"', '预设全拒绝'))}
设 甲元 为 解析JSON(甲应["体"])
设 乙元 为 解析JSON(乙应["体"])
设 甲id 为 甲元["id"]
设 乙id 为 乙元["id"]
打印("甲写=" + 服.检查会话权限(甲id, "写文件", {{}}))
打印("甲读=" + 服.检查会话权限(甲id, "读文件", {{}}))
打印("乙读=" + 服.检查会话权限(乙id, "读文件", {{}}))
打印("乙写=" + 服.检查会话权限(乙id, "写文件", {{}}))
打印("全局=" + 服.权限管理器.当前预设())
打印("甲权=" + 服.取会话模式设置(甲id)["权限预设"])
打印("乙权=" + 服.取会话模式设置(乙id)["权限预设"])
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['甲写'] == '放行' and kv['甲读'] == '放行', f'甲会话（全放行）未按会话放行\n{out}'
    assert kv['乙读'] == '拒绝' and kv['乙写'] == '拒绝', f'乙会话（全拒绝）未按会话拒绝\n{out}'
    assert kv['全局'] == '按类别', f'全局预设被会话切换污染\n{out}'
    assert kv['甲权'] == '全放行' and kv['乙权'] == '全拒绝', f'会话权限预设没记下来\n{out}'


# --------------------------------------------------------------------------- #
# 2. 未设置时回退默认「标准 + 按类别」——默认行为零变化
# --------------------------------------------------------------------------- #
def test_未设置回退默认标准加按类别(tmp_path):
    src = (BOOT + _service(tmp_path)
           + f'''
设 应 为 {_new(_body('默认'))}
设 元 为 解析JSON(应["体"])
设 id 为 元["id"]
设 设置 为 服.取会话模式设置(id)
打印("模式=" + 转字符串(设置["模式"]))
打印("权限=" + 转字符串(设置["权限预设"]))
打印("写=" + 服.检查会话权限(id, "写文件", {{}}))
打印("读=" + 服.检查会话权限(id, "读文件", {{}}))
打印("生效权=" + 服.取会话权限预设(id))
设 详 为 服.处理会话详情(id)
设 详体 为 解析JSON(详["体"])
打印("详模=" + 转字符串(详体["模式"]))
打印("详权=" + 转字符串(详体["权限预设"]))
设 当 为 服.处理当前会话("", "session=" + id)
设 当体 为 解析JSON(当["体"])
打印("当模=" + 转字符串(当体["模式"]))
打印("当权=" + 转字符串(当体["权限预设"]))
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['模式'] == '' and kv['权限'] == '', f'无会话级设置时应为空串\n{out}'
    assert kv['写'] == '审批' and kv['读'] == '放行', f'默认不是「按类别」\n{out}'
    assert kv['生效权'] == '按类别', f'未设置时未回退按类别\n{out}'
    assert kv['详模'] == '' and kv['详权'] == '', f'详情缺模式/权限键\n{out}'
    assert kv['当模'] == '' and kv['当权'] == '', f'current 缺模式/权限键\n{out}'


# --------------------------------------------------------------------------- #
# 3. POST /api/permissions 改默认，不影响已绑定会话
# --------------------------------------------------------------------------- #
def test_改全局默认不影响已绑定会话(tmp_path):
    src = (BOOT + _service(tmp_path)
           + f'''
设 应 为 {_new(_body('绑定', perm='预设全放行'))}
设 元 为 解析JSON(应["体"])
设 id 为 元["id"]
打印("前写=" + 服.检查会话权限(id, "写文件", {{}}))
设 改 为 服.处理保存权限(["方法":"POST","路径":"/api/permissions","头":{{}},"体":编码(序列化JSON(["预设":预设全拒绝]))])
打印("全局=" + 服.权限管理器.当前预设())
打印("后写=" + 服.检查会话权限(id, "写文件", {{}}))
设 应2 为 {_new(_body('新'))}
设 id2 为 解析JSON(应2["体"])["id"]
打印("新写=" + 服.检查会话权限(id2, "写文件", {{}}))
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['前写'] == '放行' and kv['后写'] == '放行', f'改默认污染了已绑定会话\n{out}'
    assert kv['全局'] == '全拒绝', f'全局默认没改成\n{out}'
    assert kv['新写'] == '拒绝', f'新会话没有吃新默认\n{out}'


# --------------------------------------------------------------------------- #
# 4. 持久化/恢复：新 Web服务端实例（模拟重启）能从磁盘恢复会话模式/权限
# --------------------------------------------------------------------------- #
def test_切换会话持久化重启恢复(tmp_path):
    src = (BOOT + _service(tmp_path)
           + f'''
设 应 为 {_new(_body('持久', '"cordis"', '预设全拒绝'))}
设 id 为 解析JSON(应["体"])["id"]
设 库2 为 新建 会话存储(路径连接(根, "sessions"))
设 服2 为 新建 Web服务端()
服2.设置会话库(库2)
服2.根 为 根
设 设置 为 服2.取会话模式设置(id)
打印("重启模=" + 设置["模式"])
打印("重启权=" + 设置["权限预设"])
打印("重启读=" + 服2.检查会话权限(id, "读文件", {{}}))
设 详 为 服2.处理会话详情(id)
设 详体 为 解析JSON(详["体"])
打印("详模=" + 详体["模式"])
打印("详权=" + 详体["权限预设"])
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['重启模'] == 'cordis' and kv['重启权'] == '全拒绝', f'重启后会话模式/权限丢失\n{out}'
    assert kv['重启读'] == '拒绝', f'重启后会话权限判定错误\n{out}'
    assert kv['详模'] == 'cordis' and kv['详权'] == '全拒绝', f'重启后详情未返回模式/权限\n{out}'


# --------------------------------------------------------------------------- #
# 5. 会话内切换 POST /api/sessions/:id/模式权限 只改该会话，不动另一会话/全局
# --------------------------------------------------------------------------- #
def test_会话内切换只改本会话(tmp_path):
    src = (BOOT + _service(tmp_path)
           + f'''
设 甲应 为 {_new(_body('甲', perm='预设按类别'))}
设 乙应 为 {_new(_body('乙', perm='预设按类别'))}
设 甲id 为 解析JSON(甲应["体"])["id"]
设 乙id 为 解析JSON(乙应["体"])["id"]
设 改 为 服.处理设置会话模式权限(甲id, ["方法":"POST","路径":"/api/sessions/x/模式权限","头":{{}},"体":编码(序列化JSON(["模式":"ptc","权限预设":预设全放行]))])
打印("改状态=" + 转字符串(改["状态"]))
打印("甲写=" + 服.检查会话权限(甲id, "写文件", {{}}))
打印("乙写=" + 服.检查会话权限(乙id, "写文件", {{}}))
打印("全局=" + 服.权限管理器.当前预设())
打印("甲模=" + 服.取会话模式设置(甲id)["模式"])
设 坏 为 服.处理设置会话模式权限(甲id, ["方法":"POST","路径":"/api/sessions/x/模式权限","头":{{}},"体":编码(序列化JSON(["权限预设":"瞎写"]))])
打印("坏状态=" + 转字符串(坏["状态"]))
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['改状态'] == '200', f'会话内切换端点失败\n{out}'
    assert kv['甲写'] == '放行' and kv['乙写'] == '审批', f'会话内切换污染了另一会话\n{out}'
    assert kv['全局'] == '按类别', f'会话内切换改了全局管理器\n{out}'
    assert kv['甲模'] == 'ptc', f'模式没写进会话\n{out}'
    assert kv['坏状态'] == '400', f'非法预设没被拒绝\n{out}'


# --------------------------------------------------------------------------- #
# 6. 每轮对话把实际生效的 preset / 权限预设写回会话（含首条消息带 preset/权限预设）
# --------------------------------------------------------------------------- #
def test_对话每轮写回预设(tmp_path):
    mock = r'''
从 总入口 导入 组装注册表
从 流 导入 造块开始, 造文本增量, 造块结束, 造结束, 造停止原因

类 模拟客户端:
  属性 模型名 等于 "mock"
  段落 构造:
    设 己.模型名 为 "mock"
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    设 文本 为 "ok"
    返回 [造块开始(0, "text"), 造文本增量(0, 文本), 造块结束(0, ["type":"text","text":文本]), 造结束(造停止原因())]
'''
    src = (BOOT + mock + _service(tmp_path)
           + r'''
服.配置(新建 模拟客户端(), 组装注册表(), 根, 30.0, "", 空)
设 聊天体 为 序列化JSON(["model":"mock","messages":[["role":"user","content":"你好"]],"preset":"ptc","权限预设":预设全放行])
设 应 为 服.处理对话(["方法":"POST","路径":"/v1/chat/completions","头":{},"体":编码(聊天体)], "", "")
打印("状态=" + 转字符串(应["状态"]))
设 id 为 ""
遍历 键 之 字典键列表(服.会话表):
  设 id 为 键
设 设置 为 服.取会话模式设置(id)
打印("模=" + 设置["模式"])
打印("权=" + 设置["权限预设"])
设 会 为 服.会话表[id]
打印("头模=" + 转字符串(会.头信息.获取("模式", "空")))
打印("头权=" + 转字符串(会.头信息.获取("权限预设", "空")))
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['状态'] == '200', f'对话失败\n{out}'
    assert kv['模'] == 'ptc' and kv['权'] == '全放行', f'本轮未把预设写回会话\n{out}'
    assert kv['头模'] == 'ptc' and kv['头权'] == '全放行', f'会话头信息没记录模式/权限\n{out}'


# --------------------------------------------------------------------------- #
# 7. 前端静态契约（node --check 由 verify 保证；这里断言关键接线存在于源码）
# --------------------------------------------------------------------------- #
def test_前端会话切换恢复与按会话落库接线():
    app = os.path.join(ROOT, 'webui', 'app.js')
    with open(app, encoding='utf-8') as fh:
        s = fh.read()
    assert 'body.权限预设' in s, '请求体未携带权限预设（服务端无法按会话写回）'
    assert '/模式权限' in s, '会话内切换未走会话级端点'
    assert 'applySessionMode(data["模式"], data["权限预设"])' in s, '切换会话未恢复下拉'
    save_perm = s[s.index('function savePermission'):s.index('function savePermission') + 600]
    assert 'persistSessionMode' in save_perm, '权限切换没有落到会话级'
    assert 'fetch("/api/permissions"' not in save_perm, '权限切换仍在改全局 /api/permissions'
    assert re.search(r'modeSelectEl\.addEventListener\("change".*?persistSessionMode', s, re.S), \
        '模式切换未落到会话级'


# --------------------------------------------------------------------------- #
# 8. 续轮 / 单项更新不互相抹除（主控合入补丁：空串 ≠ 「本轮没带」）
# --------------------------------------------------------------------------- #
def test_续轮与单项更新不互相抹除(tmp_path):
    mock = r'''
从 总入口 导入 组装注册表
从 流 导入 造块开始, 造文本增量, 造块结束, 造结束, 造停止原因

类 模拟客户端:
  属性 模型名 等于 "mock"
  段落 构造:
    设 己.模型名 为 "mock"
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    设 文本 为 "ok"
    返回 [造块开始(0, "text"), 造文本增量(0, 文本), 造块结束(0, ["type":"text","text":文本]), 造结束(造停止原因())]
'''
    src = (BOOT + mock + _service(tmp_path)
           + r'''
服.配置(新建 模拟客户端(), 组装注册表(), 根, 30.0, "", 空)
设 体1 为 序列化JSON(["model":"mock","messages":[["role":"user","content":"一"]],"preset":"ptc","权限预设":预设全拒绝])
设 应1 为 服.处理对话(["方法":"POST","路径":"/v1/chat/completions","头":{},"体":编码(体1)], "", "")
设 id 为 ""
遍历 键 之 字典键列表(服.会话表):
  设 id 为 键
# 续轮只带 preset，不带 权限预设：权限必须保留 全拒绝
设 体2 为 序列化JSON(["model":"mock","session_id":id,"messages":[["role":"user","content":"二"]],"preset":"cordis"])
设 应2 为 服.处理对话(["方法":"POST","路径":"/v1/chat/completions","头":{},"体":编码(体2)], "", "")
设 置2 为 服.取会话模式设置(id)
打印("续轮模=" + 转字符串(置2["模式"]))
打印("续轮权=" + 转字符串(置2["权限预设"]))
打印("续轮判=" + 服.检查会话权限(id, "写文件", {}))
# 会话内只改权限：模式不能被抹成默认
设 改1 为 服.处理设置会话模式权限(id, ["方法":"POST","路径":"/api/sessions/x/模式权限","头":{},"体":编码(序列化JSON(["权限预设":预设全放行]))])
设 置3 为 服.取会话模式设置(id)
打印("改权后模=" + 转字符串(置3["模式"]))
打印("改权后权=" + 转字符串(置3["权限预设"]))
# 会话内只改模式：权限不能被抹成默认
设 改2 为 服.处理设置会话模式权限(id, ["方法":"POST","路径":"/api/sessions/x/模式权限","头":{},"体":编码(序列化JSON(["模式":"minimal"]))])
设 置4 为 服.取会话模式设置(id)
打印("改模后模=" + 转字符串(置4["模式"]))
打印("改模后权=" + 转字符串(置4["权限预设"]))
# 显式空串 = 回到全局默认
设 改3 为 服.处理设置会话模式权限(id, ["方法":"POST","路径":"/api/sessions/x/模式权限","头":{},"体":编码(序列化JSON(["权限预设":""]))])
设 置5 为 服.取会话模式设置(id)
打印("复位后权=" + 转字符串(置5["权限预设"]))
打印("复位后生效权=" + 服.取会话权限预设(id))
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['续轮模'] == 'cordis', f'续轮没更新模式\n{out}'
    assert kv['续轮权'] == '全拒绝', f'续轮把权限抹掉了（空串被当成显式重置）\n{out}'
    assert kv['续轮判'] == '拒绝', f'续轮后会话权限判定不对\n{out}'
    assert kv['改权后模'] == 'cordis', f'只改权限把模式抹掉了\n{out}'
    assert kv['改权后权'] == '全放行', out
    assert kv['改模后模'] == 'minimal', out
    assert kv['改模后权'] == '全放行', f'只改模式把权限抹掉了\n{out}'
    assert kv['复位后权'] == '', f'显式空串没有回到全局默认\n{out}'
    assert kv['复位后生效权'] == '按类别', f'复位后生效权限不对\n{out}'

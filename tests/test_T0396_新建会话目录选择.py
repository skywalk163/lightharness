# -*- coding: utf-8 -*-
"""T-0396 新会话面板：目录选择器 + 模式/权限预选（只读校验端点 + 前端接线）。

本卡的前端部分（chip / 弹层 / 下拉）靠浏览器手工冒烟（见 .hive/summary.md），
pytest 这里判的是**后端契约**与**前端接线**能否被机器验证：

  1. GET /api/cwd/check 的存在/不存在/是文件/相对路径四态；
  2. 无副作用：校验前后 settings.json 与进程 cwd 都不变（卡面红线）；
  3. 鉴权口径与其它 GET 一致（不被 POST 白名单误放行，也不额外要求令牌）；
  4. 相对路径按**服务进程 cwd** 解析后回显绝对路径；
  5. 前端接线：new-session.js 仍被 index.html 引入、服务端静态路由能发它、
     两个 node --check 的靶子文件确实存在且不含 `#cwd-popover` 之外的重名 id。

反证（旧实现下必须红）：
  - 第 1 组：旧路由表里没有 /api/cwd/check → 落到兜底 404，`状态` 不是 200；
  - 第 3 组：把该端点接到 POST /api/cwd 上（复用而非新建）会让 cwd 变化 → 第 2 组红。
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180


def _lp(p) -> str:
    """把宿主路径写成 .light 字符串字面量：用正斜杠，避免反斜杠被当转义。"""
    return str(p).replace('\\', '/')


def _find_sibling(name):
    """运行时依赖的兄弟仓定位（与 运行.py 的探测口径一致，但不依赖宿主环境）。

    worker 的 worktree 常常没有 ../lightplugin，Web服务端 间接依赖它的 生产挂载，
    不显式给路径时会集体假红（T-0395 已踩过这个坑）。
    """
    key = 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'
    candidates = [
        os.environ.get(name, ''),
        os.path.join(ROOT, '..', key),
        os.path.join(ROOT, '..', '..', key),
        os.path.join(ROOT, '..', '..', 'duan-light-merge', key),
        '/home/skywalk/dswork/' + key,
    ]
    for c in candidates:
        if c and os.path.isdir(c):
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


def _norm(s: str) -> str:
    return os.path.normcase(os.path.normpath(str(s).strip()))


def _same(a: str, b: str) -> bool:
    return _norm(a) == _norm(b)


BOOT = '''
从 web服务器 导入 Web服务端, 全局服务, 路由处理器
从 认证 导入 初始化认证
从 文件系统 导入 创建目录, 写入文件, 路径连接, 读取文件
从 编码解码 导入 URL编码
从 JSON 导入 解析JSON, 序列化JSON
'''

# 统一的请求构造：路由处理器吃 {方法,路径,头,体}；路由处理器是异步段落 → 助手也必须异步
REQ = '''
异步 段落 查(路径):
  返回 等待 路由处理器(["方法": "GET", "路径": 路径, "头": {}, "体": b""])
'''


def _service(root):
    return f'''
初始化认证()
设 根 为 "{_lp(root)}"
全局服务.配置(空, 空, 根, 30.0, "")
'''


def _main(body):
    """把驱动主体包进异步主函数：`等待` 只能写在异步段落里，顶层不行。"""
    return '异步 段落 主():\n' + ''.join(
        ('  ' + line if line.strip() else line) + '\n' for line in body.strip('\n').split('\n')
    ) + '\n异步 运行 主()\n'


# --------------------------------------------------------------------------- #
# 1. check 端点四态：存在目录 / 不存在 / 是文件 / 相对路径
# --------------------------------------------------------------------------- #
def test_check端点四态(tmp_path):
    good = tmp_path / '好目录'
    good.mkdir()
    missing = tmp_path / '不存在'
    afile = tmp_path / '是文件.txt'
    afile.write_text('x', encoding='utf-8')

    src = BOOT + REQ + _service(tmp_path) + _main(f'''
# 先把响应落到变量再下标：`等待 (查(...))["体"]` 在光明里绑定优先级不对，会拿到 coroutine
设 好应 为 等待 查("/api/cwd/check?工作目录=" + URL编码("{_lp(good)}"))
设 好 为 解析JSON(好应["体"])
打印("好状态=" + 转字符串(好应["状态"]))
打印("好在=" + 转字符串(好["存在"]))
打印("好是目录=" + 转字符串(好["是目录"]))
打印("好可读=" + 转字符串(好["可读"]))
打印("好绝对=" + 好["绝对路径"])
打印("好错误=" + 好["错误"])

设 缺应 为 等待 查("/api/cwd/check?工作目录=" + URL编码("{_lp(missing)}"))
设 缺 为 解析JSON(缺应["体"])
打印("缺状态=" + 转字符串(缺应["状态"]))
打印("缺在=" + 转字符串(缺["存在"]))
打印("缺可读=" + 转字符串(缺["可读"]))
打印("缺错误=" + 缺["错误"])

设 文应 为 等待 查("/api/cwd/check?工作目录=" + URL编码("{_lp(afile)}"))
设 文 为 解析JSON(文应["体"])
打印("文状态=" + 转字符串(文应["状态"]))
打印("文在=" + 转字符串(文["存在"]))
打印("文是目录=" + 转字符串(文["是目录"]))
打印("文可读=" + 转字符串(文["可读"]))
打印("文错误=" + 文["错误"])

# 相对路径：按服务进程 cwd 解析后回显绝对路径
设 相应 为 等待 查("/api/cwd/check?工作目录=" + URL编码("好目录"))
设 相 为 解析JSON(相应["体"])
打印("相状态=" + 转字符串(相应["状态"]))
打印("相绝对=" + 相["绝对路径"])
打印("相可读=" + 转字符串(相["可读"]))
打印("进程cwd=" + 当前目录())
全局服务.停止()
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'

    # 存在且可读的目录
    assert kv['好状态'] == '200', f'/api/cwd/check 不存在（旧实现下是 404）\n{out}'
    assert kv['好在'] == 'True' and kv['好是目录'] == 'True' and kv['好可读'] == 'True', out
    assert _same(kv['好绝对'], str(good)), f'绝对路径回显不对：{kv["好绝对"]}'
    assert kv['好错误'] == '', f'成功的校验不该带错误：{kv["好错误"]!r}'

    # 不存在
    assert kv['缺状态'] == '200', '校验失败也应是 200 + {错误}（不是 4xx 空体）'
    assert kv['缺在'] == 'False' and kv['缺可读'] == 'False', out
    assert kv['缺错误'].strip(), '不存在必须给理由'

    # 是文件（存在但不是目录）
    assert kv['文状态'] == '200', out
    assert kv['文在'] == 'True', '普通文件应报「存在」'
    assert kv['文是目录'] == 'False' and kv['文可读'] == 'False', out
    assert '目录' in kv['文错误'], f'是文件必须说清「不是目录」：{kv["文错误"]}'

    # 相对路径 → 按进程 cwd 解析后回显绝对路径
    assert kv['相状态'] == '200', out
    assert _same(kv['相绝对'], str(good)), (
        f'相对路径没按进程 cwd 解析：{kv["相绝对"]}（进程 cwd={kv.get("进程cwd")}）\n{out}'
    )


# --------------------------------------------------------------------------- #
# 2. 无副作用：校验前后 settings.json 与进程 cwd 都不变（卡面红线）
# --------------------------------------------------------------------------- #
def test_check端点无副作用(tmp_path):
    target = tmp_path / '另一个目录'
    target.mkdir()
    settings = tmp_path / 'settings.json'
    # 预置一份 settings.json：校验绝不能改它一个字节
    settings.write_text(json.dumps({"工作目录": str(target), "无关": "保留我"},
                                   ensure_ascii=False), encoding='utf-8')
    before_bytes = settings.read_bytes()

    src = BOOT + REQ + _service(tmp_path) + _main(f'''
设 起cwd 为 当前目录()
设 起文 为 读取文件("{_lp(settings)}")
# 服务端内存态也一并取样：配置() 从 settings.json 载入是启动行为，不算副作用
设 起生效 为 全局服务.生效工作目录
# 故意连打多次：如果端点内部偷偷 chdir/落盘，这里就会露馅
设 甲 为 等待 查("/api/cwd/check?工作目录=" + URL编码("{_lp(target)}"))
设 乙 为 等待 查("/api/cwd/check?工作目录=" + URL编码("{_lp(target)}"))
设 丙 为 等待 查("/api/cwd/check?工作目录=" + URL编码("."))
设 丁 为 等待 查("/api/cwd/check?工作目录=" + URL编码("../"))
设 止cwd 为 当前目录()
设 止文 为 读取文件("{_lp(settings)}")
打印("cwd没变=" + 转字符串(起cwd == 止cwd))
打印("起cwd=" + 起cwd)
打印("止cwd=" + 止cwd)
打印("文件没变=" + 转字符串(起文 == 止文))
打印("生效没变=" + 转字符串(起生效 == 全局服务.生效工作目录))
打印("起生效=" + 起生效)
打印("生效工作目录=" + 全局服务.生效工作目录)
全局服务.停止()
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'

    assert kv['cwd没变'] == 'True', (
        f'GET /api/cwd/check 改了进程 cwd（红线：绝不 chdir）\n'
        f'起={kv.get("起cwd")} 止={kv.get("止cwd")}\n{out}'
    )
    assert kv['文件没变'] == 'True', f'GET /api/cwd/check 写了 settings.json（红线）\n{out}'
    assert settings.read_bytes() == before_bytes, 'settings.json 字节变了'
    # 服务端内存态也不该被校验“顺手”改写（只和「校验前」比，不与空串比——
    #   配置() 从 settings.json 载入 生效工作目录 是启动行为，不是本次校验的副作用）
    assert kv['生效没变'] == 'True', (
        f'校验改了服务端内存里的生效工作目录：起={kv.get("起生效")!r} 止={kv.get("生效工作目录")!r}\n{out}'
    )


# --------------------------------------------------------------------------- #
# 3. 鉴权口径与其它 GET 一致：启用认证后，GET 仍按既有白名单放行；
#    且该端点不能“顺手”写盘（即不能被错接到 POST /api/cwd 的实现上）
# --------------------------------------------------------------------------- #
def test_check端点与GET同口径且不复用POST(tmp_path):
    target = tmp_path / '鉴权目录'
    target.mkdir()

    src = BOOT + REQ + _service(tmp_path) + _main(f'''
# 认证已由 初始化认证() 启用（随机令牌）。GET 走既有白名单 → 不该 401。
设 应 为 等待 查("/api/cwd/check?工作目录=" + URL编码("{_lp(target)}"))
打印("带认证状态=" + 转字符串(应["状态"]))
设 体 为 解析JSON(应["体"])
打印("带认证可读=" + 转字符串(体["可读"]))
# 同一路径再打一次 POST /api/cwd（那条才是会 chdir+落盘的）
设 后 为 等待 查("/api/cwd/check?工作目录=" + URL编码("{_lp(target)}"))
设 后体 为 解析JSON(后["体"])
打印("后存量=" + 转字符串(后体["存在"]))
全局服务.停止()
''')
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['带认证状态'] == '200', (
        f'GET /api/cwd/check 在启用认证后被拦了（应与其它 GET 同口径）\n{out}'
    )
    assert kv['带认证可读'] == 'True', out
    assert kv['后存量'] == 'True', out
    # 只要走了 POST /api/cwd 那条实现，settings.json 必然出现（这里必须没有）
    assert not (tmp_path / 'settings.json').exists(), (
        '校验端点写下了 settings.json —— 说明它复用了 POST /api/cwd（红线）'
    )


# --------------------------------------------------------------------------- #
# 4. 前端接线：文件在、被 index.html 引入、服务端静态路由能发出去
# --------------------------------------------------------------------------- #
def test_前端接线齐全(tmp_path):
    webui = os.path.join(ROOT, 'webui')
    ns_js = os.path.join(webui, 'new-session.js')
    app_js = os.path.join(webui, 'app.js')
    index_path = os.path.join(webui, 'index.html')
    style_path = os.path.join(webui, 'style.css')

    assert os.path.isfile(ns_js), 'webui/new-session.js 不存在'
    assert os.path.isfile(app_js), 'webui/app.js 不存在'
    ns_src = open(ns_js, encoding='utf-8').read()
    app_src = open(app_js, encoding='utf-8').read()
    index_src = open(index_path, encoding='utf-8').read()
    style_src = open(style_path, encoding='utf-8').read()

    # 被 index.html 引入（且在 app.js 之前，app 初始化时要能拿到 window.NewSession）
    assert 'src="new-session.js"' in index_src, 'index.html 没引入 new-session.js'
    assert index_src.index('new-session.js') < index_src.index('src="app.js"'), (
        'new-session.js 必须在 app.js 之前加载'
    )

    # 既有 id 一个没动（测试与 app.js 都靠它们）
    for keep in ('new-session-btn', 'model-chip', 'mode-select', 'perm-preset',
                 'messages', 'input', 'send-btn', 'settings-btn'):
        assert ('id="%s"' % keep) in index_src, f'index.html 既有 id 被动了：{keep}'

    # 卡面点名的 DOM 锚点
    for need in ('cwd-chip', 'cwd-chip-name', 'cwd-popover'):
        assert ('id="%s"' % need) in index_src, f'index.html 缺 {need}'

    # 端点/存储键/接口名都在
    assert '/api/cwd/check' in ns_src, 'new-session.js 没接只读校验端点'
    assert 'lh.recentCwd' in ns_src, '最近目录必须用 localStorage 键 lh.recentCwd'
    assert 'window.NewSession' in ns_src, 'new-session.js 必须暴露 window.NewSession'
    assert 'NewSession.init' in app_src or 'NewSession.init(' in app_src, 'app.js 没初始化 NewSession'
    assert 'NewSession.getSessionCwd' in app_src, 'app.js 发送时没取会话目录'
    assert 'NewSession.markSessionCwdError' in app_src, 'app.js 没把服务端 400 标到 chip 上'

    # 「设为全局默认」必须走既有 POST /api/cwd（不是新端点），且明确提示全局生效
    assert '设为全局默认' in ns_src and '/api/cwd"' in ns_src, (
        '「设为全局默认」应调既有 POST /api/cwd'
    )
    assert '全局' in ns_src, '「设为全局默认」必须明确提示这是全局生效'

    # 模式/权限下拉四项都在（UI 暂存；权限不假装已生效 → 要有「全局默认」态）
    for mode in ('standard', 'cordis', 'ptc', 'minimal'):
        assert mode in ns_src, f'模式下拉缺 {mode}'
    for perm in ('全放行', '按类别', '全拒绝', '自定义'):
        assert perm in ns_src, f'权限下拉缺 {perm}'
    assert '全局默认' in ns_src, '权限下拉必须有「全局默认 / 未落库」态'

    # 样式：chip 与弹层都要有规则（跟既有 token 走）
    assert '.cwd-chip' in style_src, 'style.css 缺 .cwd-chip 规则'
    assert '.cwd-popover' in style_src, 'style.css 缺 .cwd-popover 规则'
    assert '.cwd-chip.is-error' in style_src, 'style.css 缺 chip 标红态规则'

    # 服务端要能把 new-session.js 当静态资源发出去（否则浏览器 404，面板整体失效）
    server_src = open(os.path.join(ROOT, 'src', 'web服务器.light'), encoding='utf-8').read()
    assert '"/new-session.js"' in server_src, 'web服务器.light 静态路由没登记 /new-session.js'
    assert '处理校验工作目录' in server_src, 'web服务器.light 没有 check 端点实现'
    assert '"/api/cwd/check"' in server_src, 'web服务器.light 路由表没登记 /api/cwd/check'


# --------------------------------------------------------------------------- #
# 5. 两个 node --check 靶子可解析（verify 跑的是同一条命令，这里给 pytest 侧兜底）
# --------------------------------------------------------------------------- #
def test_前端两个js可被node解析(tmp_path):
    for name in ('app.js', 'new-session.js'):
        path = os.path.join(ROOT, 'webui', name)
        p = subprocess.run(['node', '--check', path], capture_output=True, text=True,
                           encoding='utf-8', errors='replace', timeout=60)
        assert p.returncode == 0, f'node --check webui/{name} 失败：\n{p.stdout}\n{p.stderr}'

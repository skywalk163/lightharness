# -*- coding: utf-8 -*-
"""T-0470：lightharness 工具根 / worktree 支持（cd 守卫与读写路径解耦）。

背景（实测，来自 T-0461 交接文档）
-----------------------------------
1. bash 的 cd 守卫是**字面量正则**（旧 src/工具_bash.light:77），只匹配
   `cd /abs`、`cd ..`；`W=/home/...; cd $W` 这类间接写法原样绕过——
   护栏被「合法绕过」，代理还把 `$W` 绕法写进了交接文档。
2. read/write/search 的根是 `取根目录()`（HARNESS_ROOT > 会话cwd > 当前目录），
   Web 层虽然把「会话 cwd」存进了会话头信息，却没有任何工具读它：
   代理在 worktree 里干活时，四个工具仍停在项目根，只能用 bash heredoc 绕写。

本文件锁住三条不变量
--------------------
A. 会话 cwd 一旦设为本线程工具根，bash/读/写/搜索 **四个工具统一**使用它
   （worktree 作为合法根被接受，且读写不越界）。
B. cd 守卫改为「解析后路径判定」：`$VAR` / `${VAR}` / 引号 / `~` 先展开再判定；
   合法 worktree 放行，`cd /tmp`、`cd ..`、未定义变量展开为空一律拒绝；
   **单引号内与 `$()` 这类静态不可判定形式不得被静默放行**。
C. 无 worktree 时行为与旧版一致：根仍是项目根，普通 `cd ..` 仍拒。

平台说明：驱动一律 `sys.executable` 起子进程，不写死 python/python3；
POSIX 判据（`cd`/`pwd`）在 Linux/FreeBSD 原样可用，Windows 上由 bash 工具
自身的 shell 决定（本仓 CI 以 POSIX 为主）。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240


def _lp(p) -> str:
    """宿主路径 → .light 字符串字面量（正斜杠，避免反斜杠被当转义）。"""
    return str(p).replace('\\', '/')


def _find_sibling(name):
    """运行时依赖的兄弟仓定位（与 运行.py 的探测口径一致）。"""
    candidates = [
        os.environ.get(name, ''),
        os.path.join(ROOT, '..', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
        os.path.join(ROOT, '..', '..', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
        os.path.join('/home/skywalk/dswork', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _run(tmp_path, name, src, cwd=None, tool_roots=None):
    """写驱动 → 子进程跑 运行.py → 返回 (rc, 合并输出, 键值表)。

    清掉 HARNESS_ROOT / HARNESS_CWD：它们会打穿「根从哪来」的判据。
    HARNESS_TOOL_ROOTS 用于把临时 worktree 加进白名单（模拟 ~/.hive/wt 前缀）。
    """
    f = tmp_path / name
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_TOOL_ROOTS')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
    env['PYTHONIOENCODING'] = 'utf-8'
    if tool_roots:
        env['HARNESS_TOOL_ROOTS'] = os.pathsep.join(_lp(p) for p in tool_roots)
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(cwd or ROOT), env=env,
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return p.returncode, p.stdout + p.stderr, kv


def _ok(proc, what):
    assert proc[0] == 0, f'{what} 驱动应 rc=0，实际 {proc[0]}\n{proc[1][-3000:]}'


def _same(a: str, b: str) -> bool:
    norm = lambda s: os.path.normcase(os.path.normpath(s.strip()))
    return norm(a) == norm(b)


def _bool(kv, key):
    raw = kv.get(key, '')
    assert raw in ('True', 'False'), f'{key} 不是布尔打印：{raw!r}'
    return raw == 'True'


def _make_worktree(tmp_path):
    """造一个「像 ~/.hive/wt 下 worktree」的目录：<tmp>/wt/T-0461。"""
    wt = tmp_path / 'wt' / 'T-0461'
    (wt / 'sub').mkdir(parents=True)
    (wt / 'seed.txt').write_text('seed\n', encoding='utf-8')
    return wt


# --------------------------------------------------------------------------- #
# A. 会话 cwd = 工具根：bash / 读 / 写 / 搜索 四工具统一
# --------------------------------------------------------------------------- #
def test_会话cwd成为四工具根(tmp_path):
    wt = _make_worktree(tmp_path)

    src = f'''
从 工具_路径安全 导入 取根目录, 设置工具根
从 工具_读文件 导入 读文件处理
从 工具_写文件 导入 写文件处理
从 工具_搜索文件 导入 搜索文件处理
从 工具_bash 导入 bash处理

设 工作树 为 "{_lp(wt)}"
打印("设根=" + 转字符串(设置工具根(工作树, 真)))
打印("根=" + 取根目录())
设 写 为 写文件处理(["路径": "新建.txt", "内容": "worktree 内容"])
打印("写路径=" + 写["路径"])
设 读 为 读文件处理(["路径": "新建.txt"])
打印("读内容=" + 读["内容"])
设 搜 为 搜索文件处理(["模式": "内容", "查询": "worktree 内容", "路径": "."])
打印("命中数=" + 转字符串(长(搜["结果"])))
设 命 为 bash处理(["命令": "pwd"])
打印("bash=" + 命["输出"].去除空白())
设 越界 为 读文件处理(["路径": "../../etc/passwd"])
'''
    # 越界用法会抛出（路径安全校验失败），单独捕获
    src = src.replace('设 越界 为 读文件处理(["路径": "../../etc/passwd"])\n',
                      '''尝试:
  设 越界 为 读文件处理(["路径": "../../etc/passwd"])
  打印("越界=放行")
捕获 错误 异常内容:
  打印("越界=拒绝")
''')
    proc = _run(tmp_path, '_a.light', src, tool_roots=[tmp_path])
    _ok(proc, '四工具根')
    rc, out, kv = proc

    assert _bool(kv, '设根') is True, f'worktree 应被接受为工具根\n{out}'
    assert _same(kv['根'], str(wt)), f'取根目录没走会话 cwd：{kv["根"]}'
    assert _same(kv['写路径'], str(wt / '新建.txt')), f'写文件没落在 worktree：{kv["写路径"]}'
    assert (wt / '新建.txt').read_text(encoding='utf-8') == 'worktree 内容'
    assert kv['读内容'] == 'worktree 内容', f'读文件没读到 worktree：{kv["读内容"]!r}'
    assert kv['命中数'] == '1', f'搜索没在 worktree 命中：{kv["命中数"]}'
    assert _same(kv['bash'], str(wt)), f'bash 工作目录没跟会话 cwd：{kv["bash"]}'
    assert kv['越界'] == '拒绝', '读文件越出工具根必须拒绝'


# --------------------------------------------------------------------------- #
# B. cd 守卫：解析后判定（变量 / 引号 / 白名单），越界仍拒
# --------------------------------------------------------------------------- #
def test_cd守卫_解析后路径判定(tmp_path):
    wt = _make_worktree(tmp_path)

    # 值：light 字面量（按命令内引号选择单/双引号包裹）
    cmd = {
        '变量': f'"W={_lp(wt)}; cd $W; pwd"',
        '花括号': f'"W={_lp(wt)}; cd ${{W}}; pwd"',
        '双引号': f"'W={_lp(wt)}; cd \"$W\"; pwd'",
        '字面量': f'"cd {_lp(wt)}; pwd"',
        '子目录': f'"cd {_lp(wt)}; cd sub; pwd"',
        '项目内相对': '"cd src; pwd"',
        '引号内非命令': "'echo \"cd /tmp\"'",
        '斜杠tmp': '"cd /tmp"',
        '上级': '"cd .."',
        '先进入再上级': f'"W={_lp(wt)}; cd $W; cd .."',
        '未定义变量': '"cd $T0470_UNSET_VAR"',
        '主目录': '"cd ~"',
        '绝对逃逸': f'"cd {_lp(wt)}; cd /etc"',
        '单引号字面量': "\"cd '/tmp'\"",
        '命令替换': '"cd $(pwd)"',
    }
    lines = [
        '从 工具_路径安全 导入 设置工具根',
        '从 工具_bash 导入 bash处理',
        f'设 根 为 设置工具根("{_lp(ROOT)}", 真)',
        '打印("设根=" + 转字符串(根))',
    ]
    for key, lit in cmd.items():
        lines.append(f'设 结果_{key} 为 bash处理(["命令": {lit}])')
        lines.append(f'打印("{key}码=" + 转字符串(结果_{key}["退出码"]))')
        lines.append(f'打印("{key}出=" + 结果_{key}["输出"].去除空白())')
    proc = _run(tmp_path, '_b.light', '\n'.join(lines), tool_roots=[tmp_path])
    _ok(proc, 'cd 守卫')
    rc, out, kv = proc
    assert _bool(kv, '设根') is True, out

    # 放行：变量/花括号/双引号/字面量/相对 都解析到同一个 worktree
    for key, expect in (
        ('变量', wt), ('花括号', wt), ('双引号', wt), ('字面量', wt),
        ('子目录', wt / 'sub'), ('项目内相对', os.path.join(ROOT, 'src')),
    ):
        assert kv[f'{key}码'] == '0', f'{key} 应放行，实际退出码 {kv[f"{key}码"]}\n{out}'
        assert _same(kv[f'{key}出'], str(expect)), f'{key} pwd 不对：{kv[f"{key}出"]}'
    assert kv['引号内非命令码'] == '0', f'引号里的 cd 不是命令，不该误杀\n{out}'

    # 拒绝：上级 / 绝对逃逸 / 未定义变量 / 单引号 / 命令替换
    for key in ('斜杠tmp', '上级', '先进入再上级', '未定义变量', '主目录',
                '绝对逃逸', '单引号字面量', '命令替换'):
        assert kv[f'{key}码'] == '-1', (
            f'{key} 必须被 cd 守卫拒绝，实际退出码 {kv[f"{key}码"]}\n{out}'
        )


# --------------------------------------------------------------------------- #
# B2. 间接形式：包装词 / eval / sh -c —— 字面量正则时代的「第二种绕过面」
# --------------------------------------------------------------------------- #
def test_cd守卫_间接形式也判定(tmp_path):
    root = tmp_path / '工程'
    root.mkdir()
    (root / '子').mkdir()

    # 值：light 字面量（按命令内引号选择单/双引号包裹）
    bad = {
        'then后': '"if true; then cd /tmp; fi"',
        '分号包裹': '"{ cd /tmp; }"',
        '子shell': '"(cd /tmp)"',
        'eval': f"'eval \"cd /tmp\"'",
        'shc': '\'sh -c "cd /tmp"\'',
        'bashlc': "\"bash -lc 'cd /tmp'\"",
        'sudo选项': '"sudo -E cd /tmp"',
        'pushd': '"pushd /tmp"',
    }
    good = {
        'eval根内': f"'eval \"cd {_lp(root)}/子\"'",
        'shc根内': f'\'sh -c "cd {_lp(root)}/子"\'',
        'then根内': f'"if true; then cd {_lp(root)}/子; fi"',
        'sudo根内': f'"sudo -E cd {_lp(root)}/子"',
        '脚本文件': '"sh /tmp/x.sh"',
    }
    lines = [
        '从 工具_路径安全 导入 设置工具根',
        '从 工具_bash 导入 bash处理',
        f'设 根 为 设置工具根("{_lp(root)}", 真)',
        '打印("设根=" + 转字符串(根))',
    ]
    for key, lit in {**bad, **good}.items():
        lines.append(f'设 结果_{key} 为 bash处理(["命令": {lit}])')
        lines.append(f'打印("{key}码=" + 转字符串(结果_{key}["退出码"]))')
    proc = _run(tmp_path, '_b2.light', '\n'.join(lines), tool_roots=[tmp_path])
    _ok(proc, '间接形式')
    rc, out, kv = proc
    assert _bool(kv, '设根') is True, out

    for key in bad:
        assert kv[f'{key}码'] == '-1', (
            f'{key} 是间接形式（不改命令名就能 cd 出去），必须被解析后判定拦下，'
            f'实际退出码 {kv[f"{key}码"]}\n{out}'
        )
    for key in good:
        assert kv[f'{key}码'] == '0', (
            f'{key} 目标在工具根内，不该被误杀，实际退出码 {kv[f"{key}码"]}\n{out}'
        )


# --------------------------------------------------------------------------- #
# C. 无 worktree 时回归：根仍是项目根，普通 cd .. 仍拒
# --------------------------------------------------------------------------- #
def test_无worktree时根仍为项目根(tmp_path):
    src = f'''
从 工具_路径安全 导入 取根目录, 解析安全路径
从 工具_bash 导入 bash处理

设 根 为 取根目录()
打印("根=" + 根)
打印("项目内=" + 转字符串(解析安全路径(根, "README.md")["ok"]))
打印("越界=" + 转字符串(解析安全路径(根, "../outside.txt")["ok"]))
设 上 为 bash处理(["命令": "cd .."])
打印("上级码=" + 转字符串(上["退出码"]))
设 绝 为 bash处理(["命令": "cd /tmp"])
打印("绝对码=" + 转字符串(绝["退出码"]))
设 命 为 bash处理(["命令": "pwd"])
打印("bash=" + 命["输出"].去除空白())
'''
    proc = _run(tmp_path, '_c.light', src)
    _ok(proc, '无 worktree 回归')
    rc, out, kv = proc

    assert _same(kv['根'], ROOT), f'无 worktree 时根应为项目根：{kv["根"]}'
    assert _bool(kv, '项目内') is True, f'项目内文件被误拒\n{out}'
    assert _bool(kv, '越界') is False, f'项目外路径被误放行\n{out}'
    assert kv['上级码'] == '-1', f'普通 cd .. 仍应拒绝，实际 {kv["上级码"]}'
    assert kv['绝对码'] == '-1', f'cd /tmp 仍应拒绝，实际 {kv["绝对码"]}'
    assert _same(kv['bash'], ROOT), f'无 worktree 时 bash 根应为项目根：{kv["bash"]}'


# --------------------------------------------------------------------------- #
# D. 白名单：不可信入口不能把任意目录设成根
# --------------------------------------------------------------------------- #
def test_工作目录参数必须过白名单(tmp_path):
    wt = _make_worktree(tmp_path)
    src = f'''
从 工具_路径安全 导入 设置工具根, 解析工具根, 取调用根, 取根目录

设 工作树 为 "{_lp(wt)}"
打印("临时不可信=" + 转字符串(设置工具根("{_lp(os.path.dirname(str(tmp_path)))}", 假) == 假))
打印("etc不可信=" + 转字符串(设置工具根("/etc", 假)))
设 解 为 解析工具根("/etc")
打印("etc解析=" + 转字符串(解["ok"]))
设 参 为 取调用根(["工作目录": "/etc"])
打印("参数回退=" + 转字符串(参 == 取根目录()))
设 信 为 设置工具根(工作树, 假)
打印("白名单内=" + 转字符串(信))
打印("根=" + 取根目录())
'''
    proc = _run(tmp_path, '_d.light', src, tool_roots=[tmp_path])
    _ok(proc, '白名单')
    rc, out, kv = proc

    assert _bool(kv, '临时不可信') is True, f'白名单外的临时父目录不得成为可不可信根\n{out}'
    assert _bool(kv, 'etc不可信') is False, f'/etc 不得被设为工具根\n{out}'
    assert _bool(kv, 'etc解析') is False, f'/etc 解析应被白名单拒绝\n{out}'
    assert _bool(kv, '参数回退') is True, f'白名单外的 工作目录 参数应回退本线程根\n{out}'
    assert _bool(kv, '白名单内') is True, f'HARNESS_TOOL_ROOTS 内的 worktree 应放行\n{out}'
    assert _same(kv['根'], str(wt)), f'白名单命中后根不生效：{kv["根"]}'


# --------------------------------------------------------------------------- #
# E. Web 服务端：会话 cwd 透传到工具执行（真实 处理对话 + 模拟模型）
# --------------------------------------------------------------------------- #
def test_Web服务端会话cwd透传到工具(tmp_path):
    wt = _make_worktree(tmp_path)

    src = f'''
从 流 导入 造块开始, 造文本增量, 造工具调用增量, 造块结束, 造结束, 造停止原因, 造工具调用原因
从 总入口 导入 组装注册表
从 web服务器 导入 Web服务端
从 会话存储 导入 会话存储
从 工具_路径安全 导入 取根目录
从 文件系统 导入 路径连接
从 字符串处理 导入 编码
从 JSON 导入 解析JSON, 序列化JSON
从 认证 导入 初始化认证

类 模拟客户端:
  属性 模型名 等于 "mock"
  属性 轮数 等于 0
  段落 构造:
    设 己.模型名 为 "mock"
    设 己.轮数 为 0
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    设 己.轮数 为 己.轮数 + 1
    如果 己.轮数 == 1:
      设 参 为 序列化JSON(["命令": "pwd"])
      返回 [造块开始(0, "tool_call"), 造工具调用增量(0, "c1", "bash", 参),
             造块结束(0, ["type": "tool-call", "id": "c1", "name": "bash", "arguments": 参]),
             造结束(造工具调用原因())]
    返回 [造块开始(0, "text"), 造文本增量(0, "完成"),
           造块结束(0, ["type": "text", "text": "完成"]), 造结束(造停止原因())]

初始化认证()
设 根 为 "{_lp(tmp_path)}"
设 库 为 新建 会话存储(路径连接(根, "sessions"))
设 服务 为 新建 Web服务端()
服务.设置会话库(库)
服务.配置(新建 模拟客户端(), 组装注册表(), 根, 30.0, "", 空)
设 工作树 为 "{_lp(wt)}"
设 应 为 服务.处理新建会话(["方法": "POST", "路径": "/api/sessions", "头": {{}},
  "体": 编码(序列化JSON(["标题": "工具根", "工作目录": 工作树]))], "")
设 元 为 解析JSON(应["体"])
设 标识 为 元["id"]
设 体 为 序列化JSON(["model": "mock", "session_id": 标识,
  "messages": [["role": "user", "content": "看下当前目录"]]])
设 对 为 服务.处理对话(["方法": "POST", "路径": "/v1/chat/completions", "头": {{}},
  "体": 编码(体)], "", "")
设 会 为 服务.取会话(标识)
设 全 为 序列化JSON(会.汇集全部事件())
打印("建会话=" + 转字符串(应["状态"]))
打印("对话=" + 转字符串(对["状态"]))
打印("含工作树=" + 转字符串(全.包含(工作树)))
打印("根=" + 取根目录())
'''
    proc = _run(tmp_path, '_e.light', src, tool_roots=[tmp_path])
    _ok(proc, 'Web 会话 cwd 透传')
    rc, out, kv = proc

    assert kv['建会话'] == '200', f'建会话失败：{out}'
    assert kv['对话'] == '200', f'对话失败：{out}'
    assert _bool(kv, '含工作树') is True, (
        '工具执行结果里没有会话 cwd —— 处理对话 没把会话 cwd 设成本线程工具根\n' + out
    )
    # 请求收尾必须清根：驱动主线程在 处理对话 之后应回落到项目根
    assert _same(kv['根'], ROOT), f'请求结束后工具根未清理（线程复用会串会话）：{kv["根"]}'

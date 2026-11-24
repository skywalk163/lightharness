# -*- coding: utf-8 -*-
"""T-0455：指令发现（AGENTS.md 多级发现 / 去重 / 截断）并渲染成系统提示段。

判据（见 hive/tasks/T-0455.md）全部走 .light 侧真实段落（子进程 `python 运行.py <driver>`）：
  1. 仓库根 AGENTS.md + src/AGENTS.md 两级 → 发现 2 份，作用域标注正确；
  2. CLAUDE.md 与同名 AGENTS.md 内容相同 → 只留一份（AGENTS.md 优先），去重数=1；
  3. 文件 > 上限 → 被截断且带「（已截断）」标记，输出总字节 ≤ 上限 + 标记长度；
  4. 渲染指令段的段落顺序 = 发现顺序（用户全局 → 仓库根 → 子目录）；
  5. 装配提示段 里项目指令段下标 < 通用契约段下标；
  6. 空仓库 → 空文本，不报错；
  7. 反跑：把去重关掉，用例 2 立红。

「文件读取必须可注入」的落实方式：
  driver 里的读回调显式传给 发现指令(...) 的第 4 个参数，默认的 文件系统.读取文件
  一次都不会被 发现指令 用到（假仓库仅存在于 pytest 临时目录，仓库自身文件全程不读）。

反跑（判据 7）用 shadow 目录注入变异版 智能体指令.light（把去重守卫行替换为 `如果 假:`），
  src/ 原文件全程不动 —— 与 tests/test_T0451_技能目录.py 同一手法，pytest -n 4 安全。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SRC_MODULE = os.path.join(ROOT, 'src', '智能体指令.light')
TIMEOUT_SEC = 180

# 反跑锚点：按候选组去重 的守卫行（去重语义的唯一出口）
DEDUP_GUARD = '如果 字典包含键(已有, 摘要): 继续'

# 截断标记（与 src/智能体指令.light 的 指令截断标记 同字面量；判据 3 断言用）
TRUNC_MARK = '（已截断）'

# ---------------------------------------------------------------------
# 公共 driver 片段
# ---------------------------------------------------------------------

_FLAT = '''
段落 压平(文本):
  设 r 为 替换字符串(文本, "\\r", "<CR>")
  设 r 为 替换字符串(r, "\\n", "<NL>")
  设 r 为 替换字符串(r, "=", "<EQ>")
  返回 r
'''

# 判据 1/2/6：只跑发现，逐项打印显示路径 + 作用域 + 字节数
_DISCOVER_DRIVER = '''从 智能体指令 导入 发现指令, 渲染指令段, 装配提示段
从 文件系统 导入 读取文件
''' + _FLAT + '''
设 仓库根 为 "__ROOT__"
设 cwd 为 "__CWD__"
设 家 为 "__DSH__"
设 代理家 为 "__AGENTS__"

段落 主程():
  设 配置 为 ["dshHome": 家, "agentsHome": 代理家]
  设 发现 为 发现指令(仓库根, cwd, 配置, 读桩)
  设 文件表 为 发现["文件表"]
  打印("文件数=" + 转字符串(列表长度(文件表)))
  打印("去重数=" + 转字符串(发现["去重数"]))
  打印("跳过数=" + 转字符串(列表长度(发现["跳过"])))
  设 序号 为 0
  遍历 项 之 文件表:
    打印("项" + 转字符串(序号) + "_显示=" + 压平(项["显示路径"]))
    打印("项" + 转字符串(序号) + "_作用域=" + 压平(项["作用域"]))
    打印("项" + 转字符串(序号) + "_字节=" + 转字符串(项["字节数"]))
    设 序号 为 序号 + 1
  设 段 为 渲染指令段(发现)
  打印("渲染=" + 压平(段))

段落 读桩(路径):
  返回 读取文件(路径)

主程()
'''

# 判据 3/4：截断与段落顺序
_RENDER_DRIVER = '''从 智能体指令 导入 发现指令, 渲染指令段, 装配提示段
从 文件系统 导入 读取文件
从 溢出 导入 字节长度
从 字符串处理 导入 包含
从 内置核心字符串 导入 查找子串
''' + _FLAT + '''
设 仓库根 为 "__ROOT__"
设 cwd 为 "__CWD__"
设 家 为 "__DSH__"
设 代理家 为 "__AGENTS__"

段落 主程():
  设 配置 为 ["dshHome": 家, "agentsHome": 代理家]
  设 发现 为 发现指令(仓库根, cwd, 配置, 读桩)
  # 顺序：逐份打印显示路径（判据 4 断言该序列）
  设 序号 为 0
  遍历 项 之 发现["文件表"]:
    打印("序" + 转字符串(序号) + "=" + 压平(项["显示路径"]))
    设 序号 为 序号 + 1
  打印("文件数=" + 转字符串(列表长度(发现["文件表"])))
  # 截断：小预算 → 必须带标记且总量受控
  设 段 为 渲染指令段(发现, 300)
  打印("截断_字节=" + 转字符串(字节长度(段)))
  打印("截断_含标记=" + 转字符串(包含(段, "（已截断）")))
  打印("截断_头=" + 压平(截取(段, 0, 40)))
  # 预算充足 → 不截断
  设 全段 为 渲染指令段(发现, 65536)
  打印("全_含标记=" + 转字符串(包含(全段, "（已截断）")))
  # 段落顺序 = 发现顺序：第一份的标题下标必须最小、最后一份最大
  设 序0 为 查找子串(全段, "## " + 发现["文件表"][0]["显示路径"])
  设 末位 为 列表长度(发现["文件表"]) - 1
  设 序末 为 查找子串(全段, "## " + 发现["文件表"][末位]["显示路径"])
  打印("首段下标=" + 转字符串(序0))
  打印("末段下标=" + 转字符串(序末))
  打印("段数=" + 转字符串(列表长度(发现["文件表"])))

段落 读桩(路径):
  返回 读取文件(路径)

主程()
'''

# 判据 5：装配顺序
_ASSEMBLE_DRIVER = '''从 智能体指令 导入 装配提示段
从 内置核心字符串 导入 查找子串
''' + _FLAT + '''
段落 主程():
  设 项目 为 "## AGENTS.md\\n\\n项目规矩"
  设 契约 为 "通用契约三条"
  设 拼 为 装配提示段(项目, 契约)
  打印("拼=" + 压平(拼))
  打印("项目下标=" + 转字符串(查找子串(拼, 项目)))
  打印("契约下标=" + 转字符串(查找子串(拼, 契约)))
  打印("空左=" + 压平(装配提示段("", 契约)))
  打印("空右=" + 压平(装配提示段(项目, "")))
  打印("双空=" + 压平(装配提示段("", "")))
主程()
'''


# ---------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------

def _light_path(p):
    """临时目录路径 → .light 字符串字面量安全形式（正斜杠，避免反斜杠转义歧义）。"""
    return str(p).replace('\\', '/')


def _run(driver, tmp_path, name, **subs):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, timeout=TIMEOUT_SEC, env=env)
    out = proc.stdout.decode('utf-8', errors='replace') + proc.stderr.decode('utf-8', errors='replace')
    assert proc.returncode == 0, ('driver 应 rc=0\n--- out ---\n' + out[-3000:])
    kv = {}
    for line in out.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return kv, out


def _mk(base, rel, text):
    p = base / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')
    return p


def _unflat(v):
    return str(v).replace('<CR>', '\r').replace('<NL>', '\n').replace('<EQ>', '=')


def _dsh(run_dir):
    """给一次运行准备两个「不存在的」用户全局根（避免踩到真机 ~/.dsh）。"""
    return (_light_path(run_dir / 'home' / '.dsh'), _light_path(run_dir / 'home' / '.agents'))


def _discover(tree, cwd, run_dir, name):
    dsh, agents = _dsh(run_dir)
    driver = (_DISCOVER_DRIVER
              .replace('__ROOT__', _light_path(tree))
              .replace('__CWD__', _light_path(cwd))
              .replace('__DSH__', dsh)
              .replace('__AGENTS__', agents))
    return _run(driver, run_dir, name)


def _int(kv, key):
    assert key in kv, ('driver 没打印 %s，实际键：%s' % (key, sorted(kv)))
    return int(kv[key])


# ---------------------------------------------------------------------
# 判据 1：两级 AGENTS.md → 2 份，作用域标注正确
# ---------------------------------------------------------------------

def test_两级AGENTS发现两份且作用域正确(tmp_path):
    tree = tmp_path / 'repo_a'
    _mk(tree, 'AGENTS.md', '根规矩：全仓通用。\n')
    _mk(tree, 'src/AGENTS.md', '子目录规矩：src 专用。\n')
    run_dir = tmp_path / 'run_a'
    run_dir.mkdir()
    kv, out = _discover(tree, tree / 'src', run_dir, 't0455_j1.light')

    assert _int(kv, '文件数') == 2, ('判据 1：两级配置应发现 2 份', kv, out)
    shows = [_unflat(kv['项0_显示']), _unflat(kv['项1_显示'])]
    assert shows == ['AGENTS.md', 'src/AGENTS.md'], ('显示路径应为根→子目录', shows, out)
    scopes = [_unflat(kv['项0_作用域']), _unflat(kv['项1_作用域'])]
    assert scopes == ['.', 'src'], ('作用域应分别为仓库根与 src 目录', scopes, out)
    assert _int(kv, '去重数') == 0, ('不同内容不得被去重', kv, out)
    assert _int(kv, '项0_字节') == len('根规矩：全仓通用。\n'.encode('utf-8')), kv
    assert _int(kv, '项1_字节') == len('子目录规矩：src 专用。\n'.encode('utf-8')), kv


# ---------------------------------------------------------------------
# 判据 2：CLAUDE.md 与 AGENTS.md 同内容 → 只留一份（AGENTS.md 优先）
# ---------------------------------------------------------------------

def test_同名内容去重只留一份(tmp_path):
    tree = tmp_path / 'repo_b'
    同文 = '同一份规矩：去重后只应留一份。\n'
    _mk(tree, 'AGENTS.md', 同文)
    _mk(tree, 'CLAUDE.md', 同文)
    run_dir = tmp_path / 'run_b'
    run_dir.mkdir()
    kv, out = _discover(tree, tree, run_dir, 't0455_j2.light')

    assert _int(kv, '文件数') == 1, ('判据 2：同内容只能留一份', kv, out)
    assert _int(kv, '去重数') == 1, ('判据 2：去重数应为 1', kv, out)
    assert _unflat(kv['项0_显示']) == 'AGENTS.md', (
        '应保留候选顺序更靠前的 AGENTS.md（CLAUDE.md 被折叠）', kv, out)


# ---------------------------------------------------------------------
# 判据 3：超上限 → 截断 + 「（已截断）」且总量受控
# ---------------------------------------------------------------------

def test_超上限被截断且带标记(tmp_path):
    tree = tmp_path / 'repo_c'
    _mk(tree, 'AGENTS.md', 'x' * 5000 + '\n')
    run_dir = tmp_path / 'run_c'
    run_dir.mkdir()
    dsh, agents = _dsh(run_dir)
    driver = (_RENDER_DRIVER
              .replace('__ROOT__', _light_path(tree))
              .replace('__CWD__', _light_path(tree))
              .replace('__DSH__', dsh)
              .replace('__AGENTS__', agents))
    kv, out = _run(driver, run_dir, 't0455_j3.light')

    assert kv.get('截断_含标记') in ('True', '真'), ('判据 3：截断必须带标记', kv, out)
    got = _int(kv, '截断_字节')
    budget = 300 + len(TRUNC_MARK.encode('utf-8'))
    assert got <= budget, ('判据 3：输出总字节 %s 应 ≤ 上限 + 标记长度 %s' % (got, budget), kv, out)
    assert got > 200, ('判据 3：截断后不应把内容砍光（应接近上限）', kv, out)
    assert _unflat(kv['截断_头']).startswith('## AGENTS.md'), ('截断后仍须保留段落标题', kv, out)
    assert kv.get('全_含标记') in ('False', '假'), ('判据 3：预算充足不得出现截断标记', kv, out)


# ---------------------------------------------------------------------
# 判据 4：段落顺序 = 发现顺序（用户全局 → 仓库根 → 子目录）
# ---------------------------------------------------------------------

def test_段落顺序等于发现顺序(tmp_path):
    tree = tmp_path / 'repo_d'
    _mk(tree, 'AGENTS.md', '根规矩。\n')
    _mk(tree, 'src/AGENTS.md', '子目录规矩。\n')
    home = tmp_path / 'run_d' / 'home'
    _mk(home, '.dsh/AGENTS.md', '全局规矩。\n')
    run_dir = tmp_path / 'run_d'
    run_dir.mkdir(exist_ok=True)
    dsh, agents = _dsh(run_dir)
    driver = (_RENDER_DRIVER
              .replace('__ROOT__', _light_path(tree))
              .replace('__CWD__', _light_path(tree / 'src'))
              .replace('__DSH__', dsh)
              .replace('__AGENTS__', agents))
    kv, out = _run(driver, run_dir, 't0455_j4.light')

    n = _int(kv, '文件数')
    assert n == 3, ('判据 4：用户全局 + 两级项目指令 = 3 份', kv, out)
    order = [_unflat(kv['序%d' % i]) for i in range(n)]
    assert order == ['~/.dsh/AGENTS.md', 'AGENTS.md', 'src/AGENTS.md'], (
        '判据 4：顺序必须是 用户全局 → 仓库根 → 子目录', order, out)
    # 渲染顺序与发现顺序一致：首段下标最小、末段下标最大且为正
    first, last = _int(kv, '首段下标'), _int(kv, '末段下标')
    assert first == 0, ('首段应在文本最前（下标 0）', kv, out)
    assert last > first, ('末段下标应大于首段', kv, out)


# ---------------------------------------------------------------------
# 判据 5：装配提示段 —— 项目指令在前、通用契约在后
# ---------------------------------------------------------------------

def test_装配顺序项目指令在通用契约之前(tmp_path):
    run_dir = tmp_path / 'run_e'
    run_dir.mkdir()
    kv, out = _run(_ASSEMBLE_DRIVER, run_dir, 't0455_j5.light')

    assert _int(kv, '项目下标') >= 0, ('项目指令段必须出现在装配结果里', kv, out)
    assert _int(kv, '契约下标') >= 0, ('通用契约段必须出现在装配结果里', kv, out)
    assert _int(kv, '项目下标') < _int(kv, '契约下标'), (
        '判据 5：项目指令必须在通用契约之前', kv, out)
    assert _unflat(kv['空左']) == '通用契约三条', ('只给契约时应原样输出', kv, out)
    assert _unflat(kv['空右']) == '## AGENTS.md\n\n项目规矩', ('只给项目时应原样输出', kv, out)
    assert kv['双空'] == '', ('两侧都空应输出空文本', kv, out)


# ---------------------------------------------------------------------
# 判据 6：空仓库 → 空文本，不报错
# ---------------------------------------------------------------------

def test_空仓库返回空文本不报错(tmp_path):
    tree = tmp_path / 'repo_f'
    tree.mkdir()
    run_dir = tmp_path / 'run_f'
    run_dir.mkdir()
    kv, out = _discover(tree, tree, run_dir, 't0455_j6.light')

    assert _int(kv, '文件数') == 0, ('判据 6：空仓库不应发现任何指令文件', kv, out)
    assert _int(kv, '跳过数') == 0, ('判据 6：空仓库不应有跳过项', kv, out)
    assert kv.get('渲染') == '', ('判据 6：空仓库渲染结果必须为空文本', kv, out)


# ---------------------------------------------------------------------
# 判据 7：反跑 —— 关掉去重，用例 2 立红
# ---------------------------------------------------------------------

_SHADOW_RUNNER = '''# -*- coding: utf-8 -*-
"""T-0455 反跑引导：把 shadow 目录插到光明导入钩子搜索路径最前后跑 driver。

用法: python t0455_shadow_runner.py <shadow_dir> <driver_path>
shadow_dir 内放变异版 智能体指令.light；钩子先命中 shadow，兄弟模块仍从
lightharness/src 正常解析。src/ 原文件不动。
"""
import os
import sys

LH_ROOT = r"__LH_ROOT__"
sys.path.insert(0, LH_ROOT)
import 运行 as lh_run  # noqa: E402

lh_run._setup_paths()

shadow = os.path.abspath(sys.argv[1])
entry = sys.argv[2]
for f in sys.meta_path:
    if type(f).__name__ == 'LightFinder':
        f.search_paths.insert(0, shadow)
        break

os.environ.setdefault('HARNESS_PY', sys.executable)
from cli.light import main as light_main  # noqa: E402

for _p in (lh_run.STDLIB, lh_run.ROOT, lh_run.SRC):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

sys.argv = ['light', 'run', '--stdlib-dir', lh_run.STDLIB, entry]
sys.exit(light_main())
'''


def test_反跑_关掉去重_用例2立红(tmp_path):
    original = open(SRC_MODULE, 'r', encoding='utf-8', newline='').read()
    assert original.count(DEDUP_GUARD) == 1, (
        '反跑锚点丢失或出现多处（按候选组去重的守卫行）', DEDUP_GUARD)
    mutated = original.replace(DEDUP_GUARD, '如果 假: 继续', 1)

    shadow_dir = tmp_path / 'shadow'
    shadow_dir.mkdir()
    (shadow_dir / '智能体指令.light').write_text(mutated, encoding='utf-8')

    runner_path = tmp_path / 't0455_shadow_runner.py'
    runner_path.write_text(_SHADOW_RUNNER.replace('__LH_ROOT__', ROOT), encoding='utf-8')

    tree = tmp_path / 'repo_g'
    同文 = '同一份规矩：去重后只应留一份。\n'
    _mk(tree, 'AGENTS.md', 同文)
    _mk(tree, 'CLAUDE.md', 同文)
    run_dir = tmp_path / 'run_g'
    run_dir.mkdir()
    dsh, agents = _dsh(run_dir)
    driver_path = run_dir / 't0455_j7.light'
    driver_path.write_text(
        _DISCOVER_DRIVER
        .replace('__ROOT__', _light_path(tree))
        .replace('__CWD__', _light_path(tree))
        .replace('__DSH__', dsh)
        .replace('__AGENTS__', agents),
        encoding='utf-8')

    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, str(runner_path), str(shadow_dir), str(driver_path)],
                          cwd=ROOT, capture_output=True, timeout=TIMEOUT_SEC, env=env)
    out = proc.stdout.decode('utf-8', errors='replace') + proc.stderr.decode('utf-8', errors='replace')
    assert proc.returncode == 0, ('反跑子进程本身不得崩（变异版语法必须仍合法）', out[-3000:])

    kv = {}
    for line in out.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    assert _int(kv, '文件数') == 2, (
        '反跑失败：关掉去重后文件数仍为 1，说明用例 2 抓不住去重缺失（判据假绿）', kv, out[-3000:])
    assert _int(kv, '去重数') == 0, ('变异版去重数应为 0', kv, out[-3000:])
    shows = [_unflat(kv['项0_显示']), _unflat(kv['项1_显示'])]
    assert shows == ['AGENTS.md', 'CLAUDE.md'], ('变异版应同时暴露两份同内容文件', shows, out[-3000:])

    # src 原文件全程未被反跑污染
    assert open(SRC_MODULE, 'r', encoding='utf-8', newline='').read() == original, \
        'src/智能体指令.light 被反跑污染'

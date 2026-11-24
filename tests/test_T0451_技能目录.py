# -*- coding: utf-8 -*-
"""T-0451：技能目录发现 + skill 工具（SKILL.md 扫描 + 系统提示段）判据。

对齐 hive/tasks/T-0451.md 判据：
  1. 两个根目录各放 1 个技能 → 发现 2 个，字段正确；
  2. 同名技能两处都有 → 只留 1 个（先出现的那份）；
  3. 坏 frontmatter（缺 --- / 无 name）→ 跳过并给 跳过原因，好的仍然发现（不整体失败）；
  4. 渲染技能清单段 含两条 `- 名字：描述`，超长描述被截断（按码点），`<` 被转义；
  5. skill 工具：已知 name 返回含 <skill_content name="x">；未知 name 返回 isError=真 + 可用清单；
  6. 工具定义过 工具.校验工具定义形状，名字恰为 skill；
  7. 反跑：把「同名去重」删掉，用例 2 立红。

反跑实现（判据 7，pytest -n 4 安全）：
  读 src/技能目录.light → 把同名去重守卫行
      如果 列表包含(已有名字表, 解析["名字"]):
  替换为 `如果 假:` → 写入临时 shadow 目录 → 用 shadow runner 引导光明运行器
  （把 shadow 目录插到 _light_import_hook 搜索路径**最前**，src/ 原文件全程不动）
  → 跑与用例 2 相同的发现 driver → 变异版发现数必须变成 2，
  即用例 2 的断言 `技能数 == 1` 在变异后必红。无写回-还原竞态。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SRC_SKILL_DIR = os.path.join(ROOT, 'src', '技能目录.light')
TIMEOUT_SEC = 180

# 同名去重守卫行（技能目录.light 内的 T-0451 判据 2 反跑锚点）
DEDUP_GUARD = '如果 列表包含(已有名字表, 解析["名字"]):'


def _run(driver, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, timeout=TIMEOUT_SEC, env=env)
    out = proc.stdout.decode('utf-8', errors='replace') + proc.stderr.decode('utf-8', errors='replace')
    kv = {}
    for line in out.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, out, kv


def _missing_module(out):
    return ('lightplugin' in out and
            ('ModuleNotFound' in out or '导入失败' in out or 'No module' in out))


def _skill_md(name, desc, body):
    """好 frontmatter 的 SKILL.md 文本。"""
    return '---\nname: %s\ndescription: %s\n---\n%s' % (name, desc, body)


def _mk_skill(base_dir, name, text):
    d = base_dir / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'SKILL.md').write_text(text, encoding='utf-8')
    return d


def _light_root(tmp_path):
    """把临时根路径转成 .light 字符串字面量安全形式（正斜杠，避免转义歧义）。"""
    return str(tmp_path).replace('\\', '/')


def _norm(p):
    """路径归一：Windows 下 driver 内 os.path.join 用反斜杠拼接，统一成正斜杠再断言。"""
    return str(p).replace('\\', '/')


def _unflat(v):
    """driver 压平的逆操作：<NL> → 换行、<EQ> → 等号，让断言贴近真实产物。"""
    return str(v).replace('<NL>', '\n').replace('<EQ>', '=')


# ---------------------------------------------------------------------
# 公共 driver 片段
# ---------------------------------------------------------------------

_FLAT = '''
段落 压平(文本):
  设 r 为 替换字符串(文本, "\\n", "<NL>")
  设 r 为 替换字符串(r, "=", "<EQ>")
  返回 r
'''

_DISCOVER_DRIVER = '''从 技能目录 导入 发现技能, 解析技能文件, 渲染技能清单段, 造技能工具定义
从 工具 导入 校验工具定义形状

''' + _FLAT + '''
段落 主程():
  设 根 为 "__ROOT__"
  设 发现 为 发现技能(根)
  设 技能表 为 发现["技能"]
  设 跳过表 为 发现["跳过"]
  打印 "技能数=" + 转字符串(列表长度(技能表))
  打印 "跳过数=" + 转字符串(列表长度(跳过表))
  设 序号 为 0
  当 序号 < 列表长度(技能表):
    设 项 为 技能表[序号]
    打印 "技能" + 转字符串(序号) + "_名字=" + 项["名字"]
    打印 "技能" + 转字符串(序号) + "_描述=" + 压平(项["描述"])
    打印 "技能" + 转字符串(序号) + "_路径=" + 项["路径"]
    打印 "技能" + 转字符串(序号) + "_正文长度=" + 转字符串(项["正文长度"])
    设 序号 为 序号 + 1
  设 序号 为 0
  当 序号 < 列表长度(跳过表):
    设 项 为 跳过表[序号]
    打印 "跳过" + 转字符串(序号) + "_原因=" + 压平(项["跳过原因"])
    打印 "跳过" + 转字符串(序号) + "_路径=" + 项["路径"]
    设 序号 为 序号 + 1
  设 空解析 为 解析技能文件("")
  打印 "空文件原因=" + 压平(空解析["跳过原因"])
主程()
'''

_RENDER_DRIVER = '''从 技能目录 导入 发现技能, 解析技能文件, 渲染技能清单段, 造技能工具定义

''' + _FLAT + '''
段落 主程():
  设 根 为 "__ROOT__"
  设 发现 为 发现技能(根)
  设 技能表 为 发现["技能"]
  设 段文本 为 渲染技能清单段(技能表)
  打印 "清单段=" + 压平(段文本)
  设 长描 为 ""
  设 k 为 0
  当 k < 100:
    设 长描 为 长描 + "字"
    设 k 为 k + 1
  设 大表 为 [["名字": "longy", "描述": 长描], ["名字": "angle", "描述": "含<b>尖"]]
  设 大文本 为 渲染技能清单段(大表)
  打印 "大表段=" + 压平(大文本)
  设 三表 为 [["名字": "a1", "描述": "d1"], ["名字": "a2", "描述": "d2"], ["名字": "a3", "描述": "d3"]]
  设 截文本 为 渲染技能清单段(三表, 2)
  打印 "截断段=" + 压平(截文本)
主程()
'''

_TOOL_DRIVER = '''从 技能目录 导入 发现技能, 解析技能文件, 渲染技能清单段, 造技能工具定义
从 工具 导入 校验工具定义形状

''' + _FLAT + '''
段落 主程():
  设 根 为 "__ROOT__"
  设 定义 为 造技能工具定义(发现技能, 根)
  打印 "工具名=" + 定义["name"]
  设 形状错 为 校验工具定义形状(定义)
  打印 "形状错误数=" + 转字符串(列表长度(形状错))
  设 执行函数 为 定义["execute"]
  设 好 为 执行函数(["name": "alpha"])
  打印 "好_isError=" + 转字符串(好["isError"])
  设 好块表 为 好["content"]
  设 好块 为 好块表[0]
  打印 "好_文本=" + 压平(好块["text"])
  设 坏 为 执行函数(["name": "不存在"])
  打印 "坏_isError=" + 转字符串(坏["isError"])
  设 坏块表 为 坏["content"]
  设 坏块 为 坏块表[0]
  打印 "坏_文本=" + 压平(坏块["text"])
主程()
'''


def _build_tree_two_skills(tmp_path):
    """判据 1 树：root/skills/alpha 与 root/.skills/beta 各 1 个技能。"""
    _mk_skill(tmp_path / 'skills', 'alpha', _skill_md('alpha', 'Alpha 描述', 'Alpha 正文。\n'))
    _mk_skill(tmp_path / '.skills', 'beta', _skill_md('beta', 'Beta 描述', 'Beta 正文。\n'))
    return tmp_path


def _build_tree_dup(tmp_path):
    """判据 2 树：同名技能 dup 同时出现在 skills/ 与 .skills/。"""
    _mk_skill(tmp_path / 'skills', 'dup', _skill_md('dup', '来自 skills', '先出现的正文。\n'))
    _mk_skill(tmp_path / '.skills', 'dup', _skill_md('dup', '来自点skills', '后出现的正文。\n'))
    return tmp_path


def _build_tree_bad(tmp_path):
    """判据 3 树：两个坏 frontmatter + 一个好技能。"""
    _mk_skill(tmp_path / 'skills', 'bad1',
              'name: bad1\ndescription: 缺分隔线的坏技能\n正文占位\n')
    _mk_skill(tmp_path / 'skills', 'bad2',
              '---\ndescription: 无名字的坏技能\n---\n正文占位\n')
    _mk_skill(tmp_path / '.skills', 'good', _skill_md('good', '好技能描述', '好正文。\n'))
    return tmp_path


# ---------------------------------------------------------------------
# 判据 1：两处各 1 技能 → 发现 2 个，字段正确
# ---------------------------------------------------------------------

def test_两处各一技能发现两个且字段正确(tmp_path):
    root = _build_tree_two_skills(tmp_path)
    rc, out, kv = _run(_DISCOVER_DRIVER.replace('__ROOT__', _light_root(root)),
                       tmp_path, 't0451_j1.light')
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓：请在 192.168.0.88 上跑')
    assert rc == 0, out
    assert kv.get('技能数') == '2', ('判据 1：应发现 2 个技能', kv, out)
    names = [kv.get('技能%d_名字' % i) for i in range(2)]
    assert names == ['alpha', 'beta'], ('技能名不对', names, out)
    assert kv.get('技能0_描述') == 'Alpha 描述', ('描述字段不对', kv, out)
    assert kv.get('技能1_描述') == 'Beta 描述', ('描述字段不对', kv, out)
    p0, p1 = _norm(kv.get('技能0_路径', '')), _norm(kv.get('技能1_路径', ''))
    assert '/skills/alpha' in p0 and '.skills' not in p0, ('alpha 应来自 skills/', p0, out)
    assert '/.skills/beta' in p1, ('beta 应来自 .skills/', p1, out)
    assert int(kv.get('技能0_正文长度', '0')) > 0, ('正文长度字段应为正', kv, out)
    assert int(kv.get('技能1_正文长度', '0')) > 0, ('正文长度字段应为正', kv, out)
    assert kv.get('空文件原因') != '', ('解析技能文件(空) 应给跳过原因', kv, out)


# ---------------------------------------------------------------------
# 判据 2：同名技能两处都有 → 只留 1 个（先出现的那份）
# ---------------------------------------------------------------------

def test_同名去重只留先出现的(tmp_path):
    root = _build_tree_dup(tmp_path)
    rc, out, kv = _run(_DISCOVER_DRIVER.replace('__ROOT__', _light_root(root)),
                       tmp_path, 't0451_j2.light')
    assert rc == 0, out
    assert kv.get('技能数') == '1', ('判据 2：同名技能必须去重只留 1 个', kv, out)
    assert kv.get('技能0_名字') == 'dup', out
    assert kv.get('技能0_描述') == '来自 skills', ('应保留先出现（skills/）那份', kv, out)
    p0 = _norm(kv.get('技能0_路径', ''))
    assert '/skills/dup/' in p0, ('保留项路径应指向 skills/ 那份', p0, out)
    assert '.skills' not in p0, ('不应指向 .skills/ 那份', p0, out)


# ---------------------------------------------------------------------
# 判据 3：坏 frontmatter → 跳过并给 跳过原因，好的仍然发现（不整体失败）
# ---------------------------------------------------------------------

def test_坏frontmatter跳过且好的仍发现(tmp_path):
    root = _build_tree_bad(tmp_path)
    rc, out, kv = _run(_DISCOVER_DRIVER.replace('__ROOT__', _light_root(root)),
                       tmp_path, 't0451_j3.light')
    assert rc == 0, out
    assert kv.get('技能数') == '1', ('好技能必须仍被发现', kv, out)
    assert kv.get('技能0_名字') == 'good', out
    assert kv.get('跳过数') == '2', ('两个坏文件都应记入跳过表', kv, out)
    reasons = [kv.get('跳过%d_原因' % i, '') for i in range(2)]
    assert any('缺起始 ---' in r for r in reasons), ('缺 --- 的跳过原因缺失', reasons, out)
    assert any('缺 name' in r for r in reasons), ('无 name 的跳过原因缺失', reasons, out)
    paths = [_norm(kv.get('跳过%d_路径' % i, '')) for i in range(2)]
    assert any('bad1' in p for p in paths) and any('bad2' in p for p in paths), \
        ('跳过表应记录坏文件路径', paths, out)


# ---------------------------------------------------------------------
# 判据 4：渲染技能清单段 —— 两条 `- 名字：描述`、按码点截断、`<` 转义、条数上限
# ---------------------------------------------------------------------

def test_渲染技能清单段_条目截断转义与上限(tmp_path):
    root = _build_tree_two_skills(tmp_path)
    rc, out, kv = _run(_RENDER_DRIVER.replace('__ROOT__', _light_root(root)),
                       tmp_path, 't0451_j4.light')
    assert rc == 0, out
    seg = kv.get('清单段', '')
    assert '- alpha：Alpha 描述' in seg, ('判据 4：应含 `- 名字：描述` 行', seg, out)
    assert '- beta：Beta 描述' in seg, ('判据 4：应含 `- 名字：描述` 行', seg, out)
    big = kv.get('大表段', '')
    assert '- longy：' + '字' * 80 + '…' in big, ('超长描述应按码点截断到 80 并加省略号', big, out)
    assert '字' * 81 not in big, ('截断后不得残留 81 个字', big, out)
    assert '- angle：含&lt;b&gt;尖' in big, ('`<` 必须被转义', big, out)
    cut = kv.get('截断段', '')
    assert '- a1：d1' in cut and '- a2：d2' in cut, ('上限内条目应保留', cut, out)
    assert '- a3：' not in cut, ('超上限条目应被裁掉', cut, out)
    assert '仅列前 2 个' in cut, ('超限应给提示行', cut, out)


# ---------------------------------------------------------------------
# 判据 5/6：skill 工具 + 工具定义形状
# ---------------------------------------------------------------------

def test_skill工具_已知名渲染未知名列清单(tmp_path):
    root = _build_tree_two_skills(tmp_path)
    # alpha 正文里放尖括号，顺带验证正文转义
    _mk_skill(root / 'skills', 'alpha', _skill_md('alpha', 'Alpha 描述', '用法：看 <示例> 段。\n'))
    rc, out, kv = _run(_TOOL_DRIVER.replace('__ROOT__', _light_root(root)),
                       tmp_path, 't0451_j5.light')
    assert rc == 0, out
    assert kv.get('好_isError') in ('False', '假'), ('已知名不得 isError', kv, out)
    good = _unflat(kv.get('好_文本', ''))
    assert '<skill_content name="alpha">' in good, ('已知名应返回 <skill_content name="x">', good, out)
    assert '&lt;示例&gt;' in good, ('正文里的 < > 必须被转义', good, out)
    assert '</skill_content>' in good, out
    assert kv.get('坏_isError') in ('True', '真'), ('未知名应 isError=真', kv, out)
    bad = kv.get('坏_文本', '')
    assert '未知技能' in bad, ('未知名应给未知提示', bad, out)
    assert 'alpha' in bad and 'beta' in bad, ('未知名应列出可用名字', bad, out)


def test_工具定义形状合法且名为skill(tmp_path):
    root = _build_tree_two_skills(tmp_path)
    rc, out, kv = _run(_TOOL_DRIVER.replace('__ROOT__', _light_root(root)),
                       tmp_path, 't0451_j6.light')
    assert rc == 0, out
    assert kv.get('工具名') == 'skill', ('工具名必须恰为 skill', kv, out)
    assert kv.get('形状错误数') == '0', ('工具定义必须过 校验工具定义形状', kv, out)


# ---------------------------------------------------------------------
# 判据 7：反跑 —— 把「同名去重」删掉，用例 2 立红
#   变异 = 守卫行替换为 `如果 假:`（行为上等于删掉去重），shadow 注入不碰 src 原文件。
# ---------------------------------------------------------------------

_SHADOW_RUNNER = '''# -*- coding: utf-8 -*-
"""T-0451 反跑引导：把 shadow 目录插到光明导入钩子搜索路径最前后跑 driver。

用法: python t0451_shadow_runner.py <shadow_dir> <driver_path>
shadow_dir 内放变异版 技能目录.light；钩子先命中 shadow，兄弟模块（工具/
技能清单 等）仍从 lightharness/src 正常解析。lightharness/src 原文件不动。
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

# 与 运行.py main 一致：CLI 导入后重申宿主路径优先（R100 路 B）
for _p in (lh_run.STDLIB, lh_run.ROOT, lh_run.SRC):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)

sys.argv = ['light', 'run', '--stdlib-dir', lh_run.STDLIB, entry]
sys.exit(light_main())
'''


def test_反跑_删掉同名去重_用例2立红(tmp_path):
    original = open(SRC_SKILL_DIR, 'r', encoding='utf-8').read()
    assert original.count(DEDUP_GUARD) == 1, \
        ('反跑锚点丢失或出现多处（同名去重守卫行）', DEDUP_GUARD)
    mutated = original.replace(DEDUP_GUARD, '如果 假:', 1)

    shadow_dir = tmp_path / 'shadow'
    shadow_dir.mkdir()
    (shadow_dir / '技能目录.light').write_text(mutated, encoding='utf-8')

    runner_path = tmp_path / 't0451_shadow_runner.py'
    runner_path.write_text(_SHADOW_RUNNER.replace('__LH_ROOT__', ROOT), encoding='utf-8')

    root = _build_tree_dup(tmp_path / 'tree')
    driver_path = tmp_path / 't0451_j7.light'
    driver_path.write_text(
        _DISCOVER_DRIVER.replace('__ROOT__', _light_root(root)), encoding='utf-8')

    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run(
        [sys.executable, str(runner_path), str(shadow_dir), str(driver_path)],
        cwd=ROOT, capture_output=True, timeout=TIMEOUT_SEC, env=env)
    out = proc.stdout.decode('utf-8', errors='replace') + proc.stderr.decode('utf-8', errors='replace')
    assert proc.returncode == 0, ('反跑子进程本身不得崩（变异版语法必须仍合法）', out[-2000:])

    kv = {}
    for line in out.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    assert kv.get('技能数') == '2', (
        '反跑失败：删掉同名去重后技能数仍为 1，'
        '说明用例 2 抓不住去重缺失（判据假绿）', kv, out[-2000:])
    dup_descs = [kv.get('技能0_描述'), kv.get('技能1_描述')]
    assert dup_descs == ['来自 skills', '来自点skills'], (
        '变异版应同时暴露两份同名技能（先 skills/ 后 .skills/）', dup_descs, out[-2000:])

    # src 原文件全程未被修改
    assert open(SRC_SKILL_DIR, 'r', encoding='utf-8').read() == original, 'src/技能目录.light 被反跑污染'

# -*- coding: utf-8 -*-
"""T-0522（D1 + D2）判据：MCP 工具的自持叶子、技能发现的确定性顺序。

背景（新 main 遗留失败第三组：MCP 装配与技能清单渲染）：
  D1  `工具名到叶子` 缺 `mcp__*` 分支 → MCP 工具在装配层「无叶子依据」，
      `造条目表带映射` 于是给不出条目，**装配挂载集里没有 MCP 的位置**（T-0468 的
      MAP_MCP 空串即此症状）。设计口径是「MCP 工具不进具体名表，用 mcp__* 通配
      + HARNESS_MCP_TOOLS 开关决定」——通配的前提是叶子看得见它，故 MCP 工具按
      「自身即叶子」自持。
  D2  `技能目录.发现技能` 的产出顺序依赖 `os.listdir`/`readdir`（Windows NTFS 给创建序、
      zeta 先建就给 zeta；FreeBSD/zfs 又是槽位序）→ 技能段文本每次/每机不同，
      系统提示前缀漂移，直接打掉提示缓存（T-0469 的「system 前缀稳定」要求）。

本卡判据：
  A. 真挂载的 MCP 工具：`工具名到叶子(mcp__<服务器>__<工具>)` == 自身名，且该工具
     **出现在 装配挂载集 里**（这是「挂载集看不见 MCP」的直接反证）；核心工具面不受影响
     （bash 仍映射 7 个壳叶子、todo_write 仍 tool-todo —— 既有映射口径不回归）。
  B. 臆造 MCP 名（没有真实挂载、凭空塞进注册表的 mcp__ 名）仍返回 []：T-0477 / T-0491
     把「硬塞叶子」钉成反跑锚点，自持范围只对真挂载工具成立。
  C. 技能发现顺序：组序固定（主根 skills/ → 主根 .skills/ → 额外根），组内按**技能名**
     升序（不是目录名、更不是 readdir 序）；连续两次调用（发现表 / 渲染段 / 提示段）
     逐字相同。
  D. 反跑（shadow 注入变异版 技能目录.light，src 原文件全程不动）：
     把 `技能组排序` 改成原样返回 → C 的顺序断言立红，说明判据抓得住「顺序靠遍历」
     这个缺陷，不是假绿。

口径说明：判据全程走子进程（`python 运行.py <driver>`），与 T-0468/T-0478 同构，
不 import src 侧模块，避免 pytest 进程内的模块态互相污染。
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
MCP_FIXTURE = os.path.join(ROOT, 'examples', 'mcp_服务器.py')
SRC_ENTRY = os.path.join(ROOT, 'src', '总入口.light')
SRC_SKILL_DIR = os.path.join(ROOT, 'src', '技能目录.light')
SERVER_NAME = 't0498'
TIMEOUT_SEC = 240

# 会改变装配/提示结果的环境变量，判据必须自己控制（不吃宿主机真实配置）
_STRIP = (
    'HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_HOME', 'HARNESS_PRESET',
    'HARNESS_MCP_CONFIG', 'HARNESS_MCP_TOOLS', 'DSH_HOME', 'AGENTS_HOME',
    'HARNESS_PERMISSION_MODE', 'HARNESS_API_KEY', 'HARNESS_ENDPOINT',
    'HARNESS_MODEL', 'HARNESS_WEB_TOKEN', 'HARNESS_TOKEN', 'HARNESS_BIND',
)


def _env(extra=None):
    env = {k: v for k, v in os.environ.items() if k not in _STRIP}
    env['PYTHONIOENCODING'] = 'utf-8'
    if extra:
        env.update(extra)
    return env


def _run_light(source, tmp_path, name, cwd=None, extra_env=None):
    path = tmp_path / (name + '.light')
    path.write_text(source, encoding='utf-8')
    proc = subprocess.run([sys.executable, RUNNER, str(path)],
                          cwd=str(cwd or ROOT), capture_output=True, text=True,
                          timeout=TIMEOUT_SEC, env=_env(extra_env))
    out = (proc.stdout or '') + (proc.stderr or '')
    kv = {}
    for line in out.splitlines():
        if '=' in line and not line.startswith('['):
            k, v = line.split('=', 1)
            kv.setdefault(k.strip(), v.strip())
    return proc.returncode, out, kv


def _missing_module(out):
    return ('生产挂载' in out) and ('No module named' in out or 'ModuleNotFound' in out or '导入失败' in out)


def _unflat(v):
    return str(v).replace('<NL>', '\n').replace('<EQ>', '=')


def _write_mcp_json(path):
    """本仓既有 stdio fixture（examples/mcp_服务器.py，提供 echo/add 两个工具）。"""
    cfg = {
        'mcpServers': [
            {'name': SERVER_NAME, 'command': sys.executable, 'args': [MCP_FIXTURE]}
        ]
    }
    path.write_text(json.dumps(cfg), encoding='utf-8')
    return path


# ---------------------------------------------------------------------
# A + B：MCP 叶子（真挂载 → 自持；臆造名 → 无叶子）
# ---------------------------------------------------------------------

_FLAT = '''
段落 压平(文本):
  设 r 为 替换字符串(文本, "\\n", "<NL>")
  设 r 为 替换字符串(r, "=", "<EQ>")
  返回 r

段落 逗号连接(表):
  设 文本 为 ""
  设 序 为 0
  遍历 项 之 表:
    如果 序 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序 为 序 + 1
  返回 文本
'''

_DRIVER_MCP = '''从 总入口 导入 组装注册表, 工具名到叶子, 解析预设装配
从 内置核心转换 导入 转字符串
''' + _FLAT + '''
段落 主():
  设 标 为 组装注册表("standard")
  设 探测名 为 "mcp__''' + SERVER_NAME + '''__echo"
  # A：真挂载的 MCP 工具 → 自持叶子
  打印 "MAP_MCP=" + 逗号连接(工具名到叶子(探测名))
  # B：臆造名（没有真挂载）→ 无叶子依据
  打印 "MAP_GHOST=" + 转字符串(长度(工具名到叶子("mcp__ghost__tool")))
  # 既有映射口径不回归
  打印 "MAP_BASH=" + 逗号连接(工具名到叶子("bash"))
  打印 "MAP_TODO=" + 逗号连接(工具名到叶子("todo_write"))
  # MCP 工具真的进了名单
  设 名表 为 标.名单()
  打印 "STD_MCP=" + 逗号连接(名表)
  # A 的关键一环：装配挂载集里必须看得见它（叶子存在的意义就在这）
  设 装 为 解析预设装配("standard", 标)
  设 挂载 为 装[0]
  设 命中 为 0
  遍历 条 之 挂载:
    如果 条["标识"] == 探测名:
      设 命中 为 1
  打印 "IN_MOUNT=" + 转字符串(命中)
  打印 "MOUNT_COUNT=" + 转字符串(长度(挂载))
主()
'''

# 隔离 cwd：没有任何 mcp.json，验证「臆造名不因分支存在而白拿叶子」
_DRIVER_MCP_OFF = '''从 总入口 导入 组装注册表, 预设保留工具, 工具名到叶子
从 工具 导入 工具注册表, 造工具定义
从 内置核心转换 导入 转字符串
''' + _FLAT + '''
段落 假执行(参):
  设 结果 为 {"content": [["type": "text", "text": "ok"]], "isError": 假}
  返回 结果

段落 主():
  设 标 为 组装注册表("standard")
  设 表 为 新建 工具注册表()
  设 形 为 {"type": "object", "properties": {}}
  设 定义 为 造工具定义("mcp__fake__a", "假 MCP 工具", 形, 假执行)
  表.注册(定义)
  打印 "OFF_MAP=" + 转字符串(长度(工具名到叶子("mcp__fake__a")))
  预设保留工具(表, "standard")
  打印 "OFF_KEEP=" + 转字符串(表.有无("mcp__fake__a"))
主()
'''


@pytest.mark.timeout(240)
def test_真挂载MCP工具自持叶子且进挂载集(tmp_path):
    cfg = _write_mcp_json(tmp_path / 'mcp_t0498.json')
    rc, out, kv = _run_light(_DRIVER_MCP, tmp_path, 'mcp_leaf',
                             extra_env={'HARNESS_MCP_CONFIG': str(cfg)})
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    # A：自持叶子（自身即叶子）
    assert kv.get('MAP_MCP') == 'mcp__' + SERVER_NAME + '__echo', \
        ('工具名到叶子 没给真挂载的 MCP 工具自持叶子', kv.get('MAP_MCP'), out[-2000:])
    # A：装配挂载集里看得见（「MCP 工具在装配层无叶子依据」的直接反证）
    assert kv.get('IN_MOUNT') == '1', ('MCP 工具没进装配挂载集', kv.get('MOUNT_COUNT'), out[-2000:])
    # 工具确实挂着（不是靠注销换来的一致）
    assert ('mcp__' + SERVER_NAME + '__echo') in (kv.get('STD_MCP', '') or ''), out[-2000:]
    # 既有映射口径一字不变
    assert kv.get('MAP_BASH') == ('tool-bash,terminal-bash,persistent-bash,pty,'
                                  'tool-pwsh,terminal-pwsh,persistent-pwsh'), kv.get('MAP_BASH')
    assert kv.get('MAP_TODO') == 'tool-todo', kv.get('MAP_TODO')
    # B：臆造名不白拿叶子
    assert kv.get('MAP_GHOST') == '0', ('臆造 mcp__ 名不该有叶子依据（T-0477 反跑锚点）', kv, out[-2000:])


@pytest.mark.timeout(180)
def test_无配置下臆造MCP名无叶子但仍按通配保留(tmp_path):
    """D1 的两条口径并存：臆造名无叶子（T-0477/T-0491），去留仍由 mcp__* 通配决定。"""
    empty = tmp_path / 'empty_cwd'
    empty.mkdir(exist_ok=True)
    rc, out, kv = _run_light(_DRIVER_MCP_OFF, tmp_path, 'mcp_off', cwd=empty)
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    assert kv.get('OFF_MAP') == '0', ('臆造 mcp__ 名不该有叶子', kv, out[-2000:])
    assert kv.get('OFF_KEEP') == 'True', ('standard 下 MCP 工具必须按 mcp__* 通配保留', kv, out[-2000:])


def test_叶子与登记静态锚():
    """反跑锚点（静态）：删掉 MCP 分支 / 删掉挂载登记调用，上面两条动态断言立红。"""
    entry = open(SRC_ENTRY, 'r', encoding='utf-8').read()
    leaf = entry.split('段落 工具名到叶子(名字):', 1)[1].split('段落 是MCP标识', 1)[0]
    assert '开头(名字, "mcp__")' in leaf, ('工具名到叶子 缺 mcp__ 分支', leaf[:400])
    assert '返回 [名字]' in leaf.split('开头(名字, "mcp__")', 1)[1], \
        ('mcp__ 分支没返回「自身即叶子」', leaf[:600])
    assert '登记MCP挂载工具(' in entry, '组装注册表 没把真挂载的 MCP 工具名登记下来'
    body = entry.split('段落 组装注册表(', 1)[1].split('段落 ', 1)[0]
    assert '登记MCP挂载工具(' in body, ('登记必须在 组装注册表 里、紧随挂载之后', body[:600])


# ---------------------------------------------------------------------
# C：技能发现的确定性顺序
# ---------------------------------------------------------------------

_SKILL_ORDER_DRIVER = '''从 技能目录 导入 发现技能, 渲染技能清单段
从 提示_技能段 导入 技能段
从 内置核心转换 导入 转字符串
''' + _FLAT + '''
段落 名串联(表):
  设 文本 为 ""
  遍历 项 之 表:
    如果 字符串长度(文本) > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 项["名字"]
  返回 文本

段落 主():
  设 根 为 "__ROOT__"
  设 额外 为 "__EXTRA__"
  设 甲 为 发现技能(根)
  设 乙 为 发现技能(根)
  设 丙 为 发现技能(根, [额外])
  打印 "ORDER=" + 名串联(甲["技能"])
  打印 "ORDER2=" + 名串联(乙["技能"])
  打印 "ORDER_EXTRA=" + 名串联(丙["技能"])
  打印 "SAME_TABLE=" + 转字符串(甲["技能"] == 乙["技能"])
  设 段甲 为 渲染技能清单段(甲["技能"], 50)
  设 段乙 为 渲染技能清单段(乙["技能"], 50)
  打印 "SAME_RENDER=" + 转字符串(段甲 == 段乙)
  打印 "SEG=" + 压平(段甲)
  设 提示甲 为 技能段(发现技能, 根)
  设 提示乙 为 技能段(发现技能, 根)
  打印 "SAME_PROMPT=" + 转字符串(提示甲 == 提示乙)
  打印 "PROMPT=" + 压平(提示甲)
主()
'''

# 目录名与技能名故意错开：靠「遍历顺序」实现时必然给出 zeta 在前（按目录名排也一样错）
_SKILL_DIRS = [
    ('skills', 'dir_a', 'zeta'),      # 主根 skills/：dir_a 里装的是 zeta
    ('skills', 'dir_z', 'alpha'),     # 主根 skills/：dir_z 里装的是 alpha
    ('.skills', 'dir_b', 'beta'),     # 主根 .skills/（组序在主根 skills/ 之后）
]


def _mk_skill(base_dir, name, skill_name):
    d = base_dir / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'SKILL.md').write_text(
        '---\nname: %s\ndescription: %s 描述\n---\n%s 正文。\n' % (skill_name, skill_name, skill_name),
        encoding='utf-8')


def _light_path(p):
    return str(p).replace('\\', '/')


def _build_skill_tree(tmp_path):
    for group, dirname, skill_name in _SKILL_DIRS:
        _mk_skill(tmp_path / group, dirname, skill_name)
    extra = tmp_path / 'extra_root'
    _mk_skill(extra / 'skills', 'dir_c', 'omega')
    return _light_path(tmp_path), _light_path(extra)


@pytest.fixture(scope='module')
def skill_tree(tmp_path_factory):
    base = tmp_path_factory.mktemp('t0498_skills')
    return base, _build_skill_tree(base)


def test_技能发现顺序确定_组内按技能名(skill_tree):
    base, (root, extra) = skill_tree
    driver = _SKILL_ORDER_DRIVER.replace('__ROOT__', root).replace('__EXTRA__', extra)
    rc, out, kv = _run_light(driver, base, 'skill_order')
    assert rc == 0, out
    # 组序固定 + 组内按技能名（alpha/zeta 是同一组，dir_a/dir_z 的目录名序给不出这个结果）
    assert kv.get('ORDER') == 'alpha,zeta,beta', ('技能发现顺序不是「组内按技能名」', kv.get('ORDER'), out[-2000:])
    assert kv.get('ORDER_EXTRA') == 'alpha,zeta,beta,omega', \
        ('额外根必须并到主根组之后', kv.get('ORDER_EXTRA'), out[-2000:])
    # 确定性：同参两次调用，表本身与渲染文本都逐字相同
    assert kv.get('SAME_TABLE') == 'True' and kv.get('ORDER2') == kv.get('ORDER'), \
        ('两次发现结果不一致', kv.get('ORDER'), kv.get('ORDER2'))
    assert kv.get('SAME_RENDER') == 'True', '两次渲染的技能清单段不一致'
    assert kv.get('SAME_PROMPT') == 'True', '两次渲染的提示技能段不一致'
    seg = _unflat(kv.get('SEG', ''))
    lines = seg.split('\n')
    assert lines[1:] == ['- alpha：alpha 描述', '- zeta：zeta 描述', '- beta：beta 描述'], \
        ('技能行顺序/文案不对', lines, out[-2000:])
    prompt = _unflat(kv.get('PROMPT', ''))
    assert prompt.split('\n')[2:] == lines[1:], ('提示段的技能行必须与渲染层同序', prompt, out[-2000:])


# ---------------------------------------------------------------------
# D：反跑——把组内排序去掉，顺序用例必须立红（证明判据不是假绿）
# ---------------------------------------------------------------------

SORT_RETURN = '返回 排序列表(技能表, 假, 技能名键)'

_SHADOW_RUNNER = '''# -*- coding: utf-8 -*-
"""T-0522 反跑引导：把 shadow 目录插到光明导入钩子搜索路径最前后跑 driver。

用法: python t0498_shadow_runner.py <shadow_dir> <driver_path>
shadow_dir 内放变异版模块；钩子先命中 shadow，兄弟模块仍从 lightharness/src
正常解析。lightharness/src 原文件全程不动。
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


@pytest.mark.timeout(240)
def test_反跑_删组内排序_顺序用例立红(skill_tree):
    base, (root, extra) = skill_tree
    original = open(SRC_SKILL_DIR, 'r', encoding='utf-8').read()
    assert original.count(SORT_RETURN) == 1, ('反跑锚点丢失或出现多处（组内排序返回点）', SORT_RETURN)
    mutated = original.replace(SORT_RETURN, '返回 技能表', 1)

    shadow_dir = base / 'shadow'
    shadow_dir.mkdir(exist_ok=True)
    (shadow_dir / '技能目录.light').write_text(mutated, encoding='utf-8')

    runner_path = base / 't0498_shadow_runner.py'
    runner_path.write_text(_SHADOW_RUNNER.replace('__LH_ROOT__', ROOT), encoding='utf-8')
    driver_path = base / 'skill_order_shadow.light'
    driver_path.write_text(_SKILL_ORDER_DRIVER.replace('__ROOT__', root).replace('__EXTRA__', extra),
                           encoding='utf-8')

    proc = subprocess.run([sys.executable, str(runner_path), str(shadow_dir), str(driver_path)],
                          cwd=ROOT, capture_output=True, text=True, timeout=TIMEOUT_SEC, env=_env())
    out = (proc.stdout or '') + (proc.stderr or '')
    assert proc.returncode == 0, ('反跑子进程本身不得崩（变异版语法必须仍合法）', out[-2000:])
    kv = {}
    for line in out.splitlines():
        if '=' in line and not line.startswith('['):
            k, v = line.split('=', 1)
            kv.setdefault(k.strip(), v.strip())
    assert kv.get('ORDER') != 'alpha,zeta,beta', \
        ('反跑失败：去掉组内排序后顺序仍「正确」，说明顺序用例抓不住「靠遍历序」这个缺陷（判据假绿）',
         kv.get('ORDER'), out[-2000:])
    assert kv.get('ORDER') == 'zeta,alpha,beta', ('变异版应暴露目录遍历序', kv.get('ORDER'), out[-2000:])

    assert open(SRC_SKILL_DIR, 'r', encoding='utf-8').read() == original, 'src/技能目录.light 被反跑污染'

# -*- coding: utf-8 -*-
"""T-0478：提示技能清单段（接进系统提示的技能目录）判据。

对齐 hive 任务卡 T-0478：
  1. 3 个技能 → 1 行引导 + 1 行指引 + 3 行 `- 名字：描述`，且清单文案与
     技能目录.渲染技能清单段(表, 50) 完全一致（只多插指引行，不复制文案），
     并含「先用 skill 工具按名字取正文 / 不要编造」提示；
  2. 0 技能 / 非列表（字符串、空、字典）→ ""（不渲染空壳段）；
  3. 发现函数抛异常 / 返回缺 技能 键 / 技能表非列表 → 技能段 返回 ""；
  4. 51 个技能（短描述）→ 只列前 50 + 省略行，总长 ≤ 1000；
  5. 51 个技能（长描述）→ 条数逐档回退（50→45→40），总长仍 ≤ 1000；
  6. 描述 200 字 → 截到 80 码点 + `…`（复用 技能目录 实现，不复制第二份）；
  7. 描述含换行 / | / 反引号 → 换行压空格不破行、| 与 ` 反斜杠转义；
  8. 名字含 `:`、`·`、中文 → 原样保留；
  9. 技能段在场(["bash","skill"]) 真、(["bash"]) 假。

反跑（shadow 注入变异版模块，src 原文件全程不动，pytest -n 4 安全）：
  ① 删掉 提示_技能段 空表守卫（返回 "" 分支）→ 空表用例立红；
  ② 技能目录.渲染技能清单段 删描述截断 → 「80 码点 + …」用例立红；
  ③ 提示_技能段 描述清洗换直拼 → 换行破行用例立红。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SRC_SEG = os.path.join(ROOT, 'src', '提示_技能段.light')
SRC_SKILL_DIR = os.path.join(ROOT, 'src', '技能目录.light')
TIMEOUT_SEC = 150

# 反跑锚点①：提示_技能段.light 的空表守卫行（该文件内唯一）
EMPTY_GUARD = '如果 列表长度(技能表) == 0:'
# 反跑锚点②：技能目录.light 的描述截断守卫行（渲染技能清单段 内唯一）
TRUNC_GUARD = '如果 字符串长度(描) > 描述截断上限:'
# 反跑锚点③：提示_技能段.light 的描述清洗调用点（该文件内唯一）
CLEAN_CALL = '"描述": 清洗单行描述(技能["描述"])'

# 渲染技能清单段 的引导行（技能目录.light:167，同一文案锚）
LEAD_LINE = '以下技能可用：需要时用 skill 工具按名字取完整正文。'
# 首行后补的取正文指引（任务卡原文）
GUIDE_LINE = '先看这里的名字，再用 skill 工具按名字取正文；不在清单里的技能不要编造'


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


def _light_root(tmp_path):
    """把临时根路径转成 .light 字符串字面量安全形式（正斜杠，避免转义歧义）。"""
    return str(tmp_path).replace('\\', '/')


def _unflat(v):
    """driver 压平的逆操作：<NL> → 换行、<EQ> → 等号，让断言贴近真实产物。"""
    return str(v).replace('<NL>', '\n').replace('<EQ>', '=')


def _skill_md(name, desc, body):
    """好 frontmatter 的 SKILL.md 文本。"""
    return '---\nname: %s\ndescription: %s\n---\n%s' % (name, desc, body)


def _mk_skill(base_dir, name, text):
    d = base_dir / name
    d.mkdir(parents=True, exist_ok=True)
    (d / 'SKILL.md').write_text(text, encoding='utf-8')
    return d


def _build_tree_three(tmp_path):
    """主根树：skills/alpha、skills/beta、.skills/gamma 各 1 个技能。"""
    _mk_skill(tmp_path / 'skills', 'alpha', _skill_md('alpha', 'Alpha 描述', 'Alpha 正文。\n'))
    _mk_skill(tmp_path / 'skills', 'beta', _skill_md('beta', 'Beta 描述', 'Beta 正文。\n'))
    _mk_skill(tmp_path / '.skills', 'gamma', _skill_md('gamma', 'Gamma 描述', 'Gamma 正文。\n'))
    return tmp_path


def _build_extra_root(tmp_path):
    """额外根：extra_root/skills/delta 1 个技能（优先级低于主根）。"""
    extra = tmp_path / 'extra_root'
    _mk_skill(extra / 'skills', 'delta', _skill_md('delta', 'Delta 描述', 'Delta 正文。\n'))
    return str(extra).replace('\\', '/')


# ---------------------------------------------------------------------
# 公共 driver 片段
# ---------------------------------------------------------------------

_FLAT = '''
段落 压平(文本):
  设 r 为 替换字符串(文本, "\\n", "<NL>")
  设 r 为 替换字符串(r, "=", "<EQ>")
  返回 r
'''

# 技能段文本 的纯构造表全场景 driver（无文件 IO）
_DRIVER_TEXT = '''从 提示_技能段 导入 技能段文本, 技能段, 技能段在场
从 技能目录 导入 渲染技能清单段

''' + _FLAT + '''
段落 造同描表(描述文本):
  设 表 为 []
  设 k 为 1
  当 k <= 51:
    如果 k < 10:
      列表追加(表, ["名字": "s0" + 转字符串(k), "描述": 描述文本])
    否则:
      列表追加(表, ["名字": "s" + 转字符串(k), "描述": 描述文本])
    设 k 为 k + 1
  返回 表

段落 造递增表(前缀):
  设 表 为 []
  设 k 为 1
  当 k <= 51:
    如果 k < 10:
      列表追加(表, ["名字": "s0" + 转字符串(k), "描述": 前缀 + 转字符串(k)])
    否则:
      列表追加(表, ["名字": "s" + 转字符串(k), "描述": 前缀 + 转字符串(k)])
    设 k 为 k + 1
  返回 表

段落 主程():
  设 三表 为 [["名字": "alpha", "描述": "Alpha 描述"], ["名字": "beta", "描述": "Beta 描述"], ["名字": "gamma", "描述": "Gamma 描述"]]
  设 段 为 技能段文本(三表)
  打印 "段=" + 压平(段)
  设 直渲染 为 渲染技能清单段(三表, 50)
  打印 "直渲染=" + 压平(直渲染)
  打印 "空表=<" + 技能段文本([]) + ">"
  打印 "串输入=<" + 技能段文本("oops") + ">"
  打印 "空输入=<" + 技能段文本(空) + ">"
  打印 "典输入=<" + 技能段文本(["a": 1]) + ">"
  设 短表 为 造递增表("描述")
  设 短段 为 技能段文本(短表)
  打印 "短段=" + 压平(短段)
  打印 "短段长=" + 转字符串(字符串长度(短段))
  设 长表 为 造同描表("dddddddddddddd")
  设 长段 为 技能段文本(长表)
  打印 "长段=" + 压平(长段)
  打印 "长段长=" + 转字符串(字符串长度(长段))
  设 长描 为 ""
  设 k 为 0
  当 k < 200:
    设 长描 为 长描 + "字"
    设 k 为 k + 1
  打印 "截段=" + 压平(技能段文本([["名字": "longy", "描述": 长描]]))
  打印 "脏段=" + 压平(技能段文本([["名字": "dirty", "描述": "第一行\\n第二行|管`引"]]))
  打印 "名段=" + 压平(技能段文本([["名字": "a:b·中文名", "描述": "普通描述"]]))
  打印 "在场mix=" + 转字符串(技能段在场(["bash", "skill"]))
  打印 "在场无=" + 转字符串(技能段在场(["bash"]))
  打印 "在场空=" + 转字符串(技能段在场([]))
  打印 "在场取用=" + 转字符串(技能段在场(["技能取用"]))
  打印 "在场列表=" + 转字符串(技能段在场(["技能列表"]))
  打印 "在场串=" + 转字符串(技能段在场("skill"))
主程()
'''

# 技能段 的端到端 driver（真发现 + 额外目录 + 抛错 / 异常返回）
_DRIVER_WIRE = '''从 提示_技能段 导入 技能段文本, 技能段, 技能段在场
从 技能目录 导入 发现技能

''' + _FLAT + '''
段落 会炸的发现(根, 额外目录表):
  抛出 新建 错误("发现函数炸了")

段落 缺键发现(根, 额外目录表):
  返回 ["跳过": []]

段落 坏表发现(根, 额外目录表):
  返回 ["技能": "oops", "跳过": []]

段落 主程():
  设 根 为 "__ROOT__"
  设 段 为 技能段(发现技能, 根)
  打印 "端段=" + 压平(段)
  设 额外段 为 技能段(发现技能, 根, ["__EXTRA__"])
  打印 "额外段=" + 压平(额外段)
  打印 "炸段=<" + 技能段(会炸的发现, 根) + ">"
  打印 "缺键段=<" + 技能段(缺键发现, 根) + ">"
  打印 "坏表段=<" + 技能段(坏表发现, 根) + ">"
主程()
'''

# 反跑小 driver：单场景聚焦（空表 / 200 字截断 / 脏描述）
_DRIVER_EMPTY = '''从 提示_技能段 导入 技能段文本

''' + _FLAT + '''
段落 主程():
  打印 "空表=<" + 技能段文本([]) + ">"
  打印 "三表长=" + 转字符串(字符串长度(技能段文本([["名字": "a", "描述": "d"]])))
主程()
'''

_DRIVER_TRUNC = '''从 提示_技能段 导入 技能段文本

''' + _FLAT + '''
段落 主程():
  设 长描 为 ""
  设 k 为 0
  当 k < 200:
    设 长描 为 长描 + "字"
    设 k 为 k + 1
  打印 "截段=" + 压平(技能段文本([["名字": "longy", "描述": 长描]]))
主程()
'''

_DRIVER_DIRTY = '''从 提示_技能段 导入 技能段文本

''' + _FLAT + '''
段落 主程():
  打印 "脏段=" + 压平(技能段文本([["名字": "dirty", "描述": "第一行\\n第二行|管`引"]]))
主程()
'''


# ---------------------------------------------------------------------
# 判据 1：3 个技能 → 1 行引导 + 1 行指引 + 3 行 `- 名字：描述`，与渲染层同一文案
# ---------------------------------------------------------------------

def test_三技能段文本_引导指引与技能行(tmp_path):
    rc, out, kv = _run(_DRIVER_TEXT, tmp_path, 't0478_j1.light')
    assert rc == 0, out
    seg = _unflat(kv.get('段', ''))
    direct = _unflat(kv.get('直渲染', ''))
    lines = seg.split('\n')
    direct_lines = direct.split('\n')
    assert len(lines) == 5, ('判据 1：应为 1 引导 + 1 指引 + 3 技能行 = 5 行', lines, out)
    assert lines[0] == LEAD_LINE, ('首行必须是渲染层同一引导行', lines[0], out)
    assert lines[1] == GUIDE_LINE, ('首行后必须紧跟取正文指引', lines[1], out)
    assert lines[2:] == direct_lines[1:], ('技能行必须与 渲染技能清单段(表,50) 完全一致（不复制文案）', lines[2:], out)
    assert '- alpha：Alpha 描述' in lines[2], ('判据 1：应含 `- 名字：描述` 行', lines[2], out)
    assert '- beta：Beta 描述' in lines[3], ('判据 1：应含 `- 名字：描述` 行', lines[3], out)
    assert '- gamma：Gamma 描述' in lines[4], ('判据 1：应含 `- 名字：描述` 行', lines[4], out)
    assert 'skill 工具按名字取正文' in seg and '不要编造' in seg, ('应含「先用 skill 取正文 / 不要编造」提示', seg, out)


# ---------------------------------------------------------------------
# 判据 2：空表 / 非列表 → ""
# ---------------------------------------------------------------------

def test_空表与非列表返回空串(tmp_path):
    rc, out, kv = _run(_DRIVER_TEXT, tmp_path, 't0478_j2.light')
    assert rc == 0, out
    assert kv.get('空表') == '<>', ('0 技能必须返回空串（反跑①锚）', kv.get('空表'), out)
    assert kv.get('串输入') == '<>', ('字符串输入（非列表）应返回空串', kv.get('串输入'), out)
    assert kv.get('空输入') == '<>', ('空（None）输入应返回空串', kv.get('空输入'), out)
    assert kv.get('典输入') == '<>', ('字典输入（非列表）应返回空串', kv.get('典输入'), out)


# ---------------------------------------------------------------------
# 判据 3：技能段 端到端——真发现 + 额外目录表
# ---------------------------------------------------------------------

def test_技能段端到端_真发现与额外目录(tmp_path):
    root = _build_tree_three(tmp_path)
    extra = _build_extra_root(tmp_path)
    driver = _DRIVER_WIRE.replace('__ROOT__', _light_root(root)).replace('__EXTRA__', extra)
    rc, out, kv = _run(driver, tmp_path, 't0478_j3.light')
    assert rc == 0, out
    seg = _unflat(kv.get('端段', ''))
    lines = seg.split('\n')
    assert len(lines) == 5, ('主根 3 技能应为 1 引导 + 1 指引 + 3 行', lines, out)
    assert lines[0] == LEAD_LINE and lines[1] == GUIDE_LINE, ('引导 + 指引两行头部缺失', lines[:2], out)
    assert '- alpha：Alpha 描述' in lines[2] and '- beta：Beta 描述' in lines[3] \
        and '- gamma：Gamma 描述' in lines[4], ('3 行技能清单不齐', lines[2:], out)
    eseg = _unflat(kv.get('额外段', ''))
    elines = eseg.split('\n')
    assert len(elines) == 6, ('主根 3 + 额外根 1 = 4 技能行', elines, out)
    assert '- delta：Delta 描述' in elines[5], ('额外目录表技能应被并入清单末尾', elines[5], out)


# ---------------------------------------------------------------------
# 判据 3 续：发现抛异常 / 缺键 / 技能表非列表 → ""
# ---------------------------------------------------------------------

def test_发现抛错与异常返回得空段(tmp_path):
    root = _build_tree_three(tmp_path)
    driver = _DRIVER_WIRE.replace('__ROOT__', _light_root(root)).replace('__EXTRA__', 'x')
    rc, out, kv = _run(driver, tmp_path, 't0478_j4.light')
    assert rc == 0, out
    assert kv.get('炸段') == '<>', ('发现函数抛错必须返回空串（不拖垮一轮）', kv.get('炸段'), out)
    assert kv.get('缺键段') == '<>', ('发现结果缺 技能 键应返回空串', kv.get('缺键段'), out)
    assert kv.get('坏表段') == '<>', ('技能表非列表应返回空串', kv.get('坏表段'), out)


# ---------------------------------------------------------------------
# 判据 4：51 个技能（短描述）→ 只列前 50 + 省略行，总长 ≤ 1000
# ---------------------------------------------------------------------

def test_五十一技能只列前五十带省略行(tmp_path):
    rc, out, kv = _run(_DRIVER_TEXT, tmp_path, 't0478_j5.light')
    assert rc == 0, out
    seg = _unflat(kv.get('短段', ''))
    assert '- s50：描述50' in seg, ('第 50 条应保留', seg, out)
    assert '- s51：' not in seg, ('第 51 条必须被裁掉', seg, out)
    assert '仅列前 50 个' in seg, ('超限应有省略提示行', seg, out)
    total = int(kv.get('短段长', '0'))
    assert 0 < total <= 1000, ('判据 4：总长必须 ≤ 1000', total, out)


# ---------------------------------------------------------------------
# 判据 5：51 个技能（长描述）→ 条数逐档回退（50→45→40），总长 ≤ 1000
# ---------------------------------------------------------------------

def test_超长描述逐档回退保总长(tmp_path):
    rc, out, kv = _run(_DRIVER_TEXT, tmp_path, 't0478_j6.light')
    assert rc == 0, out
    seg = _unflat(kv.get('长段', ''))
    total = int(kv.get('长段长', '0'))
    assert 0 < total <= 1000, ('判据 5：回退后总长必须 ≤ 1000', total, out)
    assert '- s01：' in seg, ('回退不得裁掉第一条', seg, out)
    # 长描述（14 码点/条）下 50 档 ≈ 1140、45 档 ≈ 1035 均超限，40 档 ≈ 930 达标
    assert '- s40：' in seg, ('应回退到 40 条档（s40 保留）', seg, out)
    assert '- s41：' not in seg, ('40 条档下 s41 必须被裁', seg, out)
    assert '仅列前 40 个' in seg, ('回退档省略行应写 40', seg, out)
    assert '仅列前 50 个' not in seg, ('不得停留在 50 档（总长会超限）', seg, out)


# ---------------------------------------------------------------------
# 判据 6：描述 200 字 → 截到 80 码点 + `…`（复用 技能目录 实现）
# ---------------------------------------------------------------------

def test_描述两百字截到八十加省略号(tmp_path):
    rc, out, kv = _run(_DRIVER_TEXT, tmp_path, 't0478_j7.light')
    assert rc == 0, out
    seg = _unflat(kv.get('截段', ''))
    assert '- longy：' + '字' * 80 + '…' in seg, ('超长描述应按码点截断到 80 并加省略号', seg, out)
    assert '字' * 81 not in seg, ('截断后不得残留 81 个字', seg, out)


# ---------------------------------------------------------------------
# 判据 7：描述含换行 / | / 反引号 → 不破行、| 与 ` 被转义
# ---------------------------------------------------------------------

def test_脏描述换行压平竖线反引号转义(tmp_path):
    rc, out, kv = _run(_DRIVER_TEXT, tmp_path, 't0478_j8.light')
    assert rc == 0, out
    flat = kv.get('脏段', '')
    assert '第一行<NL>' not in flat, ('描述内换行必须被压平（不得破清单行结构）', flat, out)
    seg = _unflat(flat)
    assert '- dirty：第一行 第二行\\|管\\`引' in seg, ('换行压空格、| 与 ` 应反斜杠转义', seg, out)


# ---------------------------------------------------------------------
# 判据 8：名字含 : · 中文 → 原样保留
# ---------------------------------------------------------------------

def test_名字含冒号间隔号中文原样保留(tmp_path):
    rc, out, kv = _run(_DRIVER_TEXT, tmp_path, 't0478_j9.light')
    assert rc == 0, out
    seg = _unflat(kv.get('名段', ''))
    assert '- a:b·中文名：普通描述' in seg, ('名字特殊字符应原样保留', seg, out)


# ---------------------------------------------------------------------
# 判据 9：技能段在场
# ---------------------------------------------------------------------

def test_技能段在场判定(tmp_path):
    rc, out, kv = _run(_DRIVER_TEXT, tmp_path, 't0478_j10.light')
    assert rc == 0, out
    yes = ('True', '真')
    no = ('False', '假')
    assert kv.get('在场mix') in yes, ('skill 在场应为真', kv.get('在场mix'), out)
    assert kv.get('在场取用') in yes, ('技能取用 在场应为真', kv.get('在场取用'), out)
    assert kv.get('在场列表') in yes, ('技能列表 在场应为真', kv.get('在场列表'), out)
    assert kv.get('在场无') in no, ('只有 bash 应为假', kv.get('在场无'), out)
    assert kv.get('在场空') in no, ('空工具表应为假', kv.get('在场空'), out)
    assert kv.get('在场串') in no, ('非列表工具表应为假', kv.get('在场串'), out)


# ---------------------------------------------------------------------
# 反跑公共设施（照 T-0451 shadow 注入模式：无写回-还原竞态，pytest -n 4 安全）
# ---------------------------------------------------------------------

_SHADOW_RUNNER = '''# -*- coding: utf-8 -*-
"""T-0478 反跑引导：把 shadow 目录插到光明导入钩子搜索路径最前后跑 driver。

用法: python t0478_shadow_runner.py <shadow_dir> <driver_path>
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


def _shadow_run(tmp_path, shadow_module, mutated, driver_text, work_name):
    """shadow 注入变异版模块跑 driver，返回 (kv, out)。"""
    shadow_dir = tmp_path / 'shadow'
    shadow_dir.mkdir(exist_ok=True)
    (shadow_dir / shadow_module).write_text(mutated, encoding='utf-8')

    runner_path = tmp_path / ('%s_runner.py' % work_name)
    runner_path.write_text(_SHADOW_RUNNER.replace('__LH_ROOT__', ROOT), encoding='utf-8')
    driver_path = tmp_path / ('%s.light' % work_name)
    driver_path.write_text(driver_text, encoding='utf-8')

    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, str(runner_path), str(shadow_dir), str(driver_path)],
                          cwd=ROOT, capture_output=True, timeout=TIMEOUT_SEC, env=env)
    out = proc.stdout.decode('utf-8', errors='replace') + proc.stderr.decode('utf-8', errors='replace')
    assert proc.returncode == 0, ('反跑子进程本身不得崩（变异版语法必须仍合法）', out[-2000:])
    kv = {}
    for line in out.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return kv, out


# ---------------------------------------------------------------------
# 反跑①：删掉空表守卫 → 空表用例立红
# ---------------------------------------------------------------------

def test_反跑_删空表守卫_空表用例立红(tmp_path):
    original = open(SRC_SEG, 'r', encoding='utf-8').read()
    assert original.count(EMPTY_GUARD) == 1, \
        ('反跑锚点丢失或出现多处（空表守卫行）', EMPTY_GUARD)
    mutated = original.replace(EMPTY_GUARD, '如果 假:', 1)

    kv, out = _shadow_run(tmp_path, '提示_技能段.light', mutated, _DRIVER_EMPTY, 't0478_m1')
    assert kv.get('空表') != '<>', \
        ('反跑失败：删掉空表守卫后空表仍返回空串，说明「0 技能 → 空」用例抓不住该缺陷（判据假绿）', kv, out[-2000:])
    assert kv.get('三表长', '0') != '0' and int(kv.get('三表长', '0')) > 0, \
        ('变异不得破坏正常路径（非空表仍应渲染）', kv, out[-2000:])

    assert open(SRC_SEG, 'r', encoding='utf-8').read() == original, 'src/提示_技能段.light 被反跑污染'


# ---------------------------------------------------------------------
# 反跑②：渲染层删描述截断 → 「80 码点 + …」用例立红
# ---------------------------------------------------------------------

def test_反跑_渲染层删描述截断_八十截断用例立红(tmp_path):
    original = open(SRC_SKILL_DIR, 'r', encoding='utf-8').read()
    assert original.count(TRUNC_GUARD) == 1, \
        ('反跑锚点丢失或出现多处（描述截断守卫行）', TRUNC_GUARD)
    mutated = original.replace(TRUNC_GUARD, '如果 假:', 1)

    kv, out = _shadow_run(tmp_path, '技能目录.light', mutated, _DRIVER_TRUNC, 't0478_m2')
    flat = kv.get('截段', '')
    assert ('- longy：' + '字' * 80 + '…') not in flat, \
        ('反跑失败：渲染层删掉截断后 80+… 断言仍成立，说明截断用例抓不住截断缺失（判据假绿）', flat[-300:], out[-2000:])
    assert '字' * 200 in flat, ('变异版应暴露未截断的 200 字描述', flat[-300:], out[-2000:])

    assert open(SRC_SKILL_DIR, 'r', encoding='utf-8').read() == original, 'src/技能目录.light 被反跑污染'


# ---------------------------------------------------------------------
# 反跑③：描述清洗换直拼 → 换行破行用例立红
# ---------------------------------------------------------------------

def test_反跑_清洗换直拼_破行用例立红(tmp_path):
    original = open(SRC_SEG, 'r', encoding='utf-8').read()
    assert original.count(CLEAN_CALL) == 1, \
        ('反跑锚点丢失或出现多处（描述清洗调用点）', CLEAN_CALL)
    mutated = original.replace(CLEAN_CALL, '"描述": 技能["描述"]', 1)

    kv, out = _shadow_run(tmp_path, '提示_技能段.light', mutated, _DRIVER_DIRTY, 't0478_m3')
    flat = kv.get('脏段', '')
    assert '第一行<NL>' in flat, \
        ('反跑失败：清洗换直拼后换行仍不破行，说明破行用例抓不住清洗缺失（判据假绿）', flat, out[-2000:])

    assert open(SRC_SEG, 'r', encoding='utf-8').read() == original, 'src/提示_技能段.light 被反跑污染'

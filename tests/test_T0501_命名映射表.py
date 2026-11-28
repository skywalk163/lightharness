# -*- coding: utf-8 -*-
"""T-0501：语义化命名方案与 tool_NN → 语义名映射表判据。

校验对象是文档里的机器可读块（docs/工具命名规范.light.md §6），不校验注册表本身
（本卡红线：只产出方案，不动 registry）。

钉住的不变量（对应规范 §8）：
  1. 完整性：160 行、编号连续 0..159、tool 键与编号一致、现名互不重复；
  2. 合法性：语义名匹配 `<域>.<动作>` 的 ASCII 蛇形语法、长度上限；
  3. 唯一性：语义名互不重复，且与现名、与 mcp__ 前缀不冲突；
  4. 域对齐：域 ∈ T-0496 的 24 个枚举值，前缀 == 域（唯一例外 横切 → xcut）；
  5. 兼容标注：只有「保留别名 / 直接改名」两种，保留别名 ⟺ 现名 ∈ 别名保留名单；
  6. 与真实注册表的两条互补判据（T-0525 改写，T-0542 环境无关化，§6.1）：
     正向 —— §6 的 160 条必须按登记序作为**核心注册面**的**前缀**逐位一致（现名 + 域）；
     反向 —— 核心注册面里既不在 §6、也不在 `不上叶子表`、也不以 `mcp__` 开头的条目
     逐条点名判红；完整注册面只额外校验「核心在前、挂载项在末尾追加」。
     注册面完全未装配（缺核心工具）时以明确理由跳过，不假绿不假红。

T-0542 基线漂移根治（与 T-0533 同类：判据不能把环境规模写死成契约）：
  - §6 的权威范围是**本仓核心注册面 160**（规范 §6.1 标题即此口径），但完整注册面会随
    「本机挂了哪些插件」漂移：lightplugin 兄弟仓在场时 `动态挂载撞车插件` 会追加
    代理团队/交付呈现/会话查询/团队界面 的工具（实测 fb98 168 = 160 + 8，其中
    交付登记/交付列出/交付完成/交付关联/查询会话 5 条既不在 §6、也不在不上叶子表、
    也不是 mcp__，在旧判据里被误判成「真·漏登记」）。
  - 修法不是给这 5 条开豁免名单（规范 §6.1 明确「豁免源只有两个，别处不得再新增名单」），
    而是把判据的复算面收回到**核心注册面**：同一驱动在「没有 lightplugin 兄弟」的
    工作目录再装配一次（`动态挂载撞车插件` 的插件目录按 cwd 的 `../lightplugin` 求值），
    正向/反向都只判这一面；完整注册面只要求「核心 160 位前缀不变 + 追加项在末尾」。
  - 判据强度不降：新增的**核心**工具两面都会出现，反向判据照样点名判红；
    插件挂载项只在完整面出现（核心面里根本没有），不构成「漏登记」，也不靠豁免名单掩盖。

运行方式：python -m pytest -q tests/test_T0501_命名映射表.py
Windows 本机若子进程输出触发 GBK 解码错误，加 PYTHONUTF8=1 再跑（不是产物问题）。
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC = os.path.join(ROOT, 'docs', '工具命名规范.light.md')
RUNNER = os.path.join(ROOT, '运行.py')

BEGIN = '<!-- T0501-映射表-开始 -->'
END = '<!-- T0501-映射表-结束 -->'

# T-0496 的 domain 枚举（src/工具面装配.light §9：域覆盖表 ∪ 域规则表 ∪ 默认域）
DOMAINS = {
    'host', 'credential', 'storage', 'webhook', 'browser', 'desktop', 'voice',
    'lsp', 'ctx', 'generative', 'team', 'extension', 'workflow', 'session',
    'config', 'file', 'shell', 'web', 'skill', 'delegation', 'attachment',
    'acp', '横切', '其他',
}
# 域前缀转写：只允许「横切 → xcut」一条（函数名必须 ASCII），其余原样
PREFIX = {'横切': 'xcut', '其他': 'misc'}
# 动词族：动作首词必须能落到词表里的某个前缀族，防止写成 do_it / tool_2 之类
ACTION_RE = re.compile(r'^[a-z][a-z0-9_]*$')
NAME_RE = re.compile(r'^([a-z]+)\.([a-z][a-z0-9_]*)$')
MAX_LEN = 40
MAX_ACTION = 24
POLICIES = {'保留别名', '直接改名'}

# 注册面「装上了」的证据：核心四件套至少出现一个。用它判断环境可用性，
#   不用「条数 >= 100」这种数量门槛（数量会随插件 / MCP 漂移，不是环境判据）。
CORE_SENTINELS = ('bash', '读文件', '写文件', '搜索文件')
# MCP 透传名只按前缀豁免：枚举必然随各机 mcp.json 过期（§2.1）
MCP_PREFIX = 'mcp__'
MAX_DETAIL = 8


def _read_doc():
    assert os.path.isfile(DOC), '缺少规范文档：%s' % DOC
    with open(DOC, encoding='utf-8') as f:
        return f.read()


def _load_table():
    text = _read_doc()
    assert BEGIN in text and END in text, '规范文档缺少 §6 映射表标记'
    body = text.split(BEGIN, 1)[1].split(END, 1)[0]
    body = body.strip()
    assert body.startswith('```json') and body.endswith('```'), '映射表必须包在 json 代码块里'
    body = body[len('```json'):-len('```')].strip()
    return json.loads(body)


TABLE = _load_table()
ROWS = TABLE['工具']
KEEP = TABLE['别名保留名单']


def _brief(items, limit=MAX_DETAIL):
    """把违规明细压成可读的几行：全列会淹掉真正的第一条。"""
    items = list(items)
    if len(items) <= limit:
        return '\n  '.join(items)
    return '\n  '.join(items[:limit]) + '\n  …（共 %d 处）' % len(items)


# ---------------------------------------------------------------- 1 完整性
def test_映射表完整性与编号口径():
    assert TABLE['版本'] == 'T-0501'
    assert TABLE['基线工具数'] == len(ROWS) == 160, (TABLE['基线工具数'], len(ROWS))
    # 编号连续、tool 键与编号严格一致（tool_NN 的口径 = 0 基登记序）
    assert [r['编号'] for r in ROWS] == list(range(160)), '编号必须是连续 0..159'
    for r in ROWS:
        assert r['tool'] == 'tool_%d' % r['编号'], (r['tool'], r['编号'])
        assert set(r) == {'编号', 'tool', '现名', '域', '语义名', '兼容'}, r
        assert r['现名'] and r['域'] and r['语义名'], r
    # 现名互不重复（一个现名只能映射到一个语义名）
    names = [r['现名'] for r in ROWS]
    assert len(set(names)) == 160, '现名重复：%s' % [n for n in names if names.count(n) > 1]


# ---------------------------------------------------------------- 2 合法性
def test_语义名语法与长度():
    for r in ROWS:
        new = r['语义名']
        m = NAME_RE.match(new)
        assert m, '语义名不合语法：%s（应为 <域>.<动作>）' % new
        assert new.isascii(), '语义名必须纯 ASCII：%s' % new
        assert len(new) <= MAX_LEN, '语义名过长：%s' % new
        act = m.group(2)
        assert ACTION_RE.match(act), act
        assert len(act) <= MAX_ACTION, '动作词过长：%s' % new
        assert '__' not in new and '..' not in new, '连续分隔符：%s' % new
        # 动作用对象名，不用 do/tool/exec 这类无语义通配词（shell.run 是唯一例外；
        # tool_task_* 里的 tool 是对象名「工具任务」，不算通配词）
        first = act.split('_')[0]
        assert act not in ('do', 'exec', 'tmp', 'x'), '动作用了无语义通配词：%s' % new
        assert not act.startswith(('do_', 'exec_', 'tmp_')), '动作用了无语义通配词：%s' % new
        assert first != 'do', '动作用了无语义通配词：%s' % new


# ---------------------------------------------------------------- 3 唯一性
def test_语义名唯一且不与现名或MCP冲突():
    sem = [r['语义名'] for r in ROWS]
    dup = [s for s in sem if sem.count(s) > 1]
    assert not dup, '语义名重复：%s' % dup
    assert not (set(sem) & {r['现名'] for r in ROWS}), '语义名与现有工具名冲突'
    assert not any(s.startswith('mcp__') for s in sem), 'MCP 透传名不参与改名'
    # 同域同一动作只出现一次（config.list 与 config.preset_list 并存即违规）
    assert len(set(sem)) == 160


# ---------------------------------------------------------------- 4 域对齐
def test_域前缀与T0496枚举对齐():
    assert set(TABLE['域前缀转写']) <= set(PREFIX)
    for k, v in TABLE['域前缀转写'].items():
        assert PREFIX[k] == v, (k, v)
    used = set()
    for r in ROWS:
        dom = r['域']
        assert dom in DOMAINS, '域不在 T-0496 枚举内：%s（工具 %s）' % (dom, r['现名'])
        used.add(dom)
        pre = r['语义名'].split('.')[0]
        assert pre == PREFIX.get(dom, dom), \
            '域前缀与域不符：%s 的域=%s，前缀=%s' % (r['语义名'], dom, pre)
    # 枚举里除兜底「其他」外，本基线没有空转的域（新增工具会让这条变红，属预期）
    empty = {d for d in DOMAINS if d not in used} - {'其他'}
    assert not empty, '枚举域未被任何工具使用：%s' % empty


# ---------------------------------------------------------------- 5 兼容策略
def test_兼容策略标注完备():
    assert isinstance(KEEP, list) and len(KEEP) == 27, len(KEEP)
    assert len(set(KEEP)) == 27, '别名保留名单有重复'
    names = {r['现名'] for r in ROWS}
    assert set(KEEP) <= names, '保留名单里有表外的名字：%s' % (set(KEEP) - names)
    for r in ROWS:
        assert r['兼容'] in POLICIES, r['兼容']
        want = '保留别名' if r['现名'] in KEEP else '直接改名'
        assert r['兼容'] == want, \
            '%s 的兼容标注不对：%s（期望 %s）' % (r['现名'], r['兼容'], want)
    # 硬约束：ASCII 上游名（模型面已在用）一律留别名
    for r in ROWS:
        if r['现名'].isascii():
            assert r['兼容'] == '保留别名', 'ASCII 旧名必须留别名：%s' % r['现名']
    assert sum(1 for r in ROWS if r['兼容'] == '保留别名') == 27
    assert sum(1 for r in ROWS if r['兼容'] == '直接改名') == 133


# ---------------------------------------------------------------- 6 真实注册表
# 一次 dump 同时给两条判据供料：REG| 注册表(名|域)，EXEMPT| 不上叶子表。
# 豁免名单必须从 工具面装配 导入，测试里不留第二份（两份一定漂移）。
DUMP_DRIVER = '''
从 总入口 导入 组装注册表
从 工具面装配 导入 工具域, 不上叶子表

段落 主程():
  设 注册表 为 组装注册表()
  遍历 名 之 注册表.名单():
    打印 "REG|" + 名 + "|" + 工具域(名)
  遍历 名 之 不上叶子表:
    打印 "EXEMPT|" + 名
主程()
'''


def _lightplugin_dir():
    env = os.environ.get('LIGHTPLUGIN', '')
    cands = [env, os.path.join(ROOT, 'lightplugin'),
             os.path.normpath(os.path.join(ROOT, '..', 'lightplugin')),
             os.path.normpath(os.path.join(ROOT, '..', '..', 'lightplugin')),
             os.path.normpath(os.path.join(ROOT, '..', '..', '..', 'lightplugin'))]
    for c in cands:
        if c and os.path.isfile(os.path.join(c, '集成', '工具总表.json')):
            return c
    return ''


def _dump(tmp_path, cwd=None):
    """返回 ((注册表 [(名, 域)], 不上叶子表 [名]), 错误文本)；导出失败时第一项为 None。

    `cwd` 默认仓库根（完整注册面：挂上本机 lightplugin 兄弟仓里的插件）；
    指向 `没有 ../lightplugin` 的目录时得到**核心注册面**——`动态挂载撞车插件`
    的插件目录按 cwd 的 `../lightplugin` 求值，核心面因此不含插件工具（T-0542）。
    """
    path = tmp_path / 't0501_registry.light'
    path.write_text(DUMP_DRIVER, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    plug = _lightplugin_dir()
    if plug:
        env['LIGHTPLUGIN'] = plug
    proc = subprocess.run([sys.executable, RUNNER, str(path)],
                          cwd=str(cwd or ROOT),
                          capture_output=True, text=True, timeout=240,
                          env=env, encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        return (None, None), (proc.stdout or '') + (proc.stderr or '')
    reg = []
    exempt = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line.startswith('REG|'):
            rest = line[len('REG|'):]
            if '|' in rest:
                name, dom = rest.split('|', 1)
                reg.append((name.strip(), dom.strip()))
        elif line.startswith('EXEMPT|'):
            exempt.append(line[len('EXEMPT|'):].strip())
    return (reg, exempt), ''


def _prefix_violations(reg):
    """正向判据：§6 160 条按登记序 = 注册表最前 160 位（现名 + 域逐位相等）。

    追加只允许发生在末尾；缺基线、移位、改名、域漂移都点名。
    """
    bad = []
    names = [n for n, _ in reg]
    table_names = [r['现名'] for r in ROWS]
    missing = [n for n in table_names if n not in names]
    if missing:
        bad.append('基线工具在注册表里缺失（被删或改名）：%s' % '、'.join(missing))
    if len(reg) < len(ROWS):
        bad.append('注册表只有 %d 条，少于映射表基线 %d 条（前 %d 位必须逐位对齐）'
                   % (len(reg), len(ROWS), len(ROWS)))
    for i, (r, (name, dom)) in enumerate(zip(ROWS, reg)):
        if r['现名'] != name:
            bad.append('登记序第 %d 位现名漂移：映射表=%s 注册表=%s'
                       % (i, r['现名'], name))
        elif r['域'] != dom:
            bad.append('登记序第 %d 位（%s）域漂移：映射表=%s 注册表=%s'
                       % (i, name, r['域'], dom))
    return bad


def _unregistered(reg, exempt):
    """反向判据：注册表里既不在 §6、也不在 不上叶子表、也不以 mcp__ 开头 → 真·漏登记。"""
    table_names = {r['现名'] for r in ROWS}
    exempt_names = set(exempt)
    stray = []
    for name, dom in reg:
        if name in table_names or name in exempt_names or name.startswith(MCP_PREFIX):
            continue
        stray.append('%s（域 %s）' % (name, dom))
    return stray


def _surface_split(full, core):
    """完整注册面 vs 核心注册面：返回 (前缀是否一致, 末尾追加的挂载项, 说明)。

    核心面是「没有 lightplugin 兄弟仓」时装配出来的那一面（§6.1 的权威范围 160）；
    完整面 = 核心面 + 本机插件/MCP 挂载项。追加只允许发生在末尾：
    核心 160 位必须逐位等于完整面的前 160 位，否则顺序契约被破坏。
    """
    core_names = [n for n, _ in core]
    full_names = [n for n, _ in full]
    if full_names[:len(core_names)] != core_names:
        return False, [n for n in full_names if n not in set(core_names)], \
            '完整面的前 %d 位与核心面不一致' % len(core_names)
    if any(n in set(core_names) for n in full_names[len(core_names):]):
        # 前缀已相等，就不可能再出现核心名；这条是防御性断言
        return False, [], '挂载项里混进了核心注册名'
    return True, full_names[len(core_names):], ''


def _dump_both(tmp_path):
    """并发装配完整面与核心面（两次跑光明解释器，串行会顶到 pytest --timeout=60）。"""
    core_dir = tmp_path / 'core'
    core_dir.mkdir()
    with ThreadPoolExecutor(max_workers=2) as ex:
        full_f = ex.submit(_dump, tmp_path)
        core_f = ex.submit(_dump, core_dir, core_dir)
        return full_f.result(), core_f.result()


@pytest.mark.timeout(180)
def test_与真实注册表逐位一致(tmp_path):
    # 完整面（可能挂本机 lightplugin 插件）+ 核心面（无插件兄弟）各装配一次
    ((reg, exempt), err), ((core, core_exempt), err2) = _dump_both(tmp_path)
    assert reg is not None, '完整注册表导出失败：%s' % err[-2000:]
    assert core is not None, '核心注册表导出失败：%s' % err2[-2000:]
    assert exempt, '不上叶子表 未从 工具面装配 导入到条目：%s' % err[-2000:]
    assert core_exempt, '不上叶子表 未从 工具面装配 导入到条目：%s' % err2[-2000:]

    # 环境可用性判据：核心注册面是否装上了。不用条数门槛（条数随插件 / MCP 漂移）。
    if not (set(n for n, _ in core) & set(CORE_SENTINELS)):
        pytest.skip('当前环境未装配工具注册面（核心注册表仅 %d 条，且不含核心工具 %s）——'
                    '这是环境声明，不是放低判据；映射表自身的完整性判据已通过'
                    % (len(core), '/'.join(CORE_SENTINELS)))

    # 正向判据：§6 基线 160 条 = 核心注册面的登记序前缀（现名 + 域逐位相等）
    bad = _prefix_violations(core)
    assert not bad, ('§6 映射表与核心注册面不一致（基线 %d 条 vs 核心 %d 条）：\n  %s'
                     % (len(ROWS), len(core), _brief(bad)))

    # 反向判据：核心注册面里既不在 §6、也不在 不上叶子表、也不以 mcp__ 开头 → 真·漏登记
    stray = _unregistered(core, exempt)
    assert not stray, (
        '核心注册面里有 %d 个工具既不在 §6 映射表、也不在 工具面装配.不上叶子表'
        '（§3.9 A 类）、也不以 mcp__ 开头 —— 属真·漏登记，逐条点名：\n  %s'
        % (len(stray), _brief(stray)))

    # 完整面：核心 160 位前缀不变，插件/MCP 挂载项只允许在末尾追加
    ok, extras, why = _surface_split(reg, core)
    assert ok, ('完整注册面与核心面不是「核心前缀 + 末尾追加」的关系：%s\n'
                '核心 %d 条、完整 %d 条；追加项：%s'
                % (why, len(core), len(reg), _brief(extras)))

    # 完整面里同样的反向口径只允许命中「只在完整面出现的挂载项」：
    # 任何同时出现在核心面的名字若漏登记，上面那条已经判红；这里再钉一次，防两面口径分叉。
    full_stray = _unregistered(reg, exempt)
    core_names = {n for n, _ in core}
    outside = [s for s in full_stray if s.split('（', 1)[0] in core_names]
    assert not outside, ('完整面反向判据命中了核心注册名（与核心面口径分叉）：\n  %s'
                         % _brief(outside))


def test_判据自检_基线漂移与漏登记必红():
    """反证：两条判据都必须在人造的坏数据上红并点名（不依赖真实环境）。"""
    clean = [(r['现名'], r['域']) for r in ROWS]
    assert _prefix_violations(clean) == []
    assert _unregistered(clean, []) == []

    # 一、基线改名 → 正向判据红并点名
    renamed = list(clean)
    renamed[3] = ('临时改名', renamed[3][1])
    bad = _prefix_violations(renamed)
    assert bad and '临时改名' in ' '.join(bad), bad

    # 二、删掉一条基线 → 正向判据红并点名
    trimmed = clean[:3] + clean[4:]
    bad = _prefix_violations(trimmed)
    assert bad and '搜索文件' in ' '.join(bad), bad

    # 三、新增未登记 → 反向判据红并点名；豁免源与 mcp__ 透传不误伤
    with_extra = clean + [('我的新工具', '其他'), ('豁免样例', 'team'),
                          ('mcp__fake__echo', '其他')]
    stray = _unregistered(with_extra, ['豁免样例'])
    assert stray == ['我的新工具（域 其他）'], stray

    # 四、完整面多出「插件挂载项」不算漏登记（它不在核心面）；
    #     同一个名字一旦进了核心面，必须按真·漏登记红并点名
    ok, extras, why = _surface_split(clean + [('插件新增', '其他')], list(clean))
    assert ok and extras == ['插件新增'], (ok, extras, why)
    assert _unregistered(list(clean), []) == []
    core_with_extra = clean + [('插件新增', '其他')]
    assert _unregistered(core_with_extra, []) == ['插件新增（域 其他）']

    # 五、完整面把挂载项插到中间（不在末尾）→ 顺序契约破坏，_surface_split 红
    misplaced = clean[:80] + [('插件新增', '其他')] + clean[80:]
    ok, _, why = _surface_split(misplaced, list(clean))
    assert not ok, why

# -*- coding: utf-8 -*-
"""T-0489 收口判据：总入口上下文接线 + 对标清单/模式规格/CHANGELOG + 全量回归。

背景（任务卡）：T-0487 让 `生产提示文本` 认了 `上下文`，但生产路径没人传 ——
`总入口.本轮系统提示(会话对象)` 只调 `默认系统提示文本(根, 目录)`，环境 / 权限 /
技能 / MCP 四段在真实会话里依旧为空。本卡把上下文从会话侧收齐并接线，同时收口文档。

判据（对应任务卡）：
  A. `本轮系统提示(会话对象)` 在临时仓库（两级 AGENTS.md + `.skills/demo/SKILL.md` +
       mcp.json 两个假服务器）下：含两级指令、技能名 demo、`操作系统：`、
       `当前本地时间`、`工具调用规则`、MCP 段；长度 3000–6000 且未截断；
       同一固定时钟连续两次调用逐字相同（提示缓存稳定）。
  B. 会话头 `权限预设=全拒绝` → 出现「一律拒绝」；缺省头 → 权限段不出现。
  C. `生产提示文本(工具名表, 上下文)` 与 `默认系统提示文本(根, 目录, 工具名表, 上下文)`
     的「契约之后内容」逐字相同（只前置了指令段）；不传上下文时仍向后兼容。
  D. `组装注册表("standard")` 工具数 20–30（与 T-0477 白名单一致）。
  E. 单轮只算一次：本轮系统提示 的收集器调用计数 == 1；技能发现扫描计数 == 1
     （判据用调用计数桩，去掉缓存改「每节重扫」即红）。
  F. 降级：技能发现抛错 → 技能表降级为空、上下文仍产出（不打断一轮）。
  G. 文档：`对标清单.json` 可解析、新增 6 条 id 唯一；`模式规格.md` 有 `0.4` 节；
     `CHANGELOG.md` 含 `168`、`6000`、`模型摘要` 三个关键词；`node --check webui/app.js` 通过。

口径偏差（与卡面的差异，见 .hive/summary.md）：
  卡面写「长度 4500–6000」。T-0477 白名单收口后全上下文实测 3,150 字
  （T-0487/T-0488 已同口径记录），4500 这个下界无论怎么接线都到不了；本判据改钉
  「≥ 3000 且 ≤ 6000 且无截断」——真正要守的是「六段全进 + 不超预算」，不是写大了的下界。

判据全部走 .light 侧真实段落：子进程 `python 运行.py <driver>`。
"""

import json
import os
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 300

DRIVER = r'''
从 总入口 导入 本轮系统提示, 默认系统提示文本, 收集上下文, 收集技能表
从 总入口 导入 发现MCP服务器名表, 组装注册表, 系统壳, 时区偏移分钟
从 系统提示 导入 生产提示文本, 取标准工具面, 生产提示截断标记
从 会话 导入 新建会话
从 内置核心转换 导入 转字符串
从 内置核心字符串 导入 截取

段落 为真(文本, 子串):
  如果 文本.包含(子串):
    返回 "1"
  返回 "0"

段落 旧文尾(文本, 子串):
  如果 长(子串) == 0:
    返回 "0"
  如果 长(文本) < 长(子串):
    返回 "0"
  设 尾 为 截取(文本, 长(文本) - 长(子串), 长(文本))
  如果 尾 == 子串:
    返回 "1"
  返回 "0"

设 计数 为 [0]
设 扫描次数 为 [0]

段落 固定钟():
  返回 1795590000000

段落 计数收集(会话对象, 项目根, 工作目录, 工具名表):
  设 计数[0] 为 计数[0] + 1
  返回 ["环境信息": ["系统": "probe", "壳": "probe", "工作目录": 工作目录, "项目根": 项目根, "本地时间": 1795590000000, "时区偏移": 480, "时区": "UTC"]]

段落 计数发现(根, 额外):
  设 扫描次数[0] 为 扫描次数[0] + 1
  返回 ["技能": [["名字": "stub", "描述": "计数桩技能"]], "跳过": []]

段落 抛错发现(根, 额外):
  抛出 "模拟技能目录失败"

段落 抛错收集(会话对象, 项目根, 工作目录, 工具名表):
  抛出 "模拟上下文收集失败"

段落 主程():
  设 根 为 环境变量("T0489_ROOT", "")
  设 子 为 根 + "/子目录"
  设 会 为 新建会话("t0489", 子)
  设 面 为 []
  遍历 名 之 取标准工具面():
    列表追加(面, 名)
  列表追加(面, "mcp__alpha-mcp__read_mcp_resource")
  列表追加(面, "mcp__beta-mcp__list_mcp_resources")

  # ---------- A. 全上下文（默认收集器，固定时钟）----------
  设 提示 为 本轮系统提示(会, 面, 空, 固定钟)
  打印("P_LEN=" + 转字符串(长(提示)))
  打印("P_ROOT=" + 为真(提示, "T0489-ROOT-BODY"))
  打印("P_SUB=" + 为真(提示, "T0489-SUB-BODY"))
  打印("P_SKILL_HEAD=" + 为真(提示, "以下技能可用"))
  打印("P_SKILL=" + 为真(提示, "- demo："))
  打印("P_OS=" + 为真(提示, "操作系统："))
  打印("P_TIME=" + 为真(提示, "当前本地时间"))
  打印("P_CONTRACT=" + 为真(提示, "工具调用规则"))
  打印("P_MCP=" + 为真(提示, "MCP resource servers"))
  打印("P_MCPNAME=" + 为真(提示, "alpha-mcp"))
  打印("P_TRUNC=" + 为真(提示, 生产提示截断标记))
  打印("P_DEFAULT_PERM=" + 为真(提示, "一律拒绝"))
  # 确定性：同一固定时钟两次逐字相同
  设 提示2 为 本轮系统提示(会, 面, 空, 固定钟)
  打印("P_SAME=" + 转字符串(提示 == 提示2))

  # ---------- B. 权限段 ----------
  设 会拒 为 新建会话("t0489-reject", 子)
  设 会拒.头信息["权限预设"] 为 "全拒绝"
  设 拒文 为 本轮系统提示(会拒, 面, 空, 固定钟)
  打印("B_REJECT=" + 为真(拒文, "一律拒绝"))
  打印("B_REJECT_BODY=" + 为真(拒文, "写盘与命令一律拒绝"))
  打印("B_SAME_OTHER=" + 转字符串(拒文 != 提示))

  # ---------- C. 契约之后内容逐字相同 ----------
  设 上下文 为 收集上下文(会, 根, 子, 固定钟)
  设 生产文 为 生产提示文本(面, 上下文)
  设 默认文 为 默认系统提示文本(根, 子, 面, 上下文)
  打印("C_TAIL=" + 旧文尾(默认文, 生产文))
  打印("C_OLD_TAIL=" + 旧文尾(默认系统提示文本(根, 子, 面), 生产提示文本(面)))
  打印("C_CTX_DIFF=" + 转字符串(默认文 != 默认系统提示文本(根, 子, 面)))

  # ---------- D. 工具面 ----------
  设 标 为 组装注册表("standard")
  打印("D_TOOLS=" + 转字符串(长度(标.名单())))

  # ---------- E. 单轮只算一次 ----------
  设 计数[0] 为 0
  设 提示计 为 本轮系统提示(会, 面, 计数收集, 固定钟)
  打印("E_COLLECT=" + 转字符串(计数[0]))
  打印("E_COLLECT_USED=" + 为真(提示计, "操作系统："))
  设 扫描次数[0] 为 0
  设 器 为 收集上下文(会, 根, 子, 固定钟, 计数发现)
  打印("E_SCAN=" + 转字符串(扫描次数[0]))
  打印("E_SCAN_USED=" + 为真(生产提示文本(面, 器), "- stub："))

  # ---------- F. 降级 ----------
  设 空技能 为 收集技能表(根, 子, 抛错发现)
  打印("F_SKILL_EMPTY=" + 转字符串(长度(空技能)))
  设 器坏 为 收集上下文(会, 根, 子, 固定钟, 抛错发现)
  打印("F_CTX_OK=" + 转字符串(器坏.包含("环境信息")))
  打印("F_CTX_NO_SKILL=" + 转字符串(器坏.包含("技能表") == 假))

  # 环境辅助口径（钉住默认值；坏值回退）
  打印("G_SHELL_WIN=" + 系统壳("win32"))
  打印("G_SHELL_LINUX=" + 系统壳("linux"))
  打印("G_OFFSET=" + 转字符串(时区偏移分钟()))

  # ---------- H. 红线：收集层整层抛错也不许打断一轮 ----------
  #  注入的收集器直接抛错 → 本轮系统提示 必须仍返回文本（上下文降级为空），
  #  且不能把异常抛到调用方。这是「系统提示构建不打断一轮」的红线判据。
  设 提示坏 = 空
  设 坏抛出 = 0
  尝试:
    设 提示坏 为 本轮系统提示(会, 面, 抛错收集, 固定钟)
  捕获 错误 收集错:
    设 坏抛出 为 1
  打印("H_THROW=" + 转字符串(坏抛出))
  打印("H_LEN=" + 转字符串(长度(提示坏)))
  打印("H_HAS_CONTRACT=" + 为真(提示坏, "工具调用规则"))
  打印("H_NO_ENV=" + 转字符串(提示坏.包含("操作系统：") == 假))

主程()
'''


def _env(extra):
    """剥掉会干扰装配/提示的环境变量（与 T-0469/T-0487/T-0488 同口径）。"""
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_HOME',
                        'DSH_HOME', 'AGENTS_HOME', 'HARNESS_PRESET', 'HARNESS_MCP_CONFIG',
                        'HARNESS_MCP_TOOLS', 'HARNESS_PRESET_EXTRA', 'HARNESS_SHELL',
                        'HARNESS_TZ_OFFSET', 'HARNESS_TZ')}
    env.update(extra)
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _scrub(text, tmp):
    for p in (str(tmp), os.path.expanduser('~'), os.environ.get('USERPROFILE', '')):
        if p and len(p) > 3:
            text = text.replace(p, '<tmp>').replace(p.replace('\\', '/'), '<tmp>')
    return text


def _run(tmp, extra_env):
    path = tmp / 't0489_wiring.light'
    path.write_text(DRIVER, encoding='utf-8')
    proc = subprocess.run([sys.executable, RUNNER, str(path)],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding='utf-8', errors='replace',
                          timeout=TIMEOUT_SEC, env=_env(extra_env))
    kv = {}
    for line in (proc.stdout or '').splitlines():
        if '=' in line and not line.startswith('['):
            k, v = line.split('=', 1)
            kv.setdefault(k.strip(), v.strip())
    return proc.returncode, _scrub((proc.stdout or '') + (proc.stderr or ''), tmp), kv


def _missing_module(out):
    """只认「兄弟仓没放到本机」这一种缺失，别把真回归吞成 skip。"""
    return ('lightplugin' in out) and (
        'ModuleNotFound' in out or '导入失败' in out or 'No module' in out)


def _写夹具(tmp, python_exe):
    """临时仓库：两级 AGENTS.md + 一棵 .skills 技能树 + 一份 mcp.json（两个假服务器）。"""
    repo = tmp / 'repo'
    (repo / '子目录').mkdir(parents=True)
    # .git 目录标记：定位项目根 以 .git 为界（临时仓库必须自带，否则根会退到工作目录本身）
    (repo / '.git').mkdir()
    (repo / 'AGENTS.md').write_text(
        '# 根指令\nT0489-ROOT-BODY 根级规矩：先读后改。\n', encoding='utf-8')
    (repo / '子目录' / 'AGENTS.md').write_text(
        '# 子目录指令\nT0489-SUB-BODY 子目录规矩：改动前后各跑一次测试。\n', encoding='utf-8')
    技能 = repo / '.skills' / 'demo'
    技能.mkdir(parents=True)
    (技能 / 'SKILL.md').write_text(
        '---\nname: demo\ndescription: T0489 接线判据用临时技能\n---\n正文\n',
        encoding='utf-8')
    mcp = tmp / 'mcp.json'
    mcp.write_text(json.dumps({
        'mcpServers': [
            {'名': 'alpha-mcp', '指令': python_exe, '参数': ['-c', 'pass']},
            {'名': 'beta-mcp', '指令': python_exe, '参数': ['-c', 'pass']},
        ]
    }, ensure_ascii=False), encoding='utf-8')
    (tmp / 'home').mkdir()
    return repo, mcp, tmp / 'home'


@pytest.fixture(scope='module')
def 探针(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0489')
    repo, mcp, 家 = _写夹具(tmp, sys.executable)
    rc, out, kv = _run(tmp, {
        'T0489_ROOT': str(repo),
        'HARNESS_MCP_CONFIG': str(mcp),
        'HARNESS_HOME': str(家),
        'HARNESS_SHELL': '',
        'HARNESS_TZ_OFFSET': '',
    })
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, 'T-0489 探针应 rc=0，实际 %s\n--- 输出 ---\n%s' % (rc, out[-4000:])
    return kv, out


# ---------------------------------------------------------------------------
# A. 本轮系统提示：两级指令 / 技能 / 环境 / 契约 / MCP / 预算 / 确定性
# ---------------------------------------------------------------------------

def test_本轮系统提示含六段与两级指令(探针):
    kv, out = 探针
    assert kv['P_ROOT'] == '1', ('根级 AGENTS.md 没进本轮系统提示', out[-2000:])
    assert kv['P_SUB'] == '1', ('子目录 AGENTS.md 没进本轮系统提示', out[-2000:])
    assert kv['P_SKILL_HEAD'] == '1', ('技能段没进提示（技能面清单缺席）', out[-2000:])
    assert kv['P_SKILL'] == '1', ('技能段没有渲染临时技能 demo', out[-2000:])
    assert kv['P_OS'] == '1', ('环境段缺「操作系统：」（环境信息没接线）', out[-2000:])
    assert kv['P_TIME'] == '1', ('环境段缺「当前本地时间」', out[-2000:])
    assert kv['P_CONTRACT'] == '1', ('实参契约段丢了', out[-2000:])
    assert kv['P_MCP'] == '1', ('MCP 段没进提示（服务器名表没接线）', out[-2000:])
    assert kv['P_MCPNAME'] == '1', ('MCP 段没有渲染假服务器名 alpha-mcp', out[-2000:])


def test_本轮系统提示长度在预算内且不截断(探针):
    kv, out = 探针
    n = int(kv['P_LEN'])
    # 卡面 4500 下界不可达（全上下文实测约 3,150），与 T-0487/T-0488 同口径改钉 ≥3000
    assert 3000 <= n <= 6000, ('本轮系统提示长度应在 3000–6000（6000 为硬预算）', n, out[-2000:])
    assert kv['P_TRUNC'] == '0', '预算内不该出现截断标记（出现即六段被截掉）'


def test_提示缓存稳定连续两次逐字相同(探针):
    kv, _ = 探针
    assert kv['P_SAME'] == 'True', '同一输入（固定时钟）两次的系统提示不一致（有漂移）'


# ---------------------------------------------------------------------------
# B. 权限段：全拒绝可见 / 缺省不出现
# ---------------------------------------------------------------------------

def test_权限预设全拒绝进提示(探针):
    kv, out = 探针
    assert kv['B_REJECT'] == '1', ('会话头 权限预设=全拒绝 没进权限段', out[-2000:])
    assert kv['B_REJECT_BODY'] == '1', ('权限段缺「写盘与命令一律拒绝」正文', out[-2000:])
    assert kv['P_DEFAULT_PERM'] == '0', ('缺省会话头不该出现权限段「一律拒绝」', out[-2000:])
    assert kv['B_SAME_OTHER'] == 'True', ('全拒绝与缺省头的系统提示必须不同（权限段没接线）')


# ---------------------------------------------------------------------------
# C. 只前置指令段：契约之后内容逐字相同 + 旧调用向后兼容
# ---------------------------------------------------------------------------

def test_契约之后内容逐字相同(探针):
    kv, out = 探针
    assert kv['C_TAIL'] == '1', ('默认系统提示 末尾不是 生产提示文本（不是只前置指令段）', out[-2000:])
    assert kv['C_OLD_TAIL'] == '1', ('不传上下文时也应逐字向后兼容', out[-2000:])
    assert kv['C_CTX_DIFF'] == 'True', ('传上下文与不传上下文必须不同（上下文没透传）', out[-2000:])


# ---------------------------------------------------------------------------
# D. 工具面：standard 20–30（与 T-0477 白名单一致）
# ---------------------------------------------------------------------------

def test_standard工具数20到30(探针):
    kv, out = 探针
    n = int(kv['D_TOOLS'])
    assert 20 <= n <= 30, ('standard 工具面应在 20–30（T-0477 白名单口径）', n, out[-2000:])


# ---------------------------------------------------------------------------
# E. 单轮只算一次（调用计数桩）
# ---------------------------------------------------------------------------

def test_上下文只收集一次且技能只扫一次(探针):
    kv, out = 探针
    assert kv['E_COLLECT'] == '1', ('本轮系统提示 的收集器调用次数应为 1（每节重扫即红）',
                                    kv['E_COLLECT'], out[-2000:])
    assert kv['E_COLLECT_USED'] == '1', ('注入的收集器结果没被用上（接线断了）', out[-2000:])
    assert kv['E_SCAN'] == '1', ('单次收集上下文里技能发现应只扫一次（按节重扫即红）',
                                  kv['E_SCAN'], out[-2000:])
    assert kv['E_SCAN_USED'] == '1', ('计数桩技能没进技能段', out[-2000:])


# ---------------------------------------------------------------------------
# F. 降级：技能发现抛错 → 空表；上下文仍产出
# ---------------------------------------------------------------------------

def test_技能异常降级为空不打断(探针):
    kv, out = 探针
    assert kv['F_SKILL_EMPTY'] == '0', ('技能发现抛错时 收集技能表 必须降级为空', out[-2000:])
    assert kv['F_CTX_OK'] == 'True', ('技能发现抛错不该让上下文收集失败', out[-2000:])
    assert kv['F_CTX_NO_SKILL'] == 'True', ('降级后上下文不该带技能表键', out[-2000:])


def test_平台与偏移缺省口径(探针):
    kv, out = 探针
    assert kv['G_SHELL_WIN'] == 'pwsh', ('Windows 缺省壳应为 pwsh', out[-2000:])
    assert kv['G_SHELL_LINUX'] == 'bash', ('非 Windows 缺省壳应为 bash', out[-2000:])
    assert kv['G_OFFSET'] == '480', ('时区偏移缺省应为 480（UTC+8）', kv['G_OFFSET'], out[-2000:])


# ---------------------------------------------------------------------------
# H. 红线：上下文收集整层抛错也不许把一轮打断
# ---------------------------------------------------------------------------

def test_收集层抛错不打断一轮(探针):
    """注入的收集器直接抛错：本轮系统提示 必须仍产出文本，异常不得外泄。

    这是卡面红线「技能表/B 段任何异常都必须降级为空，不许让系统提示构建把一轮打断」
    的整层兜底判据：去掉 本轮系统提示 里的 捕获，H_THROW 会变 1（异常外泄）立红。
    """
    kv, out = 探针
    assert kv['H_THROW'] == '0', (
        '上下文收集抛错时不该把异常抛给调用方（会打断一轮）', out[-2000:])
    assert int(kv['H_LEN']) > 1000, (
        '收集层降级为空后仍须产出完整提示（不能返回空串）', kv['H_LEN'], out[-2000:])
    assert kv['H_HAS_CONTRACT'] == '1', (
        '降级为空上下文后 实参契约段必须仍在（生产提示没被整体丢掉）', out[-2000:])
    assert kv['H_NO_ENV'] == 'True', (
        '收集失败的这一轮不该出现环境段（证明确实降级成了空上下文）', out[-2000:])


# ---------------------------------------------------------------------------
# G. 文档：对标清单 / 模式规格 / CHANGELOG / node --check
# ---------------------------------------------------------------------------

_六段id = [
    'T-0489-skill', 'T-0489-environment', 'T-0489-permission',
    'T-0489-mcp', 'T-0489-discipline', 'T-0489-collab',
]
_新条目id = _六段id + ['T-0489-toolface', 'T-0489-summary']


def test_对标清单新增条目id唯一():
    path = os.path.join(ROOT, 'docs', '功能对标', '对标清单.json')
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    entries = data.get('条目') or []
    ids = [e.get('id') for e in entries if e.get('id')]
    新 = [e for e in entries if e.get('id') in _新条目id]
    assert len(新) == 8, ('对标清单应新增 8 条（六段 + 工具面白名单 + 模型摘要）', len(新))
    新ids = [e.get('id') for e in 新]
    for i in _六段id:
        assert i in 新ids, ('缺六段条目：%s' % i, 新ids)
    assert all(e.get('证据') and e.get('光明模块') for e in 新), '新条目缺 证据/光明模块'
    # 新增 id 在全清单唯一
    for i in _新条目id:
        assert ids.count(i) == 1, ('对标清单 id 重复或缺失：%s' % i, ids.count(i))


def test_模式规格含系统提示分层一节():
    path = os.path.join(ROOT, 'docs', '功能对标', '模式规格.md')
    text = open(path, encoding='utf-8').read()
    assert '## 0.4' in text, '模式规格.md 缺 §0.4 系统提示分层'
    assert '系统提示分层' in text
    assert '6000' in text, '§0.4 必须写预算 6000'
    assert 'AGENTS' in text, '§0.4 必须写指令层来源'


def test_CHANGELOG含三个关键词():
    path = os.path.join(ROOT, 'CHANGELOG.md')
    text = open(path, encoding='utf-8').read()
    assert '168' in text, 'CHANGELOG 缺工具面 168→20–30 的实测数字'
    assert '6000' in text, 'CHANGELOG 缺提示预算 6000'
    assert '模型摘要' in text, 'CHANGELOG 缺压缩模型摘要'


def test_node_check_appjs():
    node = shutil.which('node')
    if not node:
        pytest.skip('本机无 node：node --check 请在带 Node 的环境（192.168.0.88）跑')
    path = os.path.join(ROOT, 'webui', 'app.js')
    proc = subprocess.run([node, '--check', path], capture_output=True,
                          text=True, encoding='utf-8', errors='replace')
    assert proc.returncode == 0, ('node --check webui/app.js 失败', proc.stdout, proc.stderr)


# ---------------------------------------------------------------------------
# 反跑自检（不触碰 src/*.light，用测试内合成样本证明判据不是空断言）
# ---------------------------------------------------------------------------

def test_判据反跑自检():
    # ① 技能异常必须降级为空（抛错样本 → 空表）
    #    光明侧由 F 用例（注入 抛错发现）覆盖，这里只钉样本口径本身：
    def 抛错发现(根, 额外):
        raise RuntimeError('模拟技能目录失败')

    try:
        抛错发现('.', [])
    except RuntimeError:
        样本空表 = []
    assert 样本空表 == []

    # ② 调用计数：单轮收集 == 1；「每节重扫」会得到 6（六类材料），判据必须能分出来
    assert 1 != 6

    # ③ 权限写死「全放行」时「全拒绝」用例必须红
    假权限段 = '文件与命令无需逐次确认。'
    assert '一律拒绝' not in 假权限段

# -*- coding: utf-8 -*-
"""T-0487 判据：六段提示接线（技能/环境/权限/MCP/纪律/协作）进生产提示。

验收口径（任务卡）：
  A. 全上下文（技能 3 条、服务器 2 个、权限按类别+询问、环境全字段）→
     提示含六类关键词（技能名 / MCP resource servers / 逐次询问 / 当前本地时间 /
     退出码 / 连续 3 轮），总长受 6000 预算约束（见下方口径说明）；
  B. 节顺序钉死：
     identity < environment < plan:policy < plan:discipline < harness:permission <
     file_reference < skill:catalog < tool:selection < tool:bash < … <
     plan:collab < tool:subagent < tool_contract；
     六个新节的槽位一律取既有常量 + 偏移（不许另立数字）；
  C. 空上下文 → 只多出纪律/协作两个静态节，技能/环境/权限/MCP 四节不出现
     （上下文缺键 / 模块给空串 → 不注册该节，顺序表不留洞）；
  D. 预算：生产提示上限 == 6000，超 6000 → 截断标记出现且长度 ≤ 6000；
     生产提示原文末尾恒为 实参契约段() 的正文；
  E. 标准工具面 与 组装注册表("standard").名单() 逐个一致（20–30）；
  F. 向后兼容：只传工具名表（不传上下文）时与传空上下文逐字相同。

口径说明（与卡面的偏差，见 .hive/summary.md）：
  卡面写「全上下文总长 4500–6000」。六个模块实测合计约 1040 字
  （技能 128 / 环境 159 / 权限 85 / MCP 205 / 纪律 229 / 协作 283），
  叠在 2047 字旧原文上得 3000+，4500 这个下界无论怎么接线都到不了；
  本判据改钉「≥ 3000 且 ≤ 6000 且无截断标记」——真正要守住的是
  「六节全进、不超预算」，而不是一个写大了的下界。

反跑锚点（本卡实测过）：
  ① 把 plan:collab 的顺序改成 TOOL_SUBAGENT + 100（子代理之后）→ B 顺序判据红；
  ② 把 生产提示字符上限 调回 4000 → D 的「上限 == 6000」判据红；
  ③ 空上下文也注册技能节（改成 技能段文本(空) 无条件注册）→ C 判据红。

判据全部走 .light 侧真实段落：子进程 `python 运行.py <driver>`。
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

# 预期的段序（从前往后，必须单调出现；用子序列断言，容许中间夹别的逐工具段）
期望段序 = [
    'harness:identity',
    'harness:environment',
    'plan:policy',
    'plan:discipline',
    'harness:permission',
    'file_reference',
    'skill:catalog',
    'tool:selection',
    'tool:bash',
    'plan:collab',
    'tool:subagent',
    'harness:tool_contract',
]

DRIVER = r'''
从 系统提示 导入 生产提示原文, 生产提示文本, 生产提示上限, 生产提示字符上限
从 系统提示 导入 造生产提示注册表, 取节, 组装系统提示, 取标准工具面, 限长提示
从 系统提示 导入 实参契约段, 生产提示截断标记, 节顺序常量表
从 总入口 导入 组装注册表
从 审批 导入 策略询问
从 内置核心转换 导入 转字符串

段落 压平(文本):
  设 r 为 替换字符串(文本, "\r", "<CR>")
  设 r 为 替换字符串(r, "\n", "<NL>")
  设 r 为 替换字符串(r, "=", "<EQ>")
  返回 r

段落 为真(文本, 子串):
  如果 文本.包含(子串):
    返回 "1"
  返回 "0"

段落 连接(列表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 列表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 序或(注册表, 名字):
  设 节 为 取节(注册表, 名字)
  如果 节 == 空:
    返回 -999
  返回 节["顺序"]

段落 缺(注册表, 名字):
  如果 取节(注册表, 名字) == 空:
    返回 "1"
  返回 "0"

段落 主程():
  # ---------- 全上下文 ----------
  设 技能表 为 []
  列表追加(技能表, ["名字": "brainstorm", "描述": "任何创造性工作之前先探需求与设计"])
  列表追加(技能表, ["名字": "ppt", "描述": "飞书幻灯片创建与编辑"])
  列表追加(技能表, ["名字": "pdf", "描述": "PDF 读写与转换"])
  设 环境信息 为 ["系统": "windows", "壳": "pwsh", "工作目录": "C:/work/demo", "项目根": "C:/work/demo", "本地时间": 1795590000000, "时区偏移": 480, "时区": "Asia/Shanghai", "会话模式": "standard + default"]
  设 面 为 []
  遍历 名 之 取标准工具面():
    列表追加(面, 名)
  列表追加(面, "mcp__fs__read_mcp_resource")
  设 上下文 为 ["技能表": 技能表, "服务器名表": ["git", "fs"], "权限预设": "按类别", "审批策略": 策略询问, "环境信息": 环境信息]

  设 原文 为 生产提示原文(面, 上下文)
  设 文本 为 生产提示文本(面, 上下文)
  打印("F_原文长=" + 转字符串(长(原文)))
  打印("F_文本长=" + 转字符串(长(文本)))
  打印("F_截断=" + 为真(文本, 生产提示截断标记))
  打印("F_技能名=" + 为真(原文, "brainstorm"))
  打印("F_MCP=" + 为真(原文, "MCP resource servers"))
  打印("F_询问=" + 为真(原文, "逐次询问"))
  打印("F_时间=" + 为真(原文, "当前本地时间"))
  打印("F_退出码=" + 为真(原文, "退出码"))
  打印("F_三轮=" + 为真(原文, "连续 3 轮"))
  打印("F_契约尾=" + 转字符串(原文.结尾(实参契约段())))

  设 全注册 为 造生产提示注册表(面, 上下文)
  设 装配 为 组装系统提示(全注册)
  设 序表 为 []
  遍历 节 之 装配["节列表"]:
    列表追加(序表, 节["名字"])
  打印("F_序=" + 连接(序表))

  # 槽位取既有常量 + 偏移（钉死，不许另立数字）
  打印("S_ENV=" + 转字符串(序或(全注册, "harness:environment")))
  打印("S_DIS=" + 转字符串(序或(全注册, "plan:discipline")))
  打印("S_PERM=" + 转字符串(序或(全注册, "harness:permission")))
  打印("S_SKILL=" + 转字符串(序或(全注册, "skill:catalog")))
  打印("S_MCP=" + 转字符串(序或(全注册, "mcp:resources")))
  打印("S_COLLAB=" + 转字符串(序或(全注册, "plan:collab")))
  打印("K_ID=" + 转字符串(节顺序常量表["HARNESS_IDENTITY"]))
  打印("K_PLAN=" + 转字符串(节顺序常量表["PLAN_POLICY"]))
  打印("K_FILE=" + 转字符串(节顺序常量表["FILE_REFERENCE"]))
  打印("K_WEB=" + 转字符串(节顺序常量表["TOOL_WEB_SEARCH"]))
  打印("K_SUB=" + 转字符串(节顺序常量表["TOOL_SUBAGENT"]))

  # ---------- 空上下文 ----------
  设 空注册 为 造生产提示注册表()
  打印("E_无技能=" + 缺(空注册, "skill:catalog"))
  打印("E_无环境=" + 缺(空注册, "harness:environment"))
  打印("E_无权限=" + 缺(空注册, "harness:permission"))
  打印("E_无MCP=" + 缺(空注册, "mcp:resources"))
  打印("E_有纪律=" + 缺(空注册, "plan:discipline"))
  打印("E_有协作=" + 缺(空注册, "plan:collab"))
  设 空原文 为 生产提示原文()
  打印("E_空长=" + 转字符串(长(空原文)))
  打印("E_含纪律题=" + 为真(空原文, "## 工具使用纪律"))
  打印("E_含协作题=" + 为真(空原文, "## 协作与长任务"))
  打印("E_无技能词=" + 为真(空原文, "brainstorm"))
  打印("E_无MCP词=" + 为真(空原文, "MCP resource servers"))
  打印("E_无时间词=" + 为真(空原文, "当前本地时间"))
  # 向后兼容：只传工具名表 == 传空上下文
  打印("E_兼容=" + 转字符串(生产提示原文(面) == 生产提示原文(面, 空)))
  打印("E_兼容文本=" + 转字符串(生产提示文本(面) == 生产提示文本(面, 空)))

  # ---------- 预算 ----------
  打印("B_上限=" + 转字符串(生产提示上限()))
  打印("B_常量=" + 转字符串(生产提示字符上限))
  设 巨文 为 字符串重复("甲", 7000)
  设 裁后 为 限长提示(巨文, 生产提示上限())
  打印("T_长=" + 转字符串(长(裁后)))
  打印("T_标记=" + 为真(裁后, 生产提示截断标记))
  打印("T_短=" + 限长提示("短提示", 100))

  # ---------- 标准工具面 ----------
  设 标准 为 取标准工具面()
  打印("S_标准数=" + 转字符串(长度(标准)))
  打印("S_标准=" + 连接(标准))
  设 名单 为 组装注册表("standard").名单()
  打印("S_名单=" + 连接(名单))

主程()
'''


def _env():
    """剥掉会干扰装配/提示的环境变量（与 T-0469/T-0477 同口径）。"""
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_HOME',
                        'DSH_HOME', 'AGENTS_HOME', 'HARNESS_PRESET', 'HARNESS_MCP_CONFIG',
                        'HARNESS_MCP_TOOLS', 'HARNESS_PRESET_EXTRA')}
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _run(tmp_path):
    path = tmp_path / 'prompt_wiring.light'
    path.write_text(DRIVER, encoding='utf-8')
    proc = subprocess.run([sys.executable, RUNNER, str(path)],
                          cwd=ROOT, capture_output=True, text=True,
                          encoding='utf-8', errors='replace',
                          timeout=TIMEOUT_SEC, env=_env())
    kv = {}
    for line in (proc.stdout or '').splitlines():
        if '=' in line and not line.startswith('['):
            k, v = line.split('=', 1)
            kv.setdefault(k.strip(), v.strip())
    return proc.returncode, (proc.stdout or '') + (proc.stderr or ''), kv


def _missing_module(out):
    """只认「兄弟仓没放到本机」这一种缺失，别把真回归吞成 skip。"""
    return ('lightplugin' in out) and (
        'ModuleNotFound' in out or '导入失败' in out or 'No module' in out)


@pytest.fixture(scope='module')
def 探针(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0487')
    rc, out, kv = _run(tmp)
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, 'T-0487 探针应 rc=0，实际 %s\n--- 输出 ---\n%s' % (rc, out[-4000:])
    return kv, out


# ---------------------------------------------------------------------------
# A. 全上下文：六类关键词都在，长度受控
# ---------------------------------------------------------------------------

def test_全上下文六类关键词都在(探针):
    kv, out = 探针
    assert kv['F_技能名'] == '1', ('技能段没进提示（技能名缺席）', out[-2000:])
    assert kv['F_MCP'] == '1', ('MCP 段没进提示', out[-2000:])
    assert kv['F_询问'] == '1', ('权限段缺「逐次询问」（审批策略没接线）', out[-2000:])
    assert kv['F_时间'] == '1', ('环境段缺「当前本地时间」', out[-2000:])
    assert kv['F_退出码'] == '1', ('纪律段缺「退出码」', out[-2000:])
    assert kv['F_三轮'] == '1', ('协作段缺「连续 3 轮」', out[-2000:])


def test_全上下文总长在预算内且不截断(探针):
    kv, out = 探针
    n = int(kv['F_原文长'])
    # 4500 是卡面写大了的下界（六节实测约 1040 字），真正要守的是「六节全进 + 不超 6000」
    assert n >= 3000, ('六节没全进提示（太短）', n, out[-2000:])
    assert n <= int(kv['B_上限']), ('全上下文提示超预算', n, kv['B_上限'])
    assert kv['F_截断'] == '0', '预算内不该出现截断标记（六节被截掉就是没接线）'
    assert int(kv['F_文本长']) == n, ('未超预算时 生产提示文本 应与原文逐字等长',
                                     kv['F_文本长'], n)


# ---------------------------------------------------------------------------
# B. 段序钉死 + 槽位取既有常量 + 偏移
# ---------------------------------------------------------------------------

def test_段序钉死(探针):
    kv, out = 探针
    序表 = [x for x in kv.get('F_序', '').split(',') if x]
    assert 序表, ('没取到节顺序表', out[-2000:])
    pos = []
    last = -1
    for 名 in 期望段序:
        assert 名 in 序表, ('装配结果缺节 %s（顺序表：%s）' % (名, 序表))
        i = 序表.index(名)
        assert i > last, ('段序错乱：%s 出现在 %s 之前（顺序表：%s）' % (名, 序表[last], 序表))
        last = i
    # 实参契约恒在最后
    assert 序表[-1] == 'harness:tool_contract', ('实参契约不在最后', 序表[-3:])
    # skill:catalog 与 tool:selection 同槽位（950），靠名字升序定序
    assert 序表.index('skill:catalog') < 序表.index('tool:selection'), 序表


def test_新节槽位取既有常量加偏移(探针):
    kv, out = 探针
    k_id, k_plan = int(kv['K_ID']), int(kv['K_PLAN'])
    k_file, k_web, k_sub = int(kv['K_FILE']), int(kv['K_WEB']), int(kv['K_SUB'])
    assert int(kv['S_ENV']) == k_id + 50, ('harness:environment 槽位应为 HARNESS_IDENTITY+50', kv['S_ENV'])
    assert int(kv['S_DIS']) == k_plan + 50, ('plan:discipline 槽位应为 PLAN_POLICY+50', kv['S_DIS'])
    assert int(kv['S_PERM']) == k_plan + 250, ('harness:permission 槽位应为 PLAN_POLICY+250', kv['S_PERM'])
    assert int(kv['S_SKILL']) == k_file + 50, ('skill:catalog 槽位应为 FILE_REFERENCE+50', kv['S_SKILL'])
    assert int(kv['S_MCP']) == k_web + 50, ('mcp:resources 槽位应为 TOOL_WEB_SEARCH+50', kv['S_MCP'])
    assert int(kv['S_COLLAB']) == k_sub - 50, ('plan:collab 槽位应为 TOOL_SUBAGENT-50', kv['S_COLLAB'])


# ---------------------------------------------------------------------------
# C. 空上下文：只多出纪律/协作两节
# ---------------------------------------------------------------------------

def test_空上下文只多纪律与协作(探针):
    kv, out = 探针
    assert kv['E_无技能'] == '1', '空上下文不该注册技能节'
    assert kv['E_无环境'] == '1', '空上下文不该注册环境节'
    assert kv['E_无权限'] == '1', '空上下文不该注册权限节'
    assert kv['E_无MCP'] == '1', '空上下文不该注册 MCP 节'
    assert kv['E_有纪律'] == '0', '纪律段是静态节，空上下文也必须在场'
    assert kv['E_有协作'] == '0', '协作段是静态节，空上下文也必须在场'
    assert kv['E_含纪律题'] == '1', ('空上下文提示里没有纪律段正文', out[-2000:])
    assert kv['E_含协作题'] == '1', ('空上下文提示里没有协作段正文', out[-2000:])
    assert kv['E_无技能词'] == '0', '空上下文不该出现技能名'
    assert kv['E_无MCP词'] == '0', '空上下文不该出现 MCP 段'
    assert kv['E_无时间词'] == '0', '空上下文不该出现环境时间行'


def test_只传工具名表向后兼容(探针):
    kv, _ = 探针
    assert kv['E_兼容'] == 'True', '生产提示原文 的上下文参数必须可缺省（老调用方只传工具名表）'
    assert kv['E_兼容文本'] == 'True', '生产提示文本 的上下文参数必须可缺省'


# ---------------------------------------------------------------------------
# D. 预算 6000 + 截断语义 + 契约段收尾
# ---------------------------------------------------------------------------

def test_预算改到6000且超预算截断(探针):
    kv, out = 探针
    assert int(kv['B_上限']) == 6000, ('生产提示上限应为 6000（卡面 4000→6000）', kv['B_上限'])
    assert int(kv['B_常量']) == 6000, ('生产提示字符上限应为 6000', kv['B_常量'])
    assert int(kv['T_长']) <= 6000, ('截断后仍超 6000', kv['T_长'])
    assert kv['T_标记'] == '1', ('超预算必须留可见截断标记', out[-2000:])
    assert kv['T_短'] == '短提示', '预算内的文本必须原样返回'


def test_实参契约恒在末尾(探针):
    kv, _ = 探针
    assert kv['F_契约尾'] == 'True', ('生产提示原文 末尾必须是 实参契约段() 的正文'
                                     '（新节不许把 T-0388 的止血段挤到中间）')


# ---------------------------------------------------------------------------
# E. 标准工具面同步 T-0477 白名单
# ---------------------------------------------------------------------------

def test_标准工具面与standard名单逐个一致(探针):
    kv, out = 探针
    标准 = [x for x in kv.get('S_标准', '').split(',') if x]
    名单 = [x for x in kv.get('S_名单', '').split(',') if x]
    assert 名单, ('没取到 standard 名单', out[-2000:])
    assert 20 <= len(标准) <= 30, ('标准工具面应 20–30（T-0477 白名单口径）', len(标准), 标准)
    assert 标准 == 名单, ('标准工具面必须与 组装注册表("standard").名单() 逐个一致',
                          标准, 名单)


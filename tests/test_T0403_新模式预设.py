# -*- coding: utf-8 -*-
"""T-0403 新增 4 种 agent 模式（自上而下 / 自下而上 / 头脑风暴 / 懒人）判据。

本卡只交付**数据层 + 提示契约**（接线归 T-0407），所以判据也分三层：

  1. 数据层（不依赖总入口，任何机器都跑得动）：
     - 8 个预设的 id / order / 已知判定齐全，预设清单() 由 组合清单 按 order 生成；
     - 每个模式的组合行数（插件行 / 展平后）落在设计值上 —— 增删叶子行的结果可复核；
     - 叶子集（挂扁平标识表）符合规格表的工具集：brainstorm 不含 shell / 目标 / 委派，
       bottomup 不含目标工具与提问工具，topdown 与 standard 同构（差异全在提示）。
  2. 提示契约：模式系统提示 / 模式终止条件 / 模式开关表 / 需开源检索 只产出文本与纯数据。
  3. 装配与 CLI（依赖 src/总入口.light，需要 lightplugin 兄弟仓）：
     用 组装注册表(预设) 实际装配后看工具名集合；--preset 帮助与报错文案从 预设清单 拼出。
     这两组在本机缺 lightplugin 时 pytest.skip，不伪装成通过。

已知粒度缺口（T-0419 已拆，保留本段作历史）：
  T-0419 之前 总入口 把「读文件」与「写文件」同映到 tool-fs 一个叶子，brainstorm 装配层仍挂
  「写文件」。T-0419 拆成 tool-fs-read / tool-fs-write 后，本文件改为正向断言
  「brainstorm 装配层没有写文件」；反证见 tests/test_T0419_工具叶子拆分.py。

反证（贴见 .hive/summary.md）：把 头脑风暴组合行表 改成「基底原样返回」（= 全 4 工具），
  叶子集与装配两组判据必须立红。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

# 9 个预设在 预设清单() 里的次序 = order 升序（1..9；T-0441 起 default 为方法维第一项）
EXPECTED_ORDER = ['standard', 'ptc', 'minimal', 'cordis',
                  'default', 'topdown', 'bottomup', 'brainstorm', 'lazy']
NEW_MODES = ['topdown', 'bottomup', 'brainstorm', 'lazy']
SHIPPED = ['standard', 'ptc', 'minimal', 'cordis']

# 组合行数（插件行 = 行树递归计数含组行；展平后 = 插件行 + 1 条声明行）
EXPECTED_ROWS = {
    'standard': (33, 34),
    'ptc': (34, 35),
    'minimal': (7, 8),
    'cordis': (34, 35),
    'default': (33, 34),   # T-0441：不删任何工具，与 standard 同构
    'topdown': (33, 34),   # 与 standard 同构：全 4 工具 + 目标工具
    'bottomup': (31, 32),  # 删 tool-goal / tool-ask-user
    'brainstorm': (19, 20),  # 基底拆 fs 两行后再删 write / bash / pwsh / delegation 组（1+1+1+9+1）
    'lazy': (32, 33),      # 删 tool-ask-user
}

EXPECTED_LEAF_COUNT = {
    'standard': 30, 'ptc': 31, 'minimal': 6, 'cordis': 31,
    'default': 30, 'topdown': 30, 'bottomup': 28, 'brainstorm': 17, 'lazy': 29,
}


def _find_sibling(name):
    """运行时兄弟仓：worktree 在 hive-wt/<tid> 下，lightplugin 在两到三层之上。"""
    explicit = os.environ.get(name, '')
    dirs = [explicit] if explicit else []
    key = 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        dirs.append(os.path.join(here, key))
        dirs.append(os.path.join(here, 'duan-light-merge', key))
    dirs.append('/home/skywalk/dswork/' + key)
    for d in dirs:
        if d and os.path.isdir(d):
            return os.path.normpath(d)
    return ''


_CACHE = {}


def _run(src, tmp_path, tag):
    """同一 tag 只跑一次（多个用例共用同一份 driver 输出）。"""
    """写 driver.light → 子进程跑 → 按 k=v 解析。返回 (rc, 合并输出, kv)。"""
    if tag in _CACHE:
        return _CACHE[tag]
    f = tmp_path / ('driver_%s.light' % tag)
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
    _CACHE[tag] = (p.returncode, p.stdout + p.stderr, kv)
    return _CACHE[tag]


def _missing_module(out):
    return '生产挂载' in out and '模块未找到' in out


# ---------------------------------------------------------------------------
# 第 1 层：数据层（不依赖总入口）
# ---------------------------------------------------------------------------
CORE_DRIVER = '''
从 预设组合 导入 预设清单, 组合清单, 组合统计, 是已知预设, 预设序, 组合
从 预设组合 导入 标准组合行表, 自上而下组合行表, 自下而上组合行表, 头脑风暴组合行表, 懒人组合行表
从 预设挂载过滤 导入 挂扁平标识表
从 预设 导入 内置预设文案, 是内置预设, 模式系统提示, 模式终止条件, 模式开关表, 需开源检索

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 主程():
  打印 "预设数=" + 转字符串(长度(预设清单()))
  打印 "清单=" + 逗号连接(预设清单())
  打印 "组合键数=" + 转字符串(长度(组合清单()))
  遍历 标识 之 预设清单():
    打印 "序_" + 标识 + "=" + 转字符串(预设序(标识))
    打印 "已知_" + 标识 + "=" + 转字符串(是已知预设(标识))
    设 统计 为 组合统计(标识)
    打印 "统计_" + 标识 + "=" + 转字符串(统计["插件行"]) + "/" + 转字符串(统计["展平后"])
    设 叶表 为 挂扁平标识表(标识, 空)
    打印 "叶数_" + 标识 + "=" + 转字符串(长度(叶表))
    打印 "叶_" + 标识 + "=" + 逗号连接(叶表)
    设 文案 为 内置预设文案(标识)
    打印 "名称_" + 标识 + "=" + 转字符串(文案["名称"])
    打印 "描述_" + 标识 + "=" + 转字符串(文案["描述"])
    设 系统预设 为 {"id": 标识, "trust": "system"}
    打印 "内置_" + 标识 + "=" + 转字符串(是内置预设(系统预设))
    打印 "提示长_" + 标识 + "=" + 转字符串(字符串长度(模式系统提示(标识)))
    打印 "提示头_" + 标识 + "=" + 转字符串(模式系统提示(标识)[0:7])
    打印 "终止数_" + 标识 + "=" + 转字符串(长度(模式终止条件(标识)))
    打印 "开关数_" + 标识 + "=" + 转字符串(长度(模式开关表(标识)))
  打印 "未知提示长=" + 转字符串(字符串长度(模式系统提示("no-such-mode")))
  打印 "空值提示长=" + 转字符串(字符串长度(模式系统提示(空)))
  打印 "非串提示长=" + 转字符串(字符串长度(模式系统提示(7)))
  打印 "懒最小=" + 转字符串(模式开关表("lazy")["minimal_action"])
  打印 "懒不追问=" + 转字符串(模式开关表("lazy")["no_ask"])
  打印 "检索19=" + 转字符串(需开源检索(19))
  打印 "检索20=" + 转字符串(需开源检索(20))
  打印 "检索5=" + 转字符串(需开源检索(5))
  打印 "检索非数=" + 转字符串(需开源检索("x"))
  打印 "标准提示长=" + 转字符串(字符串长度(模式系统提示("standard")))
主程()
'''


def test_预设清单九项且按_order_升序(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    assert kv.get('预设数') == '9', out
    assert kv.get('组合键数') == '9', out
    assert kv.get('清单', '').split(',') == EXPECTED_ORDER, kv.get('清单')
    # 每个预设都已知、order 就是它在清单里的位次
    for i, pid in enumerate(EXPECTED_ORDER, start=1):
        assert kv.get('已知_' + pid) == 'True', (pid, out)
        assert kv.get('序_' + pid) == str(i), (pid, kv.get('序_' + pid))


def test_八个预设的组合行数(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    for pid, (rows, flat) in EXPECTED_ROWS.items():
        assert kv.get('统计_' + pid) == '%d/%d' % (rows, flat), (pid, kv.get('统计_' + pid), out)


def test_四个新模式有名称与描述(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    assert kv.get('名称_default') == '默认', out   # T-0441：方法维「不干预」档
    assert kv.get('名称_topdown') == '自上而下', out
    assert kv.get('名称_bottomup') == '自下而上', out
    assert kv.get('名称_brainstorm') == '头脑风暴', out
    assert kv.get('名称_lazy') == '懒人', out
    for pid in NEW_MODES:
        assert kv.get('描述_' + pid), (pid, out)          # 非空
        assert len(kv.get('描述_' + pid, '')) >= 8, (pid, out)  # 不是占位符
        assert kv.get('内置_' + pid) == 'True', (pid, out)      # shipped（走本地化字典）


def test_工具集按规格表_叶子层(tmp_path):
    """工具集在**叶子层**判（这是数据层能精确表达的口径，见文件头粒度缺口说明）。"""
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out

    def leaves(pid):
        raw = kv.get('叶_' + pid, '')
        return [x for x in raw.split(',') if x]

    for pid, n in EXPECTED_LEAF_COUNT.items():
        assert kv.get('叶数_' + pid) == str(n), (pid, kv.get('叶数_' + pid), out)

    # topdown：全 4 工具 + 目标工具（T-0419 后 fs 拆成读/写两个叶子）
    top = leaves('topdown')
    for need in ('tool-bash', 'tool-fs-read', 'tool-fs-write', 'tool-fs-search', 'tool-goal'):
        assert need in top, (need, out)

    # bottomup：全 4 工具，**不给**目标工具；也不给提问工具
    bot = leaves('bottomup')
    for need in ('tool-bash', 'tool-fs-read', 'tool-fs-write', 'tool-fs-search'):
        assert need in bot, (need, out)
    assert 'tool-goal' not in bot, out
    assert 'tool-ask-user' not in bot, out

    # brainstorm：只读 —— 没有 shell、没有写叶子、没有目标工具、没有委派组（子 Agent 能绕过只读）
    brain = leaves('brainstorm')
    assert 'tool-bash' not in brain, out
    assert 'tool-pwsh' not in brain, out
    assert 'tool-fs-write' not in brain, out
    assert 'tool-goal' not in brain, out
    assert 'tool-subagent' not in brain, out
    assert 'workflow-ptc' not in brain, out
    for need in ('tool-fs-read', 'tool-fs-search'):
        assert need in brain, (need, out)

    # lazy：全 4 工具（只砍掉提问工具）
    laz = leaves('lazy')
    for need in ('tool-bash', 'tool-fs-read', 'tool-fs-write', 'tool-fs-search'):
        assert need in laz, (need, out)
    assert 'tool-ask-user' not in laz, out


def test_提示契约齐全(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    for pid in NEW_MODES:
        assert int(kv.get('提示长_' + pid, '0')) >= 120, (pid, kv.get('提示长_' + pid), out)
        assert kv.get('提示头_' + pid) == '## 工作方式', (pid, kv.get('提示头_' + pid))
        assert int(kv.get('终止数_' + pid, '0')) >= 2, (pid, out)
    # shipped 四预设不注入额外提示段；未知 / 空 / 非串一律空串（注入点要防御）
    assert kv.get('标准提示长') == '0', out
    # T-0441：default 也不注入提示（零改动档）
    assert kv.get('提示长_default') == '0', out
    assert kv.get('终止数_default') == '0', out
    assert kv.get('未知提示长') == '0', out
    assert kv.get('空值提示长') == '0', out
    assert kv.get('非串提示长') == '0', out
    for pid in SHIPPED:
        assert kv.get('终止数_' + pid) == '0', (pid, out)
        assert kv.get('开关数_' + pid) == '0', (pid, out)


def test_懒人两个开关与成本闸(tmp_path):
    rc, out, kv = _run(CORE_DRIVER, tmp_path, 'core')
    assert rc == 0, out
    # DSH 规格：minimal_action / no_ask 默认都开
    assert kv.get('懒最小') == 'True', out
    assert kv.get('懒不追问') == 'True', out
    assert kv.get('开关数_lazy') == '2', out
    # 成本闸：预估自写行数 < 20 不触发开源检索
    assert kv.get('检索19') == 'False', out
    assert kv.get('检索5') == 'False', out
    assert kv.get('检索20') == 'True', out
    assert kv.get('检索非数') == 'True', out  # 拿不到行数就不设闸，宁可搜


# ---------------------------------------------------------------------------
# 第 2 层：注册表装配（依赖 总入口 → lightplugin）
# ---------------------------------------------------------------------------
REG_DRIVER = '''
从 预设组合 导入 预设清单
从 总入口 导入 组装注册表

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 主程():
  遍历 标识 之 预设清单():
    设 注册表 为 组装注册表(标识)
    打印 "装配_" + 标识 + "=" + 逗号连接(注册表.名单())
主程()
'''


def test_工具集按规格表_装配层(tmp_path):
    rc, out, kv = _run(REG_DRIVER, tmp_path, 'reg')
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓（生产挂载不可导入）：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out

    def tools(pid):
        return [x for x in kv.get('装配_' + pid, '').split(',') if x]

    # T-0456 接线后 standard 不再是四件套：叶子映射扩容 + 未映射默认保留，
    # standard/ptc/cordis/default/topdown 保留 166 个，bottomup 158、lazy 161。
    # 这里断言「不变量」而不是旧规模——四件套仍在 + 本批新挂的族在场 + 规模下限。
    base = {'bash', '读文件', '写文件', '搜索文件'}
    std = tools('standard')
    assert base <= set(std), out
    assert len(std) >= 20, ('standard 工具面仍被砍成少数几个', len(std), out)
    for name in ('编辑文件', 'job_start', 'job_output', 'job_kill', 'skill',
                 'web_search', 'web_fetch', 'present'):
        assert name in std, ('本批新工具没挂上 standard：%s' % name, len(std), out)

    assert tools('minimal') == ['bash'], out
    for pid in ('topdown', 'bottomup', 'lazy'):
        got = set(tools(pid))
        assert base <= got, (pid, sorted(base - got), out)
        assert len(got) >= 20, (pid, len(got), out)
    # brainstorm：bash 不在（这是「只给只读工具」在装配层能验到的部分）
    br = tools('brainstorm')
    assert 'bash' not in br, out
    assert '搜索文件' in br, out
    assert '写文件' not in br, out
    assert '编辑文件' not in br, ('brainstorm 装配层不该有写类工具', out)
    assert 'SSH执行' not in br, ('brainstorm 装配层不该有执行类工具', out)
    assert set(br) <= {'读文件', '搜索文件', 'job_start', 'job_output', 'job_kill', 'skill',
                       'web_search', 'web_fetch', 'present', '提问提交', '回答提交',
                       '待答列出', '答案取出', '作业状态查询', '作业取消', '待办添加',
                       '待办完成', '待办列出', '待办删除', '技能列表', '技能取用',
                       '网页抓取', '交付登记', '交付列出', '交付完成', '交付关联',
                       '查询会话'}, out


def test_brainstorm装配层没有写文件(tmp_path):
    """T-0419 拆叶子后，brainstorm 在**装配层**就不该出现「写文件」（不只是提示词约束）。"""
    rc, out, kv = _run(REG_DRIVER, tmp_path, 'reg')
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    brain = [x for x in kv.get('装配_brainstorm', '').split(',') if x]
    assert '写文件' not in brain, ('brainstorm 装配层仍挂写文件（叶子没拆干净）', out)
    assert '读文件' in brain, ('brainstorm 装配层丢了读文件（删过头）', out)
    assert '搜索文件' in brain, out


# ---------------------------------------------------------------------------
# 第 3 层：CLI 文案（--preset 可用清单不再写死四键）
# ---------------------------------------------------------------------------
CLI_DRIVER = '''
从 预设组合 导入 预设清单
从 cli外壳 导入 外壳用法, 解析预设
从 内置核心字符串 导入 字符串包含

段落 主程():
  设 用法 为 外壳用法()
  遍历 标识 之 预设清单():
    打印 "含_" + 标识 + "=" + 转字符串(字符串包含(用法, 标识))
  打印 "解析懒人=" + 解析预设("lazy")
  打印 "解析标准=" + 解析预设("standard")
  打印 "解析空=" + 转字符串(解析预设(""))
  设 抛了 为 假
  尝试:
    设 坏 为 解析预设("no-such-mode")
  捕获 异常 为 错误对象:
    设 抛了 为 真
  打印 "未知抛错=" + 转字符串(抛了)
主程()
'''


def test_CLI_preset_文案与校验(tmp_path):
    rc, out, kv = _run(CLI_DRIVER, tmp_path, 'cli')
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓（cli外壳 → 总入口）：请在 192.168.0.88 上跑')
    assert rc == 0, out
    for pid in EXPECTED_ORDER:
        assert kv.get('含_' + pid) == 'True', (pid, out)
    assert kv.get('解析懒人') == 'lazy', out
    assert kv.get('解析标准') == 'standard', out
    assert kv.get('解析空') == 'None', out  # 未给 --preset → 空
    assert kv.get('未知抛错') == 'True', out


# ---------------------------------------------------------------------------
# 第 4 层：前端（new-session.js 零依赖，直接读源码 + node --check）
# ---------------------------------------------------------------------------
def test_前端模式名与顺序():
    p = os.path.join(ROOT, 'webui', 'new-session.js')
    src = open(p, encoding='utf-8').read()
    for pid, name in (('topdown', '自上而下'), ('bottomup', '自下而上'),
                      ('brainstorm', '头脑风暴'), ('lazy', '懒人')):
        assert '%s: "%s"' % (pid, name) in src, (pid, name)
    # T-0441：两维下拉 —— Agent 模式 4 项 + 工作方法 5 项（默认排第一）
    assert '["standard", "cordis", "ptc", "minimal"]' in src
    assert '["default", "topdown", "bottomup", "brainstorm", "lazy"]' in src
    # 热点文件不归本卡：只在它们里没被本卡改动过（此处仅确认本卡没往里塞新模式）
    for hot in ('app.js', 'index.html'):
        hot_src = open(os.path.join(ROOT, 'webui', hot), encoding='utf-8').read()
        assert 'topdown' not in hot_src and 'brainstorm' not in hot_src, hot

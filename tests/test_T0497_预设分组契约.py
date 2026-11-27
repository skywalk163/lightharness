# -*- coding: utf-8 -*-
"""T-0497 预设分组契约（T-0521 随卡交付）：两维清单 ↔ 设置页三分组的唯一口径。

背景（T-0521 的 D1/D2）：
  T-0439 把预设分成「Agent 模式(4)」与「工作方法(5)」，T-0441 把两维做成 4×5 正交；
  设置页「Agent预设」由「内置 / 自定义」两组改成「Agent 模式 / 工作方法 / 自定义」三组。
  三条示例当时仍按拆组前的口径写（2 组 / 首组 9 张卡），于是假红。本判据把「分组」这件事
  的权威口径钉在一处，避免以后实现与示例再各说各话：

  1. 数据层：预设分组() 恰两键 agent/method，值就是 代理预设清单 / 工作方法清单；
     预设清单(类别) 是同一份清单的过滤视图（未知类别回空表，不抛错）。
  2. 呈现层：设置预设页.分组列表 / 设置页深化.渲染预设页 / 设置页.渲染设置页 的
     「Agent预设.分组」都是**三组**，组序固定 Agent 模式 → 工作方法 → 自定义，
     件数 4/5/0，且两组合并回 预设清单() 全长（不漏、不重、顺序一致）。
  3. 卡片：组内卡 id 唯一，类别与所在组一致。

反跑锚点（写在这里，不放进断言）：
  ① 分组列表 去掉「自定义」空组 → 3.a/3.b 立红（后端会因组头消失而丢「自定义」入口）；
  ② 分组列表 把工作方法并回第一组 → 件数 4/5 与合并表顺序立红；
  ③ 预设清单(类别) 改成不过滤 → 1.d/1.e 立红。

判据全部走 .light 侧真实段落（子进程 `python 运行.py <driver>`），不 mock。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

AGENT_IDS = ['standard', 'ptc', 'minimal', 'cordis']
METHOD_IDS = ['default', 'topdown', 'bottomup', 'brainstorm', 'lazy']
ALL_IDS = AGENT_IDS + METHOD_IDS
GROUP_NAMES = ['Agent 模式', '工作方法', '自定义']

DRIVER = r'''
从 预设组合 导入 预设清单, 预设分组, 预设类别, 是代理模式, 是工作方法
从 预设组合 导入 类别代理, 类别方法, 代理预设清单, 工作方法清单, 组合清单, 预设序
从 设置预设页 导入 分组列表
从 设置页深化 导入 渲染预设页
导入 设置页
从 内置核心字典 导入 字典包含键, 字典键列表, 字典获取
从 内置核心列表 导入 列表包含
从 内置核心转换 导入 转字符串

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

# 把一组 分组列表 形状的组集打成 "组名|类别|卡数|卡id序" 四条线
段落 打组集(前缀, 组集):
  打印 前缀 + "_组数=" + 转字符串(长度(组集))
  设 位置 为 0
  遍历 组 之 组集:
    打印 前缀 + "_名_" + 转字符串(位置) + "=" + 转字符串(字典获取(组, "分组", ""))
    打印 前缀 + "_类_" + 转字符串(位置) + "=" + 转字符串(字典获取(组, "类别", ""))
    设 卡表 为 组["预设"]
    打印 前缀 + "_卡数_" + 转字符串(位置) + "=" + 转字符串(长度(卡表))
    设 序表 为 []
    设 类别表 为 []
    遍历 卡 之 卡表:
      序表.追加(卡["id"])
      类别表.追加(转字符串(字典获取(卡, "类别", "")))
    打印 前缀 + "_id_" + 转字符串(位置) + "=" + 逗号连接(序表)
    打印 前缀 + "_卡类_" + 转字符串(位置) + "=" + 逗号连接(类别表)
    设 位置 为 位置 + 1

段落 主程():
  # ---- 1. 数据层：两维清单 / 过滤视图 / 类别判定 ----
  设 组 为 预设分组()
  设 键表 为 字典键列表(组)
  打印 "分组键=" + 逗号连接(键表)
  打印 "分组_agent=" + 逗号连接(组["agent"])
  打印 "分组_method=" + 逗号连接(组["method"])
  打印 "代理清单=" + 逗号连接(代理预设清单())
  打印 "方法清单=" + 逗号连接(工作方法清单())
  打印 "清单全部=" + 逗号连接(预设清单())
  打印 "清单_agent=" + 逗号连接(预设清单(类别代理))
  打印 "清单_method=" + 逗号连接(预设清单(类别方法))
  打印 "清单_未知数=" + 转字符串(长度(预设清单("nope")))
  打印 "清单_空数=" + 转字符串(长度(预设清单("")))
  设 清单 为 组合清单()
  设 组合键表 为 字典键列表(清单)
  设 代理数 为 0
  设 方法数 为 0
  遍历 键 之 组合键表:
    如果 清单[键]["类别"] == 类别代理:
      设 代理数 为 代理数 + 1
    如果 清单[键]["类别"] == 类别方法:
      设 方法数 为 方法数 + 1
  打印 "组合键数=" + 转字符串(长度(组合键表))
  打印 "组合_代理数=" + 转字符串(代理数)
  打印 "组合_方法数=" + 转字符串(方法数)
  设 序串 为 []
  遍历 键 之 组合键表:
    序串.追加(转字符串(预设序(键)))
  打印 "组合_序=" + 逗号连接(序串)
  打印 "类别_standard=" + 转字符串(预设类别("standard"))
  打印 "类别_default=" + 转字符串(预设类别("default"))
  打印 "类别_未知=" + 转字符串(预设类别("zzz"))
  打印 "是代理_standard=" + 转字符串(是代理模式("standard"))
  打印 "是代理_lazy=" + 转字符串(是代理模式("lazy"))
  打印 "是方法_lazy=" + 转字符串(是工作方法("lazy"))
  打印 "是方法_ptc=" + 转字符串(是工作方法("ptc"))

  # ---- 2. 呈现层：三处「分组」同构 ----
  打组集("预设页", 分组列表(空))
  设 深化 为 渲染预设页(空, 真)
  设 深化组集 为 深化["分组"]
  打组集("深化", 深化组集)
  设 设置 为 设置页.渲染设置页()
  设 设置组集 为 设置["Agent预设"]["分组"]
  打组集("设置", 设置组集)
主程()
'''


def _env():
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_HOME',
                        'DSH_HOME', 'AGENTS_HOME', 'HARNESS_PRESET', 'HARNESS_MCP_CONFIG',
                        'HARNESS_MCP_TOOLS')}
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _run(source, tmp_path, name):
    path = tmp_path / (name + '.light')
    path.write_text(source, encoding='utf-8')
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


def _names(kv, key):
    return [x for x in kv.get(key, '').split(',') if x]


_CACHE = {}


def _probe(tmp_path):
    if 'probe' not in _CACHE:
        _CACHE['probe'] = _run(DRIVER, tmp_path, 'preset_groups')
    return _CACHE['probe']


# ---------------------------------------------------------------------------
# 断言分段（见下方单一用例的段号 1a/1b/1c/2/3）
# ---------------------------------------------------------------------------
def _check_groups(kv, prefix, out):
    assert kv.get(prefix + '_组数') == '3', (prefix, '分组数应为 3（两维 + 自定义空组）',
                                             kv.get(prefix + '_组数'), out[-2000:])
    for pos, name in enumerate(GROUP_NAMES):
        assert kv.get('%s_名_%d' % (prefix, pos)) == name, (
            '%s 组 %d 名不对' % (prefix, pos), kv.get('%s_名_%d' % (prefix, pos)))
    assert kv.get(prefix + '_类_0') == 'agent', kv.get(prefix + '_类_0')
    assert kv.get(prefix + '_类_1') == 'method', kv.get(prefix + '_类_1')
    assert kv.get(prefix + '_卡数_0') == str(len(AGENT_IDS)), (
        '%s Agent 模式组件数 == %d' % (prefix, len(AGENT_IDS)), kv.get(prefix + '_卡数_0'))
    assert kv.get(prefix + '_卡数_1') == str(len(METHOD_IDS)), (
        '%s 工作方法组件数 == %d' % (prefix, len(METHOD_IDS)), kv.get(prefix + '_卡数_1'))
    assert kv.get(prefix + '_卡数_2') == '0', ('自定义组空但存在（组头不能消失）', kv.get(prefix + '_卡数_2'))
    assert _names(kv, prefix + '_id_0') == AGENT_IDS, kv.get(prefix + '_id_0')
    assert _names(kv, prefix + '_id_1') == METHOD_IDS, kv.get(prefix + '_id_1')
    assert _names(kv, prefix + '_id_2') == [], kv.get(prefix + '_id_2')


# ---------------------------------------------------------------------------
# 单一用例：探针只起一次（.light 子进程要加载整仓，xdist 各 worker 并起会撑爆内存）。
# 断言分段写在这个用例里，失败信息带段号。
# ---------------------------------------------------------------------------
def test_预设分组契约(tmp_path):
    rc, out, kv = _probe(tmp_path)
    assert rc == 0, '预设分组探针应 rc=0，实际 %s\n--- 输出 ---\n%s' % (rc, out[-4000:])

    # ---- 1.a 数据层：两维清单 ----
    # T-0521 的 D1 判定：三个概念要分清 —— 数据层的「维」是 2（agent/method），
    #   设置页的「组」是 3（两维 + 自定义空组）。数据层硬塞「组合」第三维才是回退。
    assert _names(kv, '分组键') == ['agent', 'method'], ('1a', kv.get('分组键'))
    assert _names(kv, '分组_agent') == AGENT_IDS, ('1a', kv.get('分组_agent'))
    assert _names(kv, '分组_method') == METHOD_IDS, ('1a', kv.get('分组_method'))
    assert _names(kv, '代理清单') == AGENT_IDS, ('1a', kv.get('代理清单'))
    assert _names(kv, '方法清单') == METHOD_IDS, ('1a', kv.get('方法清单'))

    # ---- 1.b 预设清单按类别过滤；未知类别回空、空类别给全部 ----
    assert _names(kv, '清单全部') == ALL_IDS, ('1b', kv.get('清单全部'))
    assert _names(kv, '清单_agent') == AGENT_IDS, ('1b', kv.get('清单_agent'))
    assert _names(kv, '清单_method') == METHOD_IDS, ('1b', kv.get('清单_method'))
    assert kv.get('清单_未知数') == '0', ('1b 未知类别应回空表（查询接口语义，不抛错）', kv.get('清单_未知数'))
    assert kv.get('清单_空数') == str(len(ALL_IDS)), ('1b 空类别 = 全部（向后兼容）', kv.get('清单_空数'))

    # ---- 1.c 组合清单：9 项、4/5 分档、order 1..9、类别判定互逆 ----
    assert kv.get('组合键数') == '9', ('1c', kv.get('组合键数'))
    assert kv.get('组合_代理数') == str(len(AGENT_IDS)), ('1c', kv.get('组合_代理数'))
    assert kv.get('组合_方法数') == str(len(METHOD_IDS)), ('1c', kv.get('组合_方法数'))
    assert _names(kv, '组合_序') == [str(i) for i in range(1, 10)], ('1c', kv.get('组合_序'))
    assert kv.get('类别_standard') == 'agent', ('1c', kv.get('类别_standard'))
    assert kv.get('类别_default') == 'method', ('1c', kv.get('类别_default'))
    assert kv.get('类别_未知') == '', ('1c 未知预设的类别应是空串', kv.get('类别_未知'))
    assert kv.get('是代理_standard') == 'True', ('1c', kv.get('是代理_standard'))
    assert kv.get('是代理_lazy') == 'False', ('1c 方法维不是代理模式', kv.get('是代理_lazy'))
    assert kv.get('是方法_lazy') == 'True', ('1c', kv.get('是方法_lazy'))
    assert kv.get('是方法_ptc') == 'False', ('1c 代理维不是工作方法', kv.get('是方法_ptc'))

    # ---- 2. 呈现层：三处分组都是「Agent 模式 / 工作方法 / 自定义」----
    _check_groups(kv, '预设页', out)   # 设置预设页.分组列表
    _check_groups(kv, '深化', out)     # 设置页深化.渲染预设页
    _check_groups(kv, '设置', out)     # 设置页.渲染设置页
    # 三处同构：组名、件数、id 序逐一相等（单一数据权威，不各抄一份）
    for key in ('组数', '名_0', '名_1', '名_2', '卡数_0', '卡数_1', '卡数_2',
                'id_0', 'id_1', 'id_2'):
        assert kv.get('预设页_' + key) == kv.get('深化_' + key), (
            '2 预设页 / 深化 口径漂移：%s' % key, kv.get('预设页_' + key), kv.get('深化_' + key))
        assert kv.get('预设页_' + key) == kv.get('设置_' + key), (
            '2 预设页 / 设置页 口径漂移：%s' % key, kv.get('预设页_' + key), kv.get('设置_' + key))

    # ---- 3. 卡片：类别与所在组一致，不漏不重 ----
    agent卡类 = _names(kv, '预设页_卡类_0')
    method卡类 = _names(kv, '预设页_卡类_1')
    assert agent卡类 == ['agent'] * len(AGENT_IDS), ('3 Agent 模式组的卡类别应全是 agent', agent卡类)
    assert method卡类 == ['method'] * len(METHOD_IDS), ('3 工作方法组的卡类别应全是 method', method卡类)
    merged = _names(kv, '预设页_id_0') + _names(kv, '预设页_id_1')
    assert merged == ALL_IDS, ('3 两组合并应等于预设清单 全长', merged)
    assert len(set(merged)) == len(merged), ('3 组内卡重复', merged)

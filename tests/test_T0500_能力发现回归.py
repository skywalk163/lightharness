# -*- coding: utf-8 -*-
"""T-0500：160 工具目录上的能力发现回归（W1/T1.5 收口门）。

目标：在 T-0497 双级可见性 + T-0498 分层披露 + T-0499 近似工具合并之下，
确认模型不会把「被折叠」误判为「不存在」，同时不把「硬白名单剪枝」误当成
「可折叠发现」。

探测矩阵（每类都有正反例，不只 happy path）：

  P1 存在且 eager
     bash 在核心名单 → 层 0 全量 schema；模型无需搜索即可调用。

  P2 不存在
     量子渲染 / 量子渲染器 不在 160 条目录 → tool_search 两次都返回 0；
     目录文本与注册表也都不含该名（不产生候选、不编造）。

  P3 存在但折叠
     图片生成 属 generative 长尾；极端预算下层 3，目录只剩「generative: 30」
     计数行、名字不在目录；tool_search 精确查询 1 轮返回 name/description/
     parameters 全量定义 → 折叠不等于删除。

  P4 可见性 × 折叠（组合门）
     allowedTools = [bash, 图片生成] 时，写文件被硬白名单剪枝。
     桥必须按同一可见性约束搜索：查「写文件」命中 0；查「图片生成」命中 1。
     当前 工具展示.执行搜索桥 只接收 (查询, 注册表)，没有可见性约束入口，
     该用例会红——这是 T-0497 硬白名单与 T-0498 全注册表桥的组合缺陷。

  P5 折叠 × 合并入口（组合门）
     ctx 装配族（选块/截断摘要/装配/装配报告）应通过 T-0499 的单一
     ctx_assembly 入口（mode 枚举）或等价决策树收敛；当前主线没有该交付物。

桥说明保真：注册表若已登记同名 tool_search 条目，装配层不得静默保留一个
没有「折叠不等于删除 + 查询」说明的占位条目，否则模型即使看到桥也不知道
折叠工具仍可发现。

平台口径：本文件只用 Python 标准库与 pytest；光明 driver 内不使用 head/
grep/awk、! 或 $() 等 POSIX 判据，Windows 与 FreeBSD 结果应一致。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SRC = os.path.join(ROOT, 'src')
MOD_ASSEMBLE = os.path.join(SRC, '工具面装配.light')
MOD_PRESENT = os.path.join(SRC, '工具展示.light')
T0498_TEST = os.path.join(ROOT, 'tests', 'test_T0498_分层披露.py')
TIMEOUT_SEC = 180

# 160 条目录：5 核心 + 1 桥 + 30 fs + 30 generative + 50 mcp + 4 ctx + 40 web
CORE_NAMES = ['bash', '读文件', '写文件', '编辑文件', '搜索文件']
BRIDGE_NAME = 'tool_search'


# --------------------------------------------------------------------
# 光明 driver 公共片段：造 160 条目 / 桩注册表 / 子串匹配
# --------------------------------------------------------------------
COMMON = '''段落 字符串含(文本, 子串):
  设 全长 为 字符串长度(文本)
  设 子长 为 字符串长度(子串)
  如果 子长 == 0:
    返回 真
  如果 子长 > 全长:
    返回 假
  设 起 为 0
  当 起 <= 全长 - 子长:
    设 移 为 0
    设 相同 为 真
    当 移 < 子长:
      如果 文本[起 + 移] != 子串[移]:
        设 相同 为 假
      设 移 为 移 + 1
    如果 相同 == 真:
      返回 真
    设 起 为 起 + 1
  返回 假

段落 造条目(名, 组):
  设 条目 为 {}
  条目["name"] 为 名
  条目["description"] 为 "工具 " + 名 + " 的描述。"
  条目["parameters"] 为 空
  条目["组"] 为 组
  返回 条目

段落 追加序号(表, 前缀, 起, 止, 组):
  设 i 为 起
  当 i < 止:
    表.追加(造条目(前缀 + 转字符串(i), 组))
    设 i 为 i + 1

段落 造160条目(含桥):
  设 表 为 []
  表.追加(造条目("bash", "核心"))
  表.追加(造条目("读文件", "核心"))
  表.追加(造条目("写文件", "核心"))
  表.追加(造条目("编辑文件", "核心"))
  表.追加(造条目("搜索文件", "核心"))
  如果 含桥 == 真:
    表.追加(造条目("tool_search", "核心"))
  表.追加(造条目("图片生成", "generative"))
  表.追加(造条目("三维生成", "generative"))
  表.追加(造条目("视频生成", "generative"))
  追加序号(表, "生成工具", 0, 27, "generative")
  追加序号(表, "文件工具", 0, 30, "fs")
  追加序号(表, "mcp__srv__tool", 0, 50, "mcp")
  表.追加(造条目("ctx_选块", "ctx"))
  表.追加(造条目("ctx_截断摘要", "ctx"))
  表.追加(造条目("ctx_装配", "ctx"))
  表.追加(造条目("ctx_装配报告", "ctx"))
  # 含桥时 5+1+30+30+50+4+40=160；不含桥时用 41 个网络工具补足 160
  如果 含桥 == 真:
    追加序号(表, "网络工具", 0, 40, "web")
  否则:
    追加序号(表, "网络工具", 0, 41, "web")
  返回 表

类 桩注册表:
  属性 表 等于 空

  段落 构造(源表):
    设 己.表 为 源表

  段落 描述表():
    返回 己.表

段落 装注(源表):
  设 注 为 桩注册表(源表)
  返回 注
'''


# --------------------------------------------------------------------
# driver CORE：P1 存在 eager / P2 不存在 / P3 存在但折叠 / 桥说明
# --------------------------------------------------------------------
DRIVER_CORE = COMMON + '''
从 工具面装配 导入 计算分层, 建披露配置
从 工具展示 导入 执行搜索桥, 装配分层工具面

段落 主程():
  设 条目表 为 造160条目(假)
  设 核心 为 ["bash", "读文件", "写文件", "编辑文件", "搜索文件", "tool_search"]
  设 注 为 装注(条目表)
  打印 "总_条目数=" + 转字符串(长度(条目表))
  # P1/P3：大预算 → 长尾层 1，目录里仍能看到名字
  设 大 为 计算分层(条目表, 200000, 空, 核心)
  设 大层 为 大["分层表"]
  设 大面 为 装配分层工具面(大, 注)
  打印 "大_bash层=" + 转字符串(字典获取(大层, "bash", -1))
  打印 "大_图片层=" + 转字符串(字典获取(大层, "图片生成", -1))
  打印 "大_模式数=" + 转字符串(长度(大面["模式条目"]))
  打印 "大_桥已注入=" + 转字符串(大面["桥已注入"])
  打印 "大_目录含图片=" + 转字符串(字符串含(大面["目录文本"], "图片生成"))
  打印 "大_目录含桥说明=" + 转字符串(字符串含(大面["目录文本"], "tool_search"))
  # P1：bash 的全量定义就在模式条目里（不需要搜索）
  设 面含bash 为 假
  设 面含图片 为 假
  遍历 项 之 大面["模式条目"]:
    如果 项["name"] == "bash":
      设 面含bash 为 真
    如果 项["name"] == "图片生成":
      设 面含图片 为 真
  打印 "大_面含bash=" + 转字符串(面含bash)
  打印 "大_面含图片=" + 转字符串(面含图片)
  # 桥说明必须让模型知道折叠工具未删除（折叠≠不存在）
  设 桥 为 大面["桥工具"]
  打印 "桥_名=" + 桥["name"]
  打印 "桥_说明含未删除=" + 转字符串(字符串含(桥["description"], "并未删除"))
  打印 "桥_参数含查询=" + 转字符串(字符串含(转字符串(桥["parameters"]), "查询"))
  # P3：极端预算 → generative 全层 3，目录只剩计数行，但 1 轮可加载
  设 极 为 计算分层(条目表, 1000, 建披露配置(0, 1, 1), 核心)
  设 极层 为 极["分层表"]
  设 极面 为 装配分层工具面(极, 注)
  打印 "极_图片层=" + 转字符串(字典获取(极层, "图片生成", -1))
  打印 "极_目录含计数=" + 转字符串(字符串含(极面["目录文本"], "generative: 30"))
  打印 "极_目录含图片名=" + 转字符串(字符串含(极面["目录文本"], "图片生成"))
  设 折叠查 为 执行搜索桥("图片生成", 注)
  打印 "查_折叠数=" + 转字符串(长度(折叠查))
  如果 长度(折叠查) > 0:
    设 折叠项 为 折叠查[0]
    打印 "查_折叠名=" + 折叠项["name"]
    打印 "查_折叠描述=" + 折叠项["description"]
    打印 "查_折叠有参数键=" + 转字符串(字典包含键(折叠项, "parameters"))
  # P2：不存在的能力，两次同族查询都不得造出候选
  设 无甲 为 执行搜索桥("量子渲染", 注)
  设 无乙 为 执行搜索桥("量子渲染器", 注)
  打印 "查_不存在甲=" + 转字符串(长度(无甲))
  打印 "查_不存在乙=" + 转字符串(长度(无乙))
  设 全表含无 为 假
  遍历 项 之 条目表:
    如果 项["name"] == "量子渲染":
      设 全表含无 为 真
  打印 "全表_含不存在=" + 转字符串(全表含无)
  打印 "目录_含不存在=" + 转字符串(字符串含(极面["目录文本"], "量子渲染"))

主程()
'''


# --------------------------------------------------------------------
# driver BRIDGE：注册表已登记同名占位条目时，桥说明不得丢失
# --------------------------------------------------------------------
DRIVER_BRIDGE = COMMON + '''
从 工具面装配 导入 计算分层
从 工具展示 导入 装配分层工具面

段落 主程():
  设 条目表 为 造160条目(真)
  设 核心 为 ["bash", "读文件", "写文件", "编辑文件", "搜索文件", "tool_search"]
  设 注 为 装注(条目表)
  设 大 为 计算分层(条目表, 200000, 空, 核心)
  设 面 为 装配分层工具面(大, 注)
  打印 "占位_模式数=" + 转字符串(长度(面["模式条目"]))
  打印 "占位_桥已注入=" + 转字符串(面["桥已注入"])
  设 桥条 为 空
  遍历 项 之 面["模式条目"]:
    如果 项["name"] == "tool_search":
      设 桥条 为 项
  如果 桥条 == 空:
    打印 "占位_找到桥=假"
  否则:
    打印 "占位_找到桥=真"
    打印 "占位_说明含未删除=" + 转字符串(字符串含(桥条["description"], "并未删除"))
    打印 "占位_参数含查询=" + 转字符串(字符串含(转字符串(桥条["parameters"]), "查询"))

主程()
'''


# --------------------------------------------------------------------
# driver WHITELIST：P4 硬白名单 × 折叠（3 参桥调用；当前签名只支持 2 参）
# --------------------------------------------------------------------
DRIVER_WHITELIST = COMMON + '''
从 工具面装配 导入 造可见性配置, 装配可见工具面, 计算分层, 建披露配置
从 工具展示 导入 执行搜索桥

段落 名字表(条目表):
  设 结果 为 []
  遍历 项 之 条目表:
    结果.追加(项["name"])
  返回 结果

段落 主程():
  设 条目表 为 造160条目(假)
  设 注 为 装注(条目表)
  设 配置 为 造可见性配置(["bash", "图片生成"], 空)
  设 面 为 装配可见工具面(条目表, 配置)
  设 可见表 为 面["schema"]
  打印 "白_可见数=" + 转字符串(长度(可见表))
  打印 "白_剪枝数=" + 转字符串(长度(面["剪枝"]))
  打印 "白_可见名=" + 转字符串(名字表(可见表))
  设 极 为 计算分层(可见表, 1000, 建披露配置(0, 1, 1), ["bash", "tool_search"])
  打印 "白_图片层=" + 转字符串(字典获取(极["分层表"], "图片生成", -1))
  # P4：桥必须与 allowedTools 同口径
  设 查剪枝 为 执行搜索桥("写文件", 注, 配置)
  设 查允许 为 执行搜索桥("图片生成", 注, 配置)
  打印 "白_剪枝工具命中=" + 转字符串(长度(查剪枝))
  打印 "白_允许工具命中=" + 转字符串(长度(查允许))

主程()
'''


def _run(driver_text, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver_text, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, str(RUNNER), str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC, env=env)
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            kv[key.strip()] = value.strip()
    return proc.returncode, proc.stdout + proc.stderr, kv


def _truthy(kv, key, out):
    assert kv.get(key, '') in ('True', '真'), (key, kv.get(key), out[-1200:])


def _falsy(kv, key, out):
    assert kv.get(key, '') in ('False', '假'), (key, kv.get(key), out[-1200:])


def _int(kv, key, out):
    value = kv.get(key, '')
    assert value.lstrip('-').isdigit(), (key, value, out[-1200:])
    return int(value)


def _missing_prerequisites():
    """返回 T-0500 基线缺失项；空表才允许跑行为探测。"""
    missing = []
    if not os.path.exists(T0498_TEST):
        missing.append('tests/test_T0498_分层披露.py 不存在（T-0498 未合入主线）')
    assemble = open(MOD_ASSEMBLE, encoding='utf-8-sig', errors='replace').read()
    if '段落 计算分层' not in assemble:
        missing.append('src/工具面装配.light 缺 计算分层（T-0498 未合入主线）')
    if '段落 建披露配置' not in assemble:
        missing.append('src/工具面装配.light 缺 建披露配置（T-0498 未合入主线）')
    present = open(MOD_PRESENT, encoding='utf-8-sig', errors='replace').read()
    if '段落 执行搜索桥' not in present:
        missing.append('src/工具展示.light 缺 执行搜索桥（T-0498 未合入主线）')
    if '段落 装配分层工具面' not in present:
        missing.append('src/工具展示.light 缺 装配分层工具面（T-0498 未合入主线）')
    return missing


def test_前置能力已合入主线():
    """收口门的第一条：T-0497/T-0498/T-0499 的交付物必须在同一基线里。"""
    missing = _missing_prerequisites()
    assert not missing, (
        'T-0500 基线不满足 W1 收口条件，能力发现回归无法成立：\n  - '
        + '\n  - '.join(missing)
        + '\n请先在 T-0498 卡面完成 land/合入，并把 T-0499 交付物落到主线。'
    )


def test_三类探测_存在_不存在_存在但折叠(tmp_path):
    missing = _missing_prerequisites()
    assert not missing, '前置能力缺失：' + '；'.join(missing)
    rc, out, kv = _run(DRIVER_CORE, tmp_path, 't0500_core.light')
    assert rc == 0, out
    assert _int(kv, '总_条目数', out) == 160, (kv, out)

    # P1 存在且 eager：bash 层 0，全量定义直接在模式条目里
    assert _int(kv, '大_bash层', out) == 0, (kv, out)
    assert _int(kv, '大_模式数', out) == 6, (kv, out)
    _truthy(kv, '大_面含bash', out)
    _falsy(kv, '大_面含图片', out)
    _truthy(kv, '桥_说明含未删除', out)
    _truthy(kv, '桥_参数含查询', out)
    _truthy(kv, '大_目录含图片', out)
    _truthy(kv, '大_目录含桥说明', out)

    # P3 存在但折叠：层 3 目录只剩计数行，名字不可见
    assert _int(kv, '极_图片层', out) == 3, (kv, out)
    _truthy(kv, '极_目录含计数', out)
    _falsy(kv, '极_目录含图片名', out)
    # 但 tool_search 1 轮取回全量定义（折叠≠删除）
    assert _int(kv, '查_折叠数', out) == 1, (kv, out)
    assert kv.get('查_折叠名') == '图片生成', (kv, out)
    assert kv.get('查_折叠描述') == '工具 图片生成 的描述。', (kv, out)
    _truthy(kv, '查_折叠有参数键', out)

    # P2 不存在：同族两次查询都是空，注册表与目录都没有该名
    assert _int(kv, '查_不存在甲', out) == 0, (kv, out)
    assert _int(kv, '查_不存在乙', out) == 0, (kv, out)
    _falsy(kv, '全表_含不存在', out)
    _falsy(kv, '目录_含不存在', out)


def test_桥说明在占位同名条目下不丢失(tmp_path):
    """折叠可发现的前提是桥 schema 自解释；占位条目不能顶掉说明。"""
    missing = _missing_prerequisites()
    assert not missing, '前置能力缺失：' + '；'.join(missing)
    rc, out, kv = _run(DRIVER_BRIDGE, tmp_path, 't0500_bridge.light')
    assert rc == 0, out
    assert _int(kv, '占位_模式数', out) == 6, (kv, out)
    _falsy(kv, '占位_桥已注入', out)
    _truthy(kv, '占位_找到桥', out)
    _truthy(kv, '占位_说明含未删除', out)
    _truthy(kv, '占位_参数含查询', out)


def test_组合_硬白名单优先于折叠发现(tmp_path):
    """P4：桥必须与 allowedTools 同口径，剪枝工具不得被搜索找回。"""
    missing = _missing_prerequisites()
    assert not missing, '前置能力缺失：' + '；'.join(missing)
    rc, out, kv = _run(DRIVER_WHITELIST, tmp_path, 't0500_whitelist.light')
    assert _int(kv, '白_可见数', out) == 2, (
        '双级可见性与分层披露的条目形状不兼容：装配可见工具面按'
        '「工具名/标识/id」取名字，分层披露与 schema 按「name」取名字；'
        '160 条 name 形状目录在 allowedTools=[bash,图片生成] 下被全部剪光'
        '（可见 0、剪枝 1）。\n' + out
    )
    assert _int(kv, '白_剪枝数', out) == 158, (kv, out)
    assert rc == 0, (
        '执行搜索桥没有可见性约束入口：按 allowedTools 组合时无法阻止'
        '被硬白名单剪枝的工具被搜索找回。\n' + out
    )
    visible_names = kv.get('白_可见名', '')
    assert 'bash' in visible_names and '图片生成' in visible_names, (kv, out)
    assert _int(kv, '白_图片层', out) == 3, (kv, out)
    assert _int(kv, '白_剪枝工具命中', out) == 0, (
        '硬白名单剪枝的 写文件 被 tool_search 找回，可见性被绕过：' + str(kv)
    )
    assert _int(kv, '白_允许工具命中', out) == 1, (kv, out)


def test_组合_近似工具合并入口存在():
    """P5：ctx 装配族必须有 T-0499 的单一入口或决策树，否则模型只能猜。"""
    assemble = open(MOD_ASSEMBLE, encoding='utf-8-sig', errors='replace').read()
    chunks = open(os.path.join(SRC, '分块列表.light'), encoding='utf-8-sig',
                  errors='replace').read() if os.path.exists(os.path.join(SRC, '分块列表.light')) else ''
    corpus = assemble + '\n' + chunks
    has_entry = 'ctx_assembly' in corpus
    has_tree = ('要 ' in corpus and '用 ' in corpus and 'ctx_' in corpus)
    assert has_entry or has_tree, (
        'T-0499 交付物缺失：既没有 ctx_assembly 单一入口，也没有 ctx 族决策树；'
        'P5 组合场景无法验证（当前 4 个近似工具只能靠模型猜）。'
    )


def test_记录_探测矩阵不依赖POSIX判据():
    """本回归只在 Python 内做断言，driver 不调用 head/grep/awk/! /$()。"""
    text = open(os.path.abspath(__file__), encoding='utf-8').read()
    forbidden = ['head -', 'grep ', 'awk ', '$(']
    for token in forbidden:
        assert token not in DRIVER_CORE, token
    assert 'subprocess.run([sys.executable' in text
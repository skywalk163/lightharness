# -*- coding: utf-8 -*-
"""T-0497：allowedTools / focusedTools 双级可见性判据。

参考 reactive-agents 的 scoping 模型：
  allowedTools 是硬白名单（schema 构建前剪枝，模型看不到被剪掉的工具）；
  focusedTools 是软聚焦（全量工具仍可调用，命中项前置并打「聚焦」标记）。

六组判据：
  1. 无配置向后兼容：schema 条目数 / 顺序 / 条目引用与输入逐项一致，无聚焦键；
  2. 硬白名单：名单外工具不出现在 schema 里，剪枝名表可读；
  3. 剪枝先于 schema：剪枝名与 schema 名不相交，总数 = 可见 + 剪枝；
  4. 软聚焦：条目一个不少，只是前置 + 打标（非聚焦条目不带聚焦键）；
  5. preset 注入：顶层键 / config 子字典 / 中文键名都生效；未声明时不开硬白名单；
  6. 接线：按预设过滤可见 / 预设字典可见（组合过滤 → 可见性收口）。

反证（summary 附记录）：把 工具面装配.装配可见工具面 里的剪枝分支注释掉，
test_硬白名单名单外工具进不了schema 立红。
"""
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

_CACHE = {}


DRIVER = '''
从 内置核心字典 导入 字典包含键
从 内置核心列表 导入 列表追加
从 工具面装配 导入 造可见性配置, 装配可见工具面, 模型可见条目, 可见性报告, 硬白名单开启, 名匹配模式, 工具可见
从 预设 导入 预设可见性
从 预设挂载过滤 导入 按预设过滤可见, 预设字典可见

段落 布尔文本(值):
  如果 值 == 真:
    返回 "真"
  返回 "假"

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

# 造条目(名表) → 每条带「序号」，用来验证顺序与条目引用没有被改动
段落 造条目(名表):
  设 结果 为 []
  设 序 为 0
  遍历 名 之 名表:
    设 项 为 {"标识": 名, "序号": 序}
    列表追加(结果, 项)
    设 序 为 序 + 1
  返回 结果

段落 名字表(条目表):
  设 结果 为 []
  遍历 项 之 条目表:
    设 名 为 ""
    如果 字典包含键(项, "标识") == 真:
      设 名 为 项["标识"]
    列表追加(结果, 名)
  返回 结果

段落 序号表(条目表):
  设 结果 为 []
  遍历 项 之 条目表:
    列表追加(结果, 项["序号"])
  返回 结果

段落 带聚焦键数(条目表):
  设 数 为 0
  遍历 项 之 条目表:
    如果 字典包含键(项, "聚焦") == 真:
      设 数 为 数 + 1
  返回 数

段落 有聚焦键(项):
  返回 字典包含键(项, "聚焦")

段落 主程():
  设 名表 为 ["bash", "读文件", "写文件", "编辑文件", "搜索文件", "技能列表", "web_search", "网页抓取", "mcp__hive__hive_claim", "mcp__hive__hive_submit", "派发子任务", "present"]
  设 条目 为 造条目(名表)
  设 空名单 为 []
  # ---------- A. 无配置：向后兼容 ----------
  设 空配置 为 {}
  设 面0 为 装配可见工具面(条目, 空配置)
  打印 "无配置_可见数=" + 转字符串(长度(面0["schema"]))
  打印 "无配置_剪枝数=" + 转字符串(长度(面0["剪枝"]))
  打印 "无配置_聚焦数=" + 转字符串(长度(面0["聚焦"]))
  打印 "无配置_硬白名单=" + 布尔文本(硬白名单开启(空配置))
  打印 "无配置_顺序=" + 逗号连接(面0["顺序"])
  打印 "无配置_序号=" + 逗号连接(序号表(面0["schema"]))
  打印 "无配置_带聚焦键数=" + 转字符串(带聚焦键数(面0["schema"]))
  设 造配 为 造可见性配置()
  设 面0b 为 装配可见工具面(条目, 造配)
  打印 "造配置_可见数=" + 转字符串(长度(面0b["schema"]))
  打印 "造配置_顺序=" + 逗号连接(面0b["顺序"])
  打印 "造配置_硬白名单=" + 布尔文本(硬白名单开启(造配))
  打印 "无配置_模型可见数=" + 转字符串(长度(模型可见条目(条目, 空配置)))

  # ---------- B. 硬白名单 ----------
  设 白 为 ["读文件", "bash", "mcp__*"]
  设 锁配置 为 造可见性配置(白, 空名单)
  设 面1 为 装配可见工具面(条目, 锁配置)
  打印 "锁_可见=" + 逗号连接(面1["顺序"])
  打印 "锁_剪枝=" + 逗号连接(面1["剪枝"])
  打印 "锁_可见数=" + 转字符串(长度(面1["schema"]))
  打印 "锁_剪枝数=" + 转字符串(长度(面1["剪枝"]))
  打印 "锁_总数=" + 转字符串(面1["总数"])
  打印 "锁_模型可见=" + 逗号连接(名字表(模型可见条目(条目, 锁配置)))
  打印 "锁_报告可见=" + 转字符串(可见性报告(条目, 锁配置)["可见"])
  打印 "锁_报告剪枝=" + 转字符串(可见性报告(条目, 锁配置)["剪枝"])

  # ---------- C. 软聚焦 ----------
  设 聚 为 ["写文件", "搜索文件"]
  设 聚配置 为 造可见性配置(空名单, 聚)
  设 面2 为 装配可见工具面(条目, 聚配置)
  打印 "聚_可见数=" + 转字符串(长度(面2["schema"]))
  打印 "聚_顺序=" + 逗号连接(面2["顺序"])
  打印 "聚_聚焦=" + 逗号连接(面2["聚焦"])
  打印 "聚_剪枝数=" + 转字符串(长度(面2["剪枝"]))
  打印 "聚_首有键=" + 布尔文本(有聚焦键(面2["schema"][0]))
  打印 "聚_首标记=" + 布尔文本(面2["schema"][0]["聚焦"])
  打印 "聚_次标记=" + 布尔文本(面2["schema"][1]["聚焦"])
  打印 "聚_第三有键=" + 布尔文本(有聚焦键(面2["schema"][2]))
  打印 "聚_带聚焦键数=" + 转字符串(带聚焦键数(面2["schema"]))

  # ---------- D. 两级叠加 ----------
  设 白三 为 ["bash", "读文件", "写文件"]
  设 聚三 为 ["搜索文件", "写文件"]
  设 合配置 为 造可见性配置(白三, 聚三)
  设 面3 为 装配可见工具面(条目, 合配置)
  打印 "合_可见=" + 逗号连接(面3["顺序"])
  打印 "合_聚焦=" + 逗号连接(面3["聚焦"])
  打印 "合_剪枝=" + 逗号连接(面3["剪枝"])

  # ---------- E. preset 注入 ----------
  设 直预设 为 {"id": "standard", "allowedTools": ["bash"], "focusedTools": ["写文件"]}
  设 视一 为 预设可见性(直预设)
  打印 "预设_允许=" + 逗号连接(视一["allowedTools"])
  打印 "预设_聚焦=" + 逗号连接(视一["focusedTools"])
  打印 "预设_硬白名单=" + 布尔文本(硬白名单开启(视一))
  设 面四 为 装配可见工具面(条目, 视一)
  打印 "预设_装配可见=" + 逗号连接(面四["顺序"])
  设 嵌预设 为 {"id": "sub", "config": {"allowedTools": ["读文件"], "允许工具": ["bash"]}, "选项": {"focusedTools": ["搜索文件"]}}
  设 视二 为 预设可见性(嵌预设)
  打印 "嵌套_允许=" + 逗号连接(视二["allowedTools"])
  打印 "嵌套_聚焦=" + 逗号连接(视二["focusedTools"])
  设 裸预设 为 {"id": "standard"}
  设 视三 为 预设可见性(裸预设)
  打印 "裸预设_允许数=" + 转字符串(长度(视三["allowedTools"]))
  打印 "裸预设_聚焦数=" + 转字符串(长度(视三["focusedTools"]))
  打印 "裸预设_硬白名单=" + 布尔文本(硬白名单开启(视三))
  设 纯聚预设 为 {"id": "standard", "focusedTools": ["写文件"]}
  设 视四 为 预设可见性(纯聚预设)
  打印 "纯聚_硬白名单=" + 布尔文本(硬白名单开启(视四))
  打印 "纯聚_聚焦=" + 逗号连接(视四["focusedTools"])
  设 面五 为 装配可见工具面(条目, 视四)
  打印 "纯聚_可见数=" + 转字符串(长度(面五["schema"]))
  打印 "纯聚_首名=" + 面五["顺序"][0]

  # ---------- F. 通配与单名匹配 ----------
  打印 "通配_mcp=" + 布尔文本(名匹配模式("mcp__*", "mcp__hive__hive_claim"))
  打印 "通配_非=" + 布尔文本(名匹配模式("mcp__*", "bash"))
  打印 "全名_同=" + 布尔文本(名匹配模式("bash", "bash"))
  打印 "全名_不误判=" + 布尔文本(名匹配模式("bash", "bash2"))
  打印 "空模式=" + 布尔文本(名匹配模式("", "bash"))
  设 单白 为 ["bash"]
  设 单配 为 造可见性配置(单白, 空名单)
  打印 "工具可见_内=" + 布尔文本(工具可见("bash", 单配))
  打印 "工具可见_外=" + 布尔文本(工具可见("写文件", 单配))

  # ---------- G. 接线：组合过滤 → 可见性收口 ----------
  设 组合名表 为 ["tool-fs-read", "tool-fs-write", "tool-todo"]
  设 组合条目 为 造条目(组合名表)
  设 线配零 为 {}
  设 线零 为 按预设过滤可见(组合条目, "standard", 线配零)
  打印 "接线_无配_可见=" + 逗号连接(名字表(线零[0]))
  打印 "接线_无配_剪枝数=" + 转字符串(长度(线零[2]))
  设 线白 为 ["tool-fs-read"]
  设 线配一 为 造可见性配置(线白, 空名单)
  设 线一 为 按预设过滤可见(组合条目, "standard", 线配一)
  打印 "接线_白_可见=" + 逗号连接(名字表(线一[0]))
  打印 "接线_白_剪枝=" + 逗号连接(线一[2])
  设 预设字典 为 {"id": "standard", "config": {"allowedTools": ["tool-fs-read", "tool-todo"], "focusedTools": ["tool-todo"]}}
  设 线二 为 预设字典可见(组合条目, 预设字典)
  打印 "接线_预设_可见=" + 逗号连接(名字表(线二[0]))
  打印 "接线_预设_顺序=" + 逗号连接(线二[3]["顺序"])
  打印 "接线_预设_剪枝=" + 逗号连接(线二[2])
主程()
'''


def _run(driver_text):
    key = 'main'
    if key in _CACHE:
        return _CACHE[key]
    d = tempfile.mkdtemp(prefix='t0497_')
    path = os.path.join(d, 't0497_driver.light')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(driver_text)
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, RUNNER, path], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC, env=env)
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    out = proc.stdout + proc.stderr
    _CACHE[key] = (proc.returncode, out, kv)
    return _CACHE[key]


def _missing_module(out):
    return ('lightplugin' in out and
            ('ModuleNotFound' in out or '导入失败' in out or 'No module' in out))


def _kv():
    rc, out, kv = _run(DRIVER)
    assert rc == 0, out
    assert '无配置_可见数' in kv, ('驱动脚本没有输出，可能是光明编译失败', out)
    return kv


ALL_NAMES = ['bash', '读文件', '写文件', '编辑文件', '搜索文件', '技能列表',
             'web_search', '网页抓取', 'mcp__hive__hive_claim',
             'mcp__hive__hive_submit', '派发子任务', 'present']


def test_无配置时工具面与改动前一致():
    kv = _kv()
    # 12 个工具一个不少，顺序与序号都与输入逐项一致
    assert kv.get('无配置_可见数') == '12', kv.get('无配置_可见数')
    assert kv.get('无配置_剪枝数') == '0'
    assert kv.get('无配置_聚焦数') == '0'
    assert kv.get('无配置_顺序') == ','.join(ALL_NAMES)
    assert kv.get('无配置_序号') == ','.join(str(i) for i in range(12))
    # 无配置时不得给条目加聚焦键（形状与改动前一致）
    assert kv.get('无配置_带聚焦键数') == '0'
    assert kv.get('无配置_硬白名单') in ('假', 'False')
    assert kv.get('无配置_模型可见数') == '12'
    # 造可见性配置() 的默认形状（两个空表）同样不剪枝
    assert kv.get('造配置_可见数') == '12'
    assert kv.get('造配置_顺序') == ','.join(ALL_NAMES)
    assert kv.get('造配置_硬白名单') in ('假', 'False')


def test_硬白名单名单外工具进不了schema():
    kv = _kv()
    visible = [x for x in kv.get('锁_可见', '').split(',') if x]
    pruned = [x for x in kv.get('锁_剪枝', '').split(',') if x]
    assert visible == ['bash', '读文件', 'mcp__hive__hive_claim', 'mcp__hive__hive_submit'], visible
    assert '写文件' not in visible and '编辑文件' not in visible, visible
    assert '写文件' in pruned and '搜索文件' in pruned and 'present' in pruned, pruned
    assert kv.get('锁_可见数') == '4'
    assert kv.get('锁_剪枝数') == '8'
    # 模型可见条目 = schema（同一份剪枝结果），没有「先发给模型再撤回」的中间态
    assert kv.get('锁_模型可见') == kv.get('锁_可见')
    assert kv.get('锁_报告可见') == '4'
    assert kv.get('锁_报告剪枝') == '8'


def test_剪枝发生在schema构建之前():
    kv = _kv()
    visible = [x for x in kv.get('锁_可见', '').split(',') if x]
    pruned = [x for x in kv.get('锁_剪枝', '').split(',') if x]
    assert set(visible).isdisjoint(set(pruned)), (visible, pruned)
    assert int(kv.get('锁_总数', '0')) == len(visible) + len(pruned)
    # 被剪掉的工具名一个都不能出现在 schema 里
    for name in pruned:
        assert name not in visible, name
    assert kv.get('锁_模型可见') == kv.get('锁_可见')


def test_软聚焦不剪枝只前置打标():
    kv = _kv()
    order = [x for x in kv.get('聚_顺序', '').split(',') if x]
    assert kv.get('聚_可见数') == '12', order
    assert kv.get('聚_剪枝数') == '0'
    # 聚焦项前置，其余保持注册表原顺序
    assert order[:2] == ['写文件', '搜索文件'], order
    assert order[2:] == ['bash', '读文件', '编辑文件', '技能列表', 'web_search',
                         '网页抓取', 'mcp__hive__hive_claim',
                         'mcp__hive__hive_submit', '派发子任务', 'present'], order
    # 非聚焦工具仍然在面里（可调用），只是没有聚焦标记
    assert '编辑文件' in order
    assert kv.get('聚_聚焦') == '写文件,搜索文件'
    assert kv.get('聚_首有键') in ('真', 'True')
    assert kv.get('聚_首标记') in ('真', 'True')
    assert kv.get('聚_次标记') in ('真', 'True')
    assert kv.get('聚_第三有键') in ('假', 'False')
    assert kv.get('聚_带聚焦键数') == '2'


def test_两级叠加时先剪枝后聚焦():
    kv = _kv()
    order = [x for x in kv.get('合_可见', '').split(',') if x]
    assert order == ['写文件', 'bash', '读文件'], order
    # 搜索文件被硬白名单剪掉，因此不会出现在聚焦名单里
    assert kv.get('合_聚焦') == '写文件'
    pruned = [x for x in kv.get('合_剪枝', '').split(',') if x]
    assert '搜索文件' in pruned and '编辑文件' in pruned
    assert '写文件' not in pruned


def test_preset注入两种列表且默认不开硬白名单():
    kv = _kv()
    assert kv.get('预设_允许') == 'bash'
    assert kv.get('预设_聚焦') == '写文件'
    assert kv.get('预设_硬白名单') in ('真', 'True')
    assert kv.get('预设_装配可见') == 'bash'
    # config 子字典 + 中文键名同样生效
    assert kv.get('嵌套_允许') == '读文件,bash', kv.get('嵌套_允许')
    assert kv.get('嵌套_聚焦') == '搜索文件'
    # 未声明可见性的预设：两个名单都空，硬白名单不开启（常规会话红线）
    assert kv.get('裸预设_允许数') == '0'
    assert kv.get('裸预设_聚焦数') == '0'
    assert kv.get('裸预设_硬白名单') in ('假', 'False')
    # 只声明 focusedTools 时也不得开启硬白名单
    assert kv.get('纯聚_硬白名单') in ('假', 'False')
    assert kv.get('纯聚_聚焦') == '写文件'
    assert kv.get('纯聚_可见数') == '12'
    assert kv.get('纯聚_首名') == '写文件'


def test_通配与单名匹配口径():
    kv = _kv()
    assert kv.get('通配_mcp') in ('真', 'True')
    assert kv.get('通配_非') in ('假', 'False')
    assert kv.get('全名_同') in ('真', 'True')
    assert kv.get('全名_不误判') in ('假', 'False')
    assert kv.get('空模式') in ('假', 'False')
    assert kv.get('工具可见_内') in ('真', 'True')
    assert kv.get('工具可见_外') in ('假', 'False')


def test_接线按预设过滤可见():
    rc, out, kv = _run(DRIVER)
    if rc != 0 and _missing_module(out):
        import pytest
        pytest.skip('本机缺 lightplugin 兄弟仓：接线用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    # 未配置可见性时，组合过滤结果原样透传（向后兼容）
    assert kv.get('接线_无配_可见') == 'tool-fs-read,tool-fs-write,tool-todo'
    assert kv.get('接线_无配_剪枝数') == '0'
    # 硬白名单在组合过滤之后再收口
    assert kv.get('接线_白_可见') == 'tool-fs-read'
    assert kv.get('接线_白_剪枝') == 'tool-fs-write,tool-todo'
    # 预设字典自带配置：先按 standard 组合过滤，再剪枝 + 聚焦重排
    assert kv.get('接线_预设_可见') == 'tool-todo,tool-fs-read', kv.get('接线_预设_可见')
    assert kv.get('接线_预设_顺序') == 'tool-todo,tool-fs-read', kv.get('接线_预设_顺序')
    assert kv.get('接线_预设_剪枝') == 'tool-fs-write', kv.get('接线_预设_剪枝')

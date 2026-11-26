# -*- coding: utf-8 -*-
"""T-0506：W3/T3.3 错误消息增强 —— suggestion 可操作化（field/reason/suggestion）。

判据不是「有建议」，而是「模型照建议改一次就能过」。本文件钉四层：

  1. 期望结构层：字段缺失 / 类型错（期望 object、array）时，建议带上**由子 schema 渲染
     的骨架**（键名 + 占位类型），标量错误不强塞结构示例（不添噪）；
  2. 取值域层：枚举越界给出完整合法域，且只在**真像**时才给「最接近的合法值」
     （换一套 enum，建议随之变化；不像就闭嘴，不误导）；
  3. 执行规则层：唯一命中失败（编辑文件类）给出「命中几处、行号、三条收窄路径」，
     0 命中给出核对原文字面的办法；路径越界给出**当前真实工具根**与越界形态；
  4. 同族/接线层：新信封与 T-0504/T-0505 **键集逐字相同**（十键，不新增字段）；
     近似工具名建议指向 ctx_assembly 的 mode 决策树（与 W1/T-0499 同一张表），
     且 校验模型参数 的 ok/skipped 语义不变。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

# 与 T-0450 / T-0504 / T-0505 同族的十键（顺序即字典键顺序）
ENVELOPE_KEYS = ("['type', 'errorType', 'code', 'field', 'reason', 'message', "
                 "'suggestion', 'retryable', 'traceId', 'details']")

# ---- 驱动 1：期望结构示例（缺字段 / 类型错 / 数组）----
STRUCT_DRIVER = '''
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷, 期望结构示例

段落 报(标签, 模式, 参数):
  设 载 为 校验失败载荷(校验参数(模式, 参数), 模式, 参数)
  打印 标签 + "_字段=" + 转字符串(载["field"])
  打印 标签 + "_原因=" + 转字符串(载["reason"])
  打印 标签 + "_建议=" + 转字符串(载["suggestion"])
  返回 载

段落 主程():
  # a) 缺一个嵌套对象字段：建议要给出该对象的骨架（键名 + 占位类型）
  设 缺模 为 {"type": "object", "properties": {
    "配置": {"type": "object", "properties": {"超时": {"type": "number"},
      "重试": {"type": "integer"}}, "required": ["超时"]}}, "required": ["配置"]}
  报("缺对象", 缺模, {})

  # b) 类型错且期望是对象：给出骨架，否则模型仍要猜键名
  设 嵌模 为 {"type": "object", "properties": {"配置": {"type": "object",
    "properties": {"超时": {"type": "number"}}, "required": ["超时"]}}}
  报("型对象", 嵌模, {"配置": "不是对象"})

  # c) 类型错且期望是数组：给出元素骨架
  设 列模 为 {"type": "object", "properties": {
    "标签": {"type": "array", "items": {"type": "string"}}}}
  报("型数组", 列模, {"标签": "不是数组"})

  # d) 标量缺字段：不许硬塞结构示例（旧文案口径不变）
  设 标模 为 {"type": "object", "properties": {"秒": {"type": "number"}},
    "required": ["秒"]}
  报("缺标量", 标模, {})

  # e) 单层键太多：骨架折叠，不许无限长
  设 宽模 为 {"type": "object", "properties": {"配置": {"type": "object",
    "properties": {"甲": {"type": "string"}, "乙": {"type": "string"},
      "丙": {"type": "string"}, "丁": {"type": "string"},
      "戊": {"type": "string"}}}}, "required": ["配置"]}
  报("宽对象", 宽模, {})

  # f) 标量模式的 期望结构示例 必须是空串（决定「加不加结构示例」的闸门）
  打印 "标量闸=" + 转字符串(期望结构示例({"type": "number"}) == "")
  打印 "对象闸=" + 转字符串(期望结构示例({"type": "object", "properties": {
    "k": {"type": "string"}}}) != "")
主程()
'''

# ---- 驱动 2：枚举合法域 + 近似值（只有真像才给）----
ENUM_DRIVER = '''
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷

段落 报(标签, 模式, 参数):
  设 载 为 校验失败载荷(校验参数(模式, 参数), 模式, 参数)
  打印 标签 + "_建议=" + 转字符串(载["suggestion"])
  返回 载

段落 主程():
  设 甲模 为 {"type": "object", "properties": {
    "色": {"type": "string", "enum": ["红", "绿", "深蓝"]}}, "required": ["色"]}
  报("甲", 甲模, {"色": "蓝"})

  设 乙模 为 {"type": "object", "properties": {
    "色": {"type": "string", "enum": ["甲", "乙"]}}, "required": ["色"]}
  报("乙", 乙模, {"色": "丙"})

  设 丙模 为 {"type": "object", "properties": {
    "mode": {"type": "string", "enum": ["select", "assemble", "report"]}},
    "required": ["mode"]}
  报("丙", 丙模, {"mode": "assmble"})

  设 丁模 为 {"type": "object", "properties": {
    "级": {"type": "string", "enum": ["公开", "可逆"]}}, "required": ["级"]}
  报("丁", 丁模, {"级": "不可逆"})
主程()
'''

# ---- 驱动 3：唯一命中失败（多命中 / 零命中 / 单命中）----
EDIT_DRIVER = '''
从 错误增强 导入 造编辑命中错误, 造唯一命中建议

段落 查(标签, 信封):
  打印 标签 + "_键=" + 转字符串(字典键列表(信封))
  打印 标签 + "_类型=" + 转字符串(信封["type"])
  打印 标签 + "_细分=" + 转字符串(信封["errorType"])
  打印 标签 + "_码=" + 转字符串(信封["code"])
  打印 标签 + "_字段=" + 转字符串(信封["field"])
  打印 标签 + "_原因=" + 转字符串(信封["reason"])
  打印 标签 + "_可重试=" + 转字符串(信封["retryable"])
  打印 标签 + "_详情=" + 转字符串(信封["details"])

段落 主程():
  设 多 为 造编辑命中错误(3, [12, 40, 77], 210)
  查("多", 多)
  打印 "多_建议=" + 转字符串(多["suggestion"])

  设 零 为 造编辑命中错误(0, [], 88)
  查("零", 零)
  打印 "零_建议=" + 转字符串(零["suggestion"])

  设 单 为 造唯一命中建议(1, [7], 20)
  打印 "单_建议=" + 转字符串(单)

  # 行号超过上限要折叠（不让建议比错误本身更长）
  设 长 为 造唯一命中建议(9, [1, 2, 3, 4, 5, 6, 7], 300)
  打印 "长_建议=" + 转字符串(长)

  # 已显式传 全部替换=真 仍多命中：不是「再传一次」，而是让模型先核对文件
  设 全 为 造编辑命中错误(2, [5, 9], 40, 真)
  打印 "全_建议=" + 转字符串(全["suggestion"])
主程()
'''

# ---- 驱动 4：路径越界（真实护栏 + 真实根）----
PATH_DRIVER = '''
从 错误增强 导入 造路径越界错误, 造路径越界建议
从 工具_路径安全 导入 解析安全路径, 取根目录

段落 主程():
  设 根 为 取根目录()
  设 安 为 解析安全路径(根, "../etc/passwd")
  打印 "安_ok=" + 转字符串(安["ok"])
  打印 "安_理由=" + 转字符串(安["理由"])
  设 绝 为 解析安全路径(根, "/etc/passwd")
  打印 "绝_ok=" + 转字符串(绝["ok"])

  设 错 为 造路径越界错误("../etc/passwd", 根, 安["理由"])
  打印 "错_键=" + 转字符串(字典键列表(错))
  打印 "错_类型=" + 转字符串(错["type"])
  打印 "错_细分=" + 转字符串(错["errorType"])
  打印 "错_码=" + 转字符串(错["code"])
  打印 "错_字段=" + 转字符串(错["field"])
  打印 "错_原因=" + 转字符串(错["reason"])
  打印 "错_可重试=" + 转字符串(错["retryable"])
  打印 "错_消息=" + 转字符串(错["message"])
  打印 "错_建议=" + 转字符串(错["suggestion"])
  打印 "错_根=" + 转字符串(错["details"]["根"])

  打印 "绝_建议=" + 造路径越界建议("/etc/passwd", "/srv/app")
  打印 "盘_建议=" + 造路径越界建议("C:\\\\Windows\\\\x", "/srv/app")
  打印 "普_建议=" + 造路径越界建议("a/b/c", "/srv/app")
主程()
'''

# ---- 驱动 5：多条错误时文案铺开全部字段（一轮改完）----
MULTI_DRIVER = '''
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷, 校验失败文案, 校验改正清单

段落 主程():
  设 多模 为 {"type": "object", "properties": {"甲": {"type": "string"},
    "乙": {"type": "number"}}, "required": ["甲", "乙"]}
  设 载 为 校验失败载荷(校验参数(多模, {}), 多模, {})
  打印 "条数=" + 转字符串(长(载["validationErrors"]))
  打印 "文案=" + 校验失败文案(载)
  打印 "清单=" + 校验改正清单(载)

  设 单模 为 {"type": "object", "properties": {"甲": {"type": "string"}},
    "required": ["甲"]}
  设 单载 为 校验失败载荷(校验参数(单模, {}), 单模, {})
  打印 "单_文案=" + 校验失败文案(单载)
  打印 "单_清单=" + 转字符串(校验改正清单(单载) == "")
主程()
'''

# ---- 驱动 6：近似工具名 → 兄弟工具 / ctx_assembly（与 T-0499 决策树同源）----
TOOLNAME_DRIVER = '''
从 工具面装配 导入 参数模式表, 工具名建议, ctx装配决策树, ctx装配模式表

段落 主程():
  设 模 为 {"type": "object", "properties": {"mode": {"type": "string"}},
    "required": ["mode"]}
  设 表 为 参数模式表([
    {"工具名": "ctx_assembly", "参数模式": 模},
    {"工具名": "读文件", "参数模式": 模},
    {"工具名": "写文件", "参数模式": 模}])
  打印 "表=" + 转字符串(字典键列表(表))

  # a) 旧名（T-0499 四合一前的四个名字）→ ctx_assembly + mode
  打印 "旧_上下文装配=" + 工具名建议(表, "上下文装配")
  打印 "旧_压缩选块=" + 工具名建议(表, "压缩选块")
  打印 "旧_报告=" + 工具名建议(表, "装配报告")
  打印 "树=" + ctx装配决策树()

  # b) 拼错的兄弟工具 → 指向最像的那个
  打印 "错_读文件=" + 工具名建议(表, "读文件x")
  打印 "错_搜索=" + 工具名建议(表, "搜文件")

  # c) 一个都不像 → 摊开可用工具（不瞎指）
  打印 "不像=" + 工具名建议(表, "图片识别")

  # d) 名正确 → 无建议
  打印 "正=" + 转字符串(工具名建议(表, "读文件") == "")
  打印 "空表=" + 转字符串(工具名建议({}, "读文件") == "")

  # e) ctx_assembly 不在可见面时，不许把模型支过去（改成列清单）
  设 窄 为 参数模式表([{"工具名": "读文件", "参数模式": 模}])
  设 窄建议 为 工具名建议(窄, "上下文装配")
  打印 "窄_提ctx=" + 转字符串(字符串包含(窄建议, "ctx_assembly"))
  打印 "窄_建议=" + 窄建议
主程()
'''

# ---- 驱动 7：校验入口接线（ok/skipped 语义不变）+ 信封同族 ----
WIRE_DRIVER = '''
从 工具面装配 导入 参数模式表, 校验模型参数
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷, 造编辑命中错误

段落 校验入口(模式, 参数):
  设 原始 为 校验参数(模式, 参数)
  如果 长(原始) == 0:
    返回 {"通过": 真}
  返回 {"通过": 假, "载荷": 校验失败载荷(原始, 模式, 参数)}

段落 主程():
  设 模 为 {"type": "object", "properties": {"mode": {"type": "string", "enum": ["装配"]}},
    "required": ["mode"]}
  设 表 为 参数模式表([{"工具名": "ctx_assembly", "参数模式": 模},
    {"工具名": "读文件", "参数模式": 模}])

  设 旧 为 校验模型参数(表, "上下文装配", {}, 校验入口)
  打印 "旧_ok=" + 转字符串(旧["ok"])
  打印 "旧_跳过=" + 转字符串(旧["skipped"])
  打印 "旧_有建议=" + 转字符串(字典包含键(旧, "工具名建议"))
  打印 "旧_建议=" + 转字符串(字典获取(旧, "工具名建议", ""))

  设 裸 为 校验模型参数(表, "读文件", {}, 空)
  打印 "裸_ok=" + 转字符串(裸["ok"])
  打印 "裸_跳过=" + 转字符串(裸["skipped"])
  打印 "裸_键=" + 转字符串(字典键列表(裸))

  设 好 为 校验模型参数(表, "读文件", {"mode": "装配"}, 校验入口)
  打印 "好_ok=" + 转字符串(好["ok"])
  打印 "好_跳过=" + 转字符串(好["skipped"])
  打印 "好_键=" + 转字符串(字典键列表(好))

  设 坏 为 校验模型参数(表, "读文件", {"mode": "选块"}, 校验入口)
  打印 "坏_ok=" + 转字符串(坏["ok"])
  打印 "坏_字段=" + 转字符串(坏["field"])
  打印 "坏_建议=" + 转字符串(坏["suggestion"])

  # 同族：编辑命中信封与校验信封键集逐字相同（不许为可操作化新开字段）
  设 编 为 造编辑命中错误(2, [5, 9], 40)
  打印 "编_键=" + 转字符串(字典键列表(编))
主程()
'''

# ---- 驱动 8：建议来自真实规则（换 schema 建议就变），不是写死的表 ----
DERIVED_DRIVER = '''
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷

段落 意(模式, 参数):
  设 载 为 校验失败载荷(校验参数(模式, 参数), 模式, 参数)
  返回 转字符串(载["suggestion"])

段落 主程():
  设 甲 为 意({"type": "object", "properties": {
    "配置": {"type": "object", "properties": {"超时": {"type": "number"}}}},
    "required": ["配置"]}, {})
  设 乙 为 意({"type": "object", "properties": {
    "参数包": {"type": "object", "properties": {"重试次数": {"type": "integer"}}}},
    "required": ["参数包"]}, {})
  打印 "甲=" + 甲
  打印 "乙=" + 乙
  打印 "不同=" + 转字符串(甲 != 乙)
  打印 "甲含乙键=" + 转字符串(字符串包含(甲, "重试次数"))

  设 枚甲 为 意({"type": "object", "properties": {
    "级": {"type": "string", "enum": ["公开", "可逆"]}}, "required": ["级"]}, {"级": "不可逆"})
  设 枚乙 为 意({"type": "object", "properties": {
    "级": {"type": "string", "enum": ["只读", "可写"]}}, "required": ["级"]}, {"级": "不可逆"})
  打印 "枚甲=" + 枚甲
  打印 "枚乙=" + 枚乙
  打印 "枚不同=" + 转字符串(枚甲 != 枚乙)
主程()
'''


def _run(driver, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC, env=env)
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, proc.stdout + proc.stderr, kv


def test_缺字段建议给出期望结构(tmp_path):
    rc, out, kv = _run(STRUCT_DRIVER, tmp_path, 't0506_struct.light')
    assert rc == 0, out
    assert kv.get('缺对象_字段') == '参数.配置', out
    assert kv.get('缺对象_原因') == 'missing', out
    sug = kv.get('缺对象_建议', '')
    assert '缺少必填字段 配置' in sug, out
    assert 'object' in sug, out
    # 骨架来自 schema：键名 + 占位类型都在
    assert '期望结构示例' in sug, out
    assert '"超时": <number>' in sug, out
    assert '"重试": <integer>' in sug, out


def test_类型错建议给出期望结构(tmp_path):
    rc, out, kv = _run(STRUCT_DRIVER, tmp_path, 't0506_struct2.light')
    assert rc == 0, out
    obj = kv.get('型对象_建议', '')
    assert '类型应为 object' in obj, out
    assert '当前为 string' in obj, out
    assert '"超时": <number>' in obj, out
    arr = kv.get('型数组_建议', '')
    assert '类型应为 array' in arr, out
    assert '[<string>]' in arr, out


def test_标量错误不塞结构示例(tmp_path):
    rc, out, kv = _run(STRUCT_DRIVER, tmp_path, 't0506_struct3.light')
    assert rc == 0, out
    # 旧口径原样保留（T-0504 的等值判据）
    assert kv.get('缺标量_建议') == '缺少必填字段 秒（number）', out
    assert '期望结构示例' not in kv.get('缺标量_建议', ''), out
    assert kv.get('标量闸') in ('True', '真'), out
    assert kv.get('对象闸') in ('True', '真'), out


def test_结构示例单层折叠(tmp_path):
    rc, out, kv = _run(STRUCT_DRIVER, tmp_path, 't0506_struct4.light')
    assert rc == 0, out
    sug = kv.get('宽对象_建议', '')
    assert '期望结构示例' in sug, out
    assert '…' in sug, out
    # 只列前 3 个键（不把 5 个键全铺开）
    assert '"丁"' not in sug, out
    assert '"戊"' not in sug, out


def test_枚举建议给出合法域与近似值(tmp_path):
    rc, out, kv = _run(ENUM_DRIVER, tmp_path, 't0506_enum.light')
    assert rc == 0, out
    a = kv.get('甲_建议', '')
    assert '红|绿|深蓝' in a, out
    assert '当前为 蓝' in a, out
    assert '最接近的合法值：深蓝' in a, out
    # 拼写错（英文）也要能挑出最近的
    c = kv.get('丙_建议', '')
    assert 'select|assemble|report' in c, out
    assert '最接近的合法值：assemble' in c, out


def test_枚举不像就不给近似值(tmp_path):
    rc, out, kv = _run(ENUM_DRIVER, tmp_path, 't0506_enum2.light')
    assert rc == 0, out
    # 丙 vs 甲|乙：毫无共同字符 → 不许编一个「最接近」
    b = kv.get('乙_建议', '')
    assert '甲|乙' in b, out
    assert '最接近' not in b, out
    # 不可逆 vs 公开|可逆：字面有重合但方向是反的，仍按相似度给（可逆），
    # 关键是建议里必须同时出现完整合法域，模型不会因此走错
    d = kv.get('丁_建议', '')
    assert '公开|可逆' in d, out


def test_唯一命中失败_多命中(tmp_path):
    rc, out, kv = _run(EDIT_DRIVER, tmp_path, 't0506_edit.light')
    assert rc == 0, out
    assert kv.get('多_键') == ENVELOPE_KEYS, out
    assert kv.get('多_类型') == 'runtime', out
    assert kv.get('多_细分') == 'internal', out
    assert kv.get('多_码') == 'TOOL_INTERNAL_ERROR', out
    assert kv.get('多_字段') == '参数.旧文本', out
    assert kv.get('多_原因') == 'editMultiMatch', out
    assert kv.get('多_可重试') in ('False', '假'), out
    sug = kv.get('多_建议', '')
    # 命中几处、在哪、怎么缩小范围 —— 三条路都要在
    assert '命中 3 处' in sug, out
    assert '行号 [12, 40, 77]' in sug, out
    assert '全部替换=真' in sug, out
    assert '插入行' in sug, out
    assert '210 行' in sug, out
    # 详情带真实执行数据，可回放
    assert "'命中次数': 3" in kv.get('多_详情', ''), out
    assert "'行号': [12, 40, 77]" in kv.get('多_详情', ''), out


def test_唯一命中失败_零命中(tmp_path):
    rc, out, kv = _run(EDIT_DRIVER, tmp_path, 't0506_edit2.light')
    assert rc == 0, out
    assert kv.get('零_类型') == 'runtime', out
    assert kv.get('零_细分') == 'notFound', out
    assert kv.get('零_码') == 'TOOL_NOT_FOUND', out
    assert kv.get('零_原因') == 'editNoMatch', out
    sug = kv.get('零_建议', '')
    assert '0 命中' in sug, out
    assert '共 88 行' in sug, out
    # 必须告诉它下一步做什么（核对字面 / 换更短更唯一的片段），而不是只说失败
    assert '读文件' in sug, out
    assert '逐字一致' in sug, out
    # 单命中：说明「本该通过」，指向传参/文件搞错
    assert '只命中 1 处' in kv.get('单_建议', ''), out
    # 行号折叠
    assert '…' in kv.get('长_建议', ''), out
    # 已经全替换过就别再让它全替换一次：改成「先核对目标文件」
    allr = kv.get('全_建议', '')
    assert '已传 全部替换=真' in allr, out
    assert '读文件' in allr, out


def test_路径越界建议给真实根与形态(tmp_path):
    rc, out, kv = _run(PATH_DRIVER, tmp_path, 't0506_path.light')
    assert rc == 0, out
    # 先用真实护栏确认「确实越界」，再拿它的理由造信封（建议不是凭空写的）
    assert kv.get('安_ok') in ('False', '假'), out
    assert '超出项目根目录范围' in kv.get('安_理由', ''), out
    assert kv.get('绝_ok') in ('False', '假'), out

    assert kv.get('错_键') == ENVELOPE_KEYS, out
    assert kv.get('错_类型') == 'validation', out
    assert kv.get('错_细分') == 'schema', out
    assert kv.get('错_码') == 'PARAM_SCHEMA_INVALID', out
    assert kv.get('错_字段') == '参数.路径', out
    assert kv.get('错_原因') == 'pathEscape', out
    assert kv.get('错_可重试') in ('False', '假'), out
    assert '超出项目根目录范围' in kv.get('错_消息', ''), out

    sug = kv.get('错_建议', '')
    assert '相对路径' in sug, out
    assert '..' in sug, out
    assert kv.get('错_根') not in ('', 'None'), out
    assert kv.get('错_根') in sug, out   # 用的是当前真实工具根

    assert '绝对路径' in kv.get('绝_建议', ''), out
    assert '盘符' in kv.get('盘_建议', ''), out
    assert '相对路径' in kv.get('普_建议', ''), out


def test_多错误文案铺开全部字段(tmp_path):
    rc, out, kv = _run(MULTI_DRIVER, tmp_path, 't0506_multi.light')
    assert rc == 0, out
    assert kv.get('条数') == '2', out
    text = kv.get('文案', '')
    # 旧口径不回归
    assert '另有 1 处字段错误' in text, out
    # 新增：把剩下的字段与原因直接铺出来，模型一轮改完
    assert '参数.乙（missing）' in text, out
    assert kv.get('清单') == '参数.乙（missing）', out
    # 单条错误不加「另有」
    assert '另有' not in kv.get('单_文案', ''), out
    assert kv.get('单_清单') in ('True', '真'), out


def test_旧名工具指向ctx装配决策树(tmp_path):
    rc, out, kv = _run(TOOLNAME_DRIVER, tmp_path, 't0506_toolname.light')
    assert rc == 0, out
    tree = kv.get('树', '')
    assert 'mode=装配' in tree, out
    for label, mode in (('旧_上下文装配', '装配'), ('旧_压缩选块', '选块'),
                        ('旧_报告', '装配报告')):
        sug = kv.get(label, '')
        assert 'ctx_assembly' in sug, out
        assert 'mode=' + mode in sug, (label, out)
        # 口径与 T-0499 决策树同源：整段原文都在建议里，不是自己另写一句
        assert tree in sug, (label, out)


def test_拼错工具名指向兄弟工具(tmp_path):
    rc, out, kv = _run(TOOLNAME_DRIVER, tmp_path, 't0506_toolname2.light')
    assert rc == 0, out
    wrong = kv.get('错_读文件', '')
    assert '最接近的是「读文件」' in wrong, out
    assert '读文件x' in wrong, out
    assert kv.get('错_搜索', '').count('写文件') == 0, out
    # 都不像：摊开可用工具名，不瞎指
    far = kv.get('不像', '')
    assert 'ctx_assembly' in far and '读文件' in far and '写文件' in far, out
    # 正确的名 / 空表：不出建议
    assert kv.get('正') in ('True', '真'), out
    assert kv.get('空表') in ('True', '真'), out


def test_不可见时不许支到ctx装配(tmp_path):
    rc, out, kv = _run(TOOLNAME_DRIVER, tmp_path, 't0506_toolname3.light')
    assert rc == 0, out
    assert kv.get('窄_提ctx') in ('False', '假'), out
    assert '读文件' in kv.get('窄_建议', ''), out


def test_校验入口未知工具带建议但不改语义(tmp_path):
    rc, out, kv = _run(WIRE_DRIVER, tmp_path, 't0506_wire.light')
    assert rc == 0, out
    # 旧名：仍旧「跳过」，但带上该调谁
    assert kv.get('旧_ok') in ('True', '真'), out
    assert kv.get('旧_跳过') in ('True', '真'), out
    assert kv.get('旧_有建议') in ('True', '真'), out
    assert 'ctx_assembly' in kv.get('旧_建议', ''), out
    # 名在表里但没注入入口：跳过且不带建议键（成功路径返回结构不变）
    assert kv.get('裸_跳过') in ('True', '真'), out
    assert kv.get('裸_键') == "['ok', 'skipped']", out
    # 合法参数：通过路径四键口径不变（ok/skipped 两项）
    assert kv.get('好_ok') in ('True', '真'), out
    assert kv.get('好_跳过') in ('False', '假'), out
    assert kv.get('好_键') == "['ok', 'skipped']", out
    # 非法参数：仍走校验信封（建议含真实合法域）
    assert kv.get('坏_ok') in ('False', '假'), out
    assert kv.get('坏_字段') == '参数.mode', out
    assert '装配' in kv.get('坏_建议', ''), out
    assert kv.get('编_键') == ENVELOPE_KEYS, out


def test_建议随schema变化不是写死的表(tmp_path):
    rc, out, kv = _run(DERIVED_DRIVER, tmp_path, 't0506_derived.light')
    assert rc == 0, out
    assert kv.get('不同') in ('True', '真'), out
    assert kv.get('甲含乙键') in ('False', '假'), out
    assert '"超时": <number>' in kv.get('甲', ''), out
    assert '"重试次数": <integer>' in kv.get('乙', ''), out
    # 枚举近似值随 enum 变：同一句「不可逆」在两套 schema 下给出不同的近邻
    assert kv.get('枚不同') in ('True', '真'), out
    assert '公开|可逆' in kv.get('枚甲', ''), out
    assert '只读|可写' in kv.get('枚乙', ''), out

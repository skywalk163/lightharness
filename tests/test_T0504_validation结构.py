# -*- coding: utf-8 -*-
"""T-0504：W3/T3.1 统一 ValidationError 结构与 suggestion 字段。

判据三层：
  1. 契约层：校验失败返回同一只结构化信封（type/errorType/code/field/reason/
     message/suggestion/retryable/traceId/details），JSON 序列化键名固定、
     与 T-0505 运行时异常同族（type 区分大类，errorType 区分细分）；
  2. 建议层：suggestion 由真实 schema 推导（缺字段/类型错/枚举越界/额外字段/
     嵌套路径），换一套 schema 建议随之变化 —— 证明不是硬编码；
  3. 接线层：工具执行（串行 + 前置闸门）与工具面装配（模型面入口）都回结构化
     失败，且处理函数一次都不调用；成功路径返回结构仍是 状态/结果/错误码/消息 四键。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

# ---- 驱动 1：信封结构与 JSON 契约 ----
ENVELOPE_DRIVER = '''
从 错误增强 导入 造校验错误, 是校验错误, 信封可否重试
从 JSON 导入 序列化JSON, 解析JSON

段落 主程():
  设 e 为 造校验错误("参数.秒", "type", "参数.秒：期望 number 实际 字符串",
    "类型应为 number（当前为 string）", {"路径": ["参数", "秒"]})
  设 文 为 序列化JSON(e)
  打印 "原始串=" + 文
  设 b 为 解析JSON(文)
  打印 "type=" + 转字符串(b["type"])
  打印 "errorType=" + 转字符串(b["errorType"])
  打印 "code=" + 转字符串(b["code"])
  打印 "field=" + 转字符串(b["field"])
  打印 "reason=" + 转字符串(b["reason"])
  打印 "message=" + 转字符串(b["message"])
  打印 "suggestion=" + 转字符串(b["suggestion"])
  打印 "retryable=" + 转字符串(b["retryable"])
  打印 "traceId=" + 转字符串(b["traceId"])
  打印 "是校验错误=" + 转字符串(是校验错误(b))
  打印 "信封可否重试=" + 转字符串(信封可否重试(e))
  打印 "非校验错误判定=" + 转字符串(是校验错误({"type": "runtime"}))
主程()
'''

# ---- 驱动 2：建议由真实 schema 推导 ----
SUGGEST_DRIVER = '''
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷, 校验失败文案

段落 报(标签, 模式, 参数):
  设 载 为 校验失败载荷(校验参数(模式, 参数), 模式, 参数)
  打印 标签 + "_ok=" + 转字符串(载["ok"])
  打印 标签 + "_条数=" + 转字符串(长(载["validationErrors"]))
  打印 标签 + "_字段=" + 转字符串(载["field"])
  打印 标签 + "_原因=" + 转字符串(载["reason"])
  打印 标签 + "_建议=" + 转字符串(载["suggestion"])
  打印 标签 + "_文案=" + 校验失败文案(载)
  返回 载

段落 主程():
  设 缺模式 为 {"type": "object", "properties": {"秒": {"type": "number"}},
    "required": ["秒"]}
  设 缺载 为 报("缺", 缺模式, {})

  设 型模式 为 {"type": "object", "properties": {"秒": {"type": "number"}}}
  设 型载 为 报("型", 型模式, {"秒": "不是数字"})

  设 枚甲 为 {"type": "object", "properties": {"色": {"type": "string", "enum": ["红", "绿"]}},
    "required": ["色"]}
  设 枚甲载 为 报("枚甲", 枚甲, {"色": "蓝"})
  设 枚乙 为 {"type": "object", "properties": {"色": {"type": "string", "enum": ["甲", "乙"]}},
    "required": ["色"]}
  设 枚乙载 为 报("枚乙", 枚乙, {"色": "丙"})

  设 嵌模式 为 {"type": "object", "properties": {
    "配置": {"type": "object", "properties": {"超时": {"type": "number"}},
      "required": ["超时"]}}, "required": ["配置"]}
  设 嵌载 为 报("嵌", 嵌模式, {"配置": {"超时": "x"}})

  设 闭模式 为 {"type": "object", "properties": {"a": {"type": "string"}},
    "additionalProperties": 假}
  设 闭载 为 报("闭", 闭模式, {"a": "x", "b": "y"})

  设 多模式 为 {"type": "object", "properties": {"甲": {"type": "string"},
    "乙": {"type": "number"}}, "required": ["甲", "乙"]}
  设 多载 为 报("多", 多模式, {})

  设 列模式 为 {"type": "object", "properties": {
    "标签": {"type": "array", "items": {"type": "number"}}}, "required": ["标签"]}
  设 列载 为 报("列", 列模式, {"标签": ["不是数字"]})
  设 列少模式 为 {"type": "object", "properties": {
    "标签": {"type": "array", "items": {"type": "number"}, "minItems": 2}},
    "required": ["标签"]}
  设 列少载 为 报("列少", 列少模式, {"标签": [1]})

  设 合法 为 报("合法", 缺模式, {"秒": 3})
主程()
'''

# ---- 驱动 3：工具执行接线（串行 + 前置闸门） ----
EXEC_DRIVER = '''
从 工具执行 导入 建注册表, 具注册工具, 建执行器, 执行工具, 级公开, 具执行前置闸门, 具校验工具参数 
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷
从 JSON 导入 序列化JSON

设 计数 为 {"次": 0}

段落 处理(参数, 令牌):
  字典设置(计数, "次", 字典获取(计数, "次", 0) + 1)
  返回 {"收到": 参数}

# 校验入口（依赖注入）：(模式, 参数) → {"通过": 真} / {"通过": 假, "载荷": …}
段落 校验入口(模式, 参数):
  设 原始 为 校验参数(模式, 参数)
  如果 长(原始) == 0:
    返回 {"通过": 真}
  返回 {"通过": 假, "载荷": 校验失败载荷(原始, 模式, 参数)}

段落 主程():
  设 模式 为 {"type": "object", "properties": {
    "秒": {"type": "number"}, "颜色": {"type": "string", "enum": ["红", "绿"]}},
    "required": ["秒", "颜色"]}
  设 注册 为 建注册表()
  具注册工具(注册, "演示", 级公开, 处理, 空, 模式)
  设 执行器 为 建执行器(10, 1000, 0, "滑动窗口", 注册, 校验入口)

  设 坏 为 执行工具(执行器, "演示", 级公开, "测试", {"颜色": "蓝"}, 空)
  打印 "坏_状态=" + 转字符串(坏["状态"])
  打印 "坏_码=" + 转字符串(坏["错误码"])
  打印 "坏_可重试=" + 转字符串(坏["错误"]["retryable"])
  打印 "坏_大类=" + 转字符串(坏["错误"]["type"])
  打印 "坏_细分=" + 转字符串(坏["错误"]["errorType"])
  打印 "坏_字段=" + 转字符串(坏["错误"]["field"])
  打印 "坏_建议=" + 转字符串(坏["错误"]["suggestion"])
  打印 "坏_条数=" + 转字符串(长(坏["校验错误"]))
  打印 "坏_调用次数=" + 转字符串(字典获取(计数, "次", 0))
  打印 "坏_信封串=" + 序列化JSON(坏["错误"])

  设 好 为 执行工具(执行器, "演示", 级公开, "测试", {"秒": 1, "颜色": "红"}, 空)
  打印 "好_状态=" + 转字符串(好["状态"])
  打印 "好_键=" + 转字符串(字典键列表(好))
  打印 "好_结果=" + 转字符串(好["结果"]["收到"]["秒"])
  打印 "好_调用次数=" + 转字符串(字典获取(计数, "次", 0))

  打印 "闸_前=" + 转字符串(字典获取(计数, "次", 0))
  设 闸 为 具执行前置闸门(执行器, "演示", 级公开, "测试", {"颜色": "蓝"}, 空)
  打印 "闸_过=" + 转字符串(闸["过"])
  打印 "闸_码=" + 转字符串(闸["结果"]["错误码"])
  打印 "闸_建议=" + 转字符串(闸["结果"]["错误"]["suggestion"])
  打印 "闸_后=" + 转字符串(字典获取(计数, "次", 0))

  设 查询 为 具校验工具参数(取工具包装(注册), {"颜色": "蓝"}, 校验入口)
  打印 "查_过=" + 转字符串(查询["通过"])

段落 取工具包装(注册):
  返回 注册["工具表"]["演示"]
主程()
'''

# ---- 驱动 4：工具面装配模型面入口 ----
ASSEMBLY_DRIVER = '''
从 工具面装配 导入 参数模式表, 校验模型参数
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷, 校验失败文案

段落 校验入口(模式, 参数):
  设 原始 为 校验参数(模式, 参数)
  如果 长(原始) == 0:
    返回 {"通过": 真}
  返回 {"通过": 假, "载荷": 校验失败载荷(原始, 模式, 参数)}

段落 主程():
  设 模式 为 {"type": "object", "properties": {
    "颜色": {"type": "string", "enum": ["红", "绿"]}}, "required": ["颜色"]}
  设 条目表 为 [{"工具名": "演示", "参数模式": 模式}, {"工具名": "裸"},
    {"标识": "别名工具", "参数模式": 模式}]
  设 表 为 参数模式表(条目表)
  打印 "表数=" + 转字符串(长(表))
  设 坏 为 校验模型参数(表, "演示", {"颜色": "紫"}, 校验入口)
  打印 "坏_ok=" + 转字符串(坏["ok"])
  打印 "坏_字段=" + 转字符串(坏["field"])
  打印 "坏_建议=" + 转字符串(坏["suggestion"])
  打印 "坏_可重试=" + 转字符串(坏["retryable"])
  打印 "坏_文案=" + 校验失败文案(坏)
  设 跳 为 校验模型参数(表, "裸", {})
  打印 "跳_ok=" + 转字符串(跳["ok"])
  打印 "跳_跳过=" + 转字符串(跳["skipped"])
  设 知 为 校验模型参数(表, "不存在的工具", {})
  打印 "知_ok=" + 转字符串(知["ok"])
  设 合法 为 校验模型参数(表, "演示", {"颜色": "红"}, 校验入口)
  打印 "合法_ok=" + 转字符串(合法["ok"])
  打印 "合法_跳过=" + 转字符串(合法["skipped"])
  设 无入口 为 校验模型参数(表, "演示", {"颜色": "红"})
  打印 "无入口_ok=" + 转字符串(无入口["ok"])
  打印 "无入口_跳过=" + 转字符串(无入口["skipped"])
主程()
'''

# ---- 驱动 5：既有校验器语义不回归 ----
VALIDATOR_DRIVER = '''
从 工具 导入 校验参数

段落 主程():
  设 模式 为 {"type": "object", "properties": {"颜色": {"type": "string", "enum": ["红", "绿"]}},
    "required": ["颜色"]}
  设 错表 为 校验参数(模式, {"颜色": "蓝"})
  打印 "条数=" + 转字符串(长(错表))
  设 项 为 错表[0]
  打印 "键=" + 转字符串(字典键列表(项))
  打印 "路径=" + 转字符串(项["路径"])
  打印 "原因=" + 转字符串(项["原因"])
  打印 "细节=" + 转字符串(项["细节"])
  设 合法表 为 校验参数(模式, {"颜色": "红"})
  打印 "合法条数=" + 转字符串(长(合法表))
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


def test_信封结构与JSON契约(tmp_path):
    rc, out, kv = _run(ENVELOPE_DRIVER, tmp_path, 't0504_envelope.light')
    assert rc == 0, out
    assert kv.get('type') == 'validation', out
    assert kv.get('errorType') == 'schema', out
    assert kv.get('code') == 'PARAM_SCHEMA_INVALID', out
    assert kv.get('field') == '参数.秒', out
    assert kv.get('reason') == 'type', out
    assert kv.get('suggestion') == '类型应为 number（当前为 string）', out
    assert kv.get('retryable') in ('False', '假'), out
    assert kv.get('traceId') in ('None', '空'), out
    assert kv.get('是校验错误') in ('True', '真'), out
    assert kv.get('信封可否重试') in ('False', '假'), out
    assert kv.get('非校验错误判定') in ('False', '假'), out
    # JSON 键名固定（契约面，不能随内部命名漂移）
    for key in ('"type": "validation"', '"errorType": "schema"',
                '"code": "PARAM_SCHEMA_INVALID"', '"field": "参数.秒"',
                '"reason": "type"', '"suggestion":',
                '"retryable": false', '"traceId": null', '"details":'):
        assert key in kv.get('原始串', ''), (key, out)


def test_缺字段建议可操作(tmp_path):
    rc, out, kv = _run(SUGGEST_DRIVER, tmp_path, 't0504_missing.light')
    assert rc == 0, out
    assert kv.get('缺_ok') in ('False', '假'), out
    assert kv.get('缺_字段') == '参数.秒', out
    assert kv.get('缺_原因') == 'missing', out
    assert '缺少必填字段 秒' in kv.get('缺_建议', ''), out
    assert 'number' in kv.get('缺_建议', ''), out


def test_类型错建议给出期望与现值(tmp_path):
    rc, out, kv = _run(SUGGEST_DRIVER, tmp_path, 't0504_type.light')
    assert rc == 0, out
    assert kv.get('型_原因') == 'type', out
    assert '类型应为 number' in kv.get('型_建议', ''), out
    assert '当前为 string' in kv.get('型_建议', ''), out


def test_枚举建议随schema变化(tmp_path):
    rc, out, kv = _run(SUGGEST_DRIVER, tmp_path, 't0504_enum.light')
    assert rc == 0, out
    # 同一段生成逻辑，两套 schema 给出两套合法取值域 —— 证明建议来自真实规则
    assert '红|绿' in kv.get('枚甲_建议', ''), out
    assert '甲|乙' in kv.get('枚乙_建议', ''), out
    assert '当前为 蓝' in kv.get('枚甲_建议', ''), out
    assert '当前为 丙' in kv.get('枚乙_建议', ''), out


def test_嵌套路径与额外字段建议(tmp_path):
    rc, out, kv = _run(SUGGEST_DRIVER, tmp_path, 't0504_nested.light')
    assert rc == 0, out
    assert kv.get('嵌_字段') == '参数.配置.超时', out
    assert kv.get('嵌_原因') == 'type', out
    assert 'number' in kv.get('嵌_建议', ''), out
    assert kv.get('闭_字段') == '参数.b', out
    assert '删除未声明的字段 b' in kv.get('闭_建议', ''), out
    assert '可用字段：a' in kv.get('闭_建议', ''), out


def test_数组元素路径用下标渲染(tmp_path):
    rc, out, kv = _run(SUGGEST_DRIVER, tmp_path, 't0504_array.light')
    assert rc == 0, out
    # 数组下钻必须能按 "0" 走到 items，否则建议会退化成泛泛之谈
    assert kv.get('列_字段') == '参数.标签[0]', out
    assert kv.get('列_原因') == 'type', out
    assert '类型应为 number' in kv.get('列_建议', ''), out
    assert '当前为 string' in kv.get('列_建议', ''), out
    # 整条数组的约束（minItems）落在数组字段本身，不落到元素上
    assert kv.get('列少_字段') == '参数.标签', out
    assert kv.get('列少_原因') == 'minItems', out
    assert '至少需要 2 项' in kv.get('列少_建议', ''), out


def test_多错误全量返回与文案计数(tmp_path):
    rc, out, kv = _run(SUGGEST_DRIVER, tmp_path, 't0504_multi.light')
    assert rc == 0, out
    assert kv.get('多_条数') == '2', out
    assert '另有 1 处字段错误' in kv.get('多_文案', ''), out
    assert kv.get('合法_条数') == '0', out


def test_工具执行_非法参数被拦下(tmp_path):
    rc, out, kv = _run(EXEC_DRIVER, tmp_path, 't0504_exec_bad.light')
    assert rc == 0, out
    assert kv.get('坏_状态') == 'failed', out
    assert kv.get('坏_码') == 'PARAM_SCHEMA_INVALID', out
    assert kv.get('坏_大类') == 'validation', out
    assert kv.get('坏_细分') == 'schema', out
    assert kv.get('坏_可重试') in ('False', '假'), out
    assert kv.get('坏_字段') == '参数.颜色', out
    assert '红|绿' in kv.get('坏_建议', ''), out
    assert kv.get('坏_条数') == '2', out
    # 拦在派发前：处理函数一次都不该跑
    assert kv.get('坏_调用次数') == '0', out
    # 信封整体可直接喂给模型（键名固定）
    assert '"suggestion":' in kv.get('坏_信封串', ''), out
    assert '"field": "参数.颜色"' in kv.get('坏_信封串', ''), out


def test_工具执行_前置闸门同判(tmp_path):
    rc, out, kv = _run(EXEC_DRIVER, tmp_path, 't0504_gate.light')
    assert rc == 0, out
    assert kv.get('闸_过') in ('False', '假'), out
    assert kv.get('闸_码') == 'PARAM_SCHEMA_INVALID', out
    assert '红|绿' in kv.get('闸_建议', ''), out
    assert kv.get('闸_前') == kv.get('闸_后', 'x'), out
    assert kv.get('闸_后') == '1', out
    assert kv.get('查_过') in ('False', '假'), out


def test_工具执行_成功路径结构不变(tmp_path):
    rc, out, kv = _run(EXEC_DRIVER, tmp_path, 't0504_exec_ok.light')
    assert rc == 0, out
    assert kv.get('好_状态') == 'ok', out
    assert kv.get('好_键') == "['状态', '结果', '错误码', '消息']", out
    assert kv.get('好_结果') == '1', out
    assert kv.get('好_调用次数') == '1', out


def test_工具面装配_模型面校验入口(tmp_path):
    rc, out, kv = _run(ASSEMBLY_DRIVER, tmp_path, 't0504_assembly.light')
    assert rc == 0, out
    assert kv.get('表数') == '2', out       # 裸 工具无模式，不进表
    assert kv.get('坏_ok') in ('False', '假'), out
    assert kv.get('坏_字段') == '参数.颜色', out
    assert '红|绿' in kv.get('坏_建议', ''), out
    assert kv.get('坏_可重试') in ('False', '假'), out
    assert '建议：' in kv.get('坏_文案', ''), out
    assert kv.get('跳_ok') in ('True', '真'), out
    assert kv.get('跳_跳过') in ('True', '真'), out
    assert kv.get('知_ok') in ('True', '真'), out
    assert kv.get('合法_ok') in ('True', '真'), out
    assert kv.get('合法_跳过') in ('False', '假'), out
    # 未注入入口不假报通过，明确标跳过
    assert kv.get('无入口_ok') in ('True', '真'), out
    assert kv.get('无入口_跳过') in ('True', '真'), out


def test_既有校验器语义不回归(tmp_path):
    rc, out, kv = _run(VALIDATOR_DRIVER, tmp_path, 't0504_validator.light')
    assert rc == 0, out
    assert kv.get('条数') == '1', out
    assert kv.get('键') == "['路径', '原因', '细节']", out
    assert kv.get('路径') == "['参数', '颜色']", out
    assert kv.get('原因') == 'enum', out
    assert kv.get('合法条数') == '0', out

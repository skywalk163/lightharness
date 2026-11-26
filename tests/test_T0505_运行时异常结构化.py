# -*- coding: utf-8 -*-
"""T-0505：W3/T3.2 运行时异常结构化（工具执行路径）+ 可重试提示。

判据四层（全部走 .light 侧真实代码，子进程 `python 运行.py <driver>`）：

  1. 契约层：运行时异常装进与 T-0504 校验错误**同一只信封**（十键：
     type/errorType/code/field/reason/message/suggestion/retryable/traceId/details），
     type="runtime" 与校验类的 "validation" 在契约上可区分；
  2. 分类层：errorType ∈ timeout/notFound/permission/cancelled/internal，
     未知/空值一律归 internal；稳定错误码 TOOL_* 与 errorType 一一对应；
  3. 重试层：retryable 是**保守白名单**——只有 timeout 为真，其余（含未知、内部错）
     一律为假；显式传「真」也不能越过白名单（防调用方乐观标注把模型带进空转）；
  4. 接线层：执行管线（同步 §6 / 异步并发 §6b）失败结果挂信封 + traceId + suggestion；
     参数校验失败与运行时异常在同一只契约里可区分；**成功路径返回逐键不变**；
     工具面装配能把失败结果投影成模型面载荷（与 错误增强 同形）。

兼容边界（有意保留）：`造运行时异常` 仍是 T-0515 钉住的 4 键轻量视图
（errorType/message/retryable/traceId），由同一只信封投影而来，不是第二套 schema；
执行结果的 错误码 仍沿用既有 wire 口径（= 状态字面值），稳定码在信封的 code 里。
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

# ---- 驱动 1：错误增强 §14 运行时信封契约 ----
ENVELOPE_DRIVER = r'''
从 错误增强 导入 造运行时错误, 造校验错误, 是运行时错误, 是校验错误, 错误大类归属
从 错误增强 导入 运行时可重试, 运行时失败载荷, 运行时失败文案, 归一运行时型
从 JSON 导入 序列化JSON, 解析JSON

段落 键串(表):
  返回 序列化JSON(字典键列表(表))

段落 主程():
  设 超 为 造运行时错误("timeout", "执行超时 30000ms")
  设 未 为 造运行时错误("notFound", "no such file or directory")
  设 权 为 造运行时错误("permission", "permission denied: /root")
  设 消 为 造运行时错误("cancelled", "cancelled by user")
  设 内 为 造运行时错误("internal", "division by zero")
  设 怪 为 造运行时错误("whatever", "boom")
  设 空型 为 造运行时错误(空, "no type given")

  设 校 为 造校验错误("参数.秒", "type", "参数.秒：期望 number",
    "类型应为 number", 空)
  打印("族_键=" + 键串(超))
  打印("族_同键=" + 转字符串(字典键列表(超) == 字典键列表(校)))
  打印("族_大类=" + 转字符串(超["type"]) + "|" + 转字符串(校["type"]))

  设 名表 为 ["timeout", "notFound", "permission", "cancelled", "internal"]
  设 信封表 为 [超, 未, 权, 消, 内]
  设 序 为 0
  遍历 封 之 信封表:
    设 标 为 名表[序]
    打印(标 + "_型=" + 转字符串(封["errorType"]))
    打印(标 + "_码=" + 转字符串(封["code"]))
    打印(标 + "_可重试=" + 转字符串(封["retryable"]))
    打印(标 + "_建议=" + 转字符串(封["suggestion"]))
    设 序 为 序 + 1
  打印("怪_型=" + 转字符串(怪["errorType"]) + "|" + 转字符串(怪["code"]))
  打印("怪_可重试=" + 转字符串(怪["retryable"]))
  打印("空型_型=" + 转字符串(空型["errorType"]))
  打印("归一_未知=" + 归一运行时型("nonsense"))
  打印("可重试_未知=" + 转字符串(运行时可重试("nonsense")))

  设 未硬 为 造运行时错误("notFound", "x", 空, 真)
  设 超否 为 造运行时错误("timeout", "x", 空, 假)
  设 超真 为 造运行时错误("timeout", "x", 空, 真)
  打印("钳_未硬=" + 转字符串(未硬["retryable"]))
  打印("钳_超否=" + 转字符串(超否["retryable"]))
  打印("钳_超真=" + 转字符串(超真["retryable"]))

  设 裸表 为 {"x": 1}
  打印("是运_运=" + 转字符串(是运行时错误(超)))
  打印("是运_校=" + 转字符串(是运行时错误(校)))
  打印("是校_运=" + 转字符串(是校验错误(超)))
  打印("归属_运=" + 错误大类归属(超))
  打印("归属_校=" + 错误大类归属(校))
  打印("归属_裸=" + 错误大类归属(裸表))

  设 回 为 解析JSON(序列化JSON(超))
  打印("往返=" + 转字符串(回 == 超))
  打印("原始串=" + 序列化JSON(超))

  设 载 为 运行时失败载荷(超)
  打印("载_键=" + 键串(载))
  打印("载_ok=" + 转字符串(载["ok"]))
  打印("载_可重试=" + 转字符串(载["retryable"]))
  打印("载_条数=" + 转字符串(长(载["runtimeErrors"])))
  打印("载_error同=" + 转字符串(载["error"] == 超))
  打印("载_文案=" + 运行时失败文案(载))
  设 未载 为 运行时失败载荷(未)
  打印("载_文案否=" + 运行时失败文案(未载))
主程()
'''

# ---- 驱动 2：执行管线（同步）运行时异常 + 校验失败可区分 ----
PIPELINE_DRIVER = r'''
从 工具执行 导入 建执行器, 具注册工具, 执行工具, 级公开
从 工具执行 导入 造运行时异常, 造运行时异常信封, 具登记参数模式
从 工具 导入 校验参数
从 错误增强 导入 校验失败载荷, 造校验错误
从 JSON 导入 序列化JSON

设 计数 为 {"次": 0}

段落 成功处理(参数, 令牌):
  返回 "done"

段落 超时处理(参数, 令牌):
  抛出 新建 错误("timeout while reading")

段落 找不到处理(参数, 令牌):
  抛出 新建 错误("notFound: no such file")

段落 权限处理(参数, 令牌):
  抛出 新建 错误("permission denied: /root")

段落 内部处理(参数, 令牌):
  抛出 新建 错误("division by zero")

段落 受控处理(参数, 令牌):
  设 次 为 字典获取(计数, "次", 0) + 1
  字典设置(计数, "次", 次)
  返回 "handled"

段落 校验入口(模式, 参数):
  设 原始 为 校验参数(模式, 参数)
  如果 长(原始) == 0:
    返回 {"通过": 真}
  返回 {"通过": 假, "载荷": 校验失败载荷(原始, 模式, 参数)}

段落 报(标, 果):
  打印(标 + "_态=" + 转字符串(果["状态"]))
  打印(标 + "_码=" + 转字符串(果["错误码"]))
  如果 字典包含键(果, "运行时异常") == 假:
    打印(标 + "_有信封=" + 转字符串(假))
    返回 空
  设 封 为 果["运行时异常"]
  打印(标 + "_有信封=" + 转字符串(真))
  打印(标 + "_键=" + 序列化JSON(字典键列表(封)))
  打印(标 + "_型=" + 转字符串(封["errorType"]))
  打印(标 + "_码段=" + 转字符串(封["code"]))
  打印(标 + "_可重试=" + 转字符串(封["retryable"]))
  打印(标 + "_建议=" + 转字符串(封["suggestion"]))
  打印(标 + "_trace同=" + 转字符串(封["traceId"] == 果["traceId"]))
  打印(标 + "_短键型=" + 转字符串(果["errorType"]))
  打印(标 + "_短键重试=" + 转字符串(果["retryable"]))
  打印(标 + "_trace=" + 转字符串(果["traceId"]))
  打印(标 + "_果建议=" + 转字符串(果["suggestion"]))
  返回 封

段落 主程():
  设 ex 为 建执行器(1000, 100000, 0, "滑动窗口", 空, 校验入口)
  具注册工具(ex["注册"], "成功", 级公开, 成功处理)
  具注册工具(ex["注册"], "慢", 级公开, 超时处理)
  具注册工具(ex["注册"], "缺", 级公开, 找不到处理)
  具注册工具(ex["注册"], "禁", 级公开, 权限处理)
  具注册工具(ex["注册"], "炸", 级公开, 内部处理)
  设 颜色模式 为 {"type": "object", "properties": {
    "颜色": {"type": "string", "enum": ["红", "绿"]}}, "required": ["颜色"]}
  具注册工具(ex["注册"], "受控", 级公开, 受控处理, 空, 颜色模式)

  设 成 为 执行工具(ex, "成功", "public", "u", {})
  打印("成_键=" + 序列化JSON(字典键列表(成)))
  打印("成_态=" + 转字符串(成["状态"]))

  设 慢 为 执行工具(ex, "慢", "public", "u", {})
  设 慢封 为 报("慢", 慢)
  设 缺 为 执行工具(ex, "缺", "public", "u", {})
  报("缺", 缺)
  设 禁 为 执行工具(ex, "禁", "public", "u", {})
  报("禁", 禁)
  设 炸 为 执行工具(ex, "炸", "public", "u", {})
  报("炸", 炸)

  设 校 为 执行工具(ex, "受控", "public", "u", {"颜色": "蓝"})
  打印("校_态=" + 转字符串(校["状态"]))
  打印("校_码=" + 转字符串(校["错误码"]))
  打印("校_有信封=" + 转字符串(字典包含键(校, "运行时异常")))
  设 校封 为 校["错误"]
  打印("校_大类=" + 转字符串(校封["type"]))
  打印("校_型=" + 转字符串(校封["errorType"]))
  打印("校_可重试=" + 转字符串(校封["retryable"]))
  打印("校_条数=" + 转字符串(长(校["校验错误"])))
  打印("校_处理次数=" + 转字符串(字典获取(计数, "次", 0)))
  打印("校_同键=" + 转字符串(字典键列表(校封) == 字典键列表(慢封)))

  设 合 为 执行工具(ex, "受控", "public", "u", {"颜色": "红"})
  打印("合_态=" + 转字符串(合["状态"]))
  打印("合_处理次数=" + 转字符串(字典获取(计数, "次", 0)))

  设 轻 为 造运行时异常("notFound: no such file", "tr_手工")
  打印("轻_键=" + 序列化JSON(字典键列表(轻)))
  设 轻超 为 造运行时异常("timeout x", "tr_a", 空, 真)
  打印("轻超_可重试=" + 转字符串(轻超["retryable"]))
  设 轻钳 为 造运行时异常("notFound x", "tr_b", 空, 真)
  打印("轻钳_可重试=" + 转字符串(轻钳["retryable"]))
  设 信封 为 造运行时异常信封("timeout x", "tr_c")
  打印("信封_键=" + 序列化JSON(字典键列表(信封)))
  打印("信封_型=" + 转字符串(信封["type"]) + "|" + 转字符串(信封["code"]))
主程()
'''

# ---- 驱动 3：异步 / 并发路径同样结构化 ----
ASYNC_DRIVER = r'''
从 工具执行 导入 建执行器, 具注册工具, 具异步执行, 具并发执行, 级公开

段落 超时处理(参数, 令牌):
  抛出 新建 错误("timeout on async")

段落 成功处理(参数, 令牌):
  返回 "ok"

异步 段落 主程():
  设 ex 为 建执行器(1000, 100000, 0, "滑动窗口")
  具注册工具(ex["注册"], "炸", 级公开, 超时处理)
  具注册工具(ex["注册"], "好", 级公开, 成功处理)

  设 单 为 等待 具异步执行(ex, "炸", "public", "u")
  打印("异步_态=" + 转字符串(单["状态"]))
  设 封 为 单["运行时异常"]
  打印("异步_键=" + 序列化JSON(字典键列表(封)))
  打印("异步_型=" + 转字符串(封["errorType"]))
  打印("异步_码=" + 转字符串(封["code"]))
  打印("异步_可重试=" + 转字符串(封["retryable"]))
  打印("异步_trace同=" + 转字符串(封["traceId"] == 单["traceId"]))

  设 请求甲 为 {"工具名": "炸"}
  设 请求乙 为 {"工具名": "好"}
  设 请求表 为 [请求甲, 请求乙]
  设 并 为 等待 具并发执行(ex, 请求表, "public", "u")
  打印("并发_0态=" + 转字符串(并[0]["状态"]))
  打印("并发_0型=" + 转字符串(并[0]["运行时异常"]["errorType"]))
  打印("并发_0重试=" + 转字符串(并[0]["运行时异常"]["retryable"]))
  打印("并发_1态=" + 转字符串(并[1]["状态"]))
  打印("并发_1有信封=" + 转字符串(字典包含键(并[1], "运行时异常")))
异步 运行 主程()
'''

# ---- 驱动 4：工具面装配模型面运行时失败投影 ----
SURFACE_DRIVER = r'''
从 工具面装配 导入 运行时失败载荷, 运行时可否重试, 是运行时失败, 运行时平铺键表
从 工具执行 导入 建执行器, 具注册工具, 执行工具, 级公开
从 错误增强 导入 造运行时错误
从 JSON 导入 序列化JSON

段落 超时处理(参数, 令牌):
  抛出 新建 错误("timeout while reading")

段落 成功处理(参数, 令牌):
  返回 "done"

段落 主程():
  设 手工封 为 造运行时错误("notFound", "no such file")
  设 手工果 为 {"状态": "failed", "运行时异常": 手工封}
  设 载 为 运行时失败载荷(手工果)
  打印("装_键=" + 序列化JSON(字典键列表(载)))
  打印("装_平铺=" + 序列化JSON(运行时平铺键表))
  打印("装_ok=" + 转字符串(载["ok"]))
  打印("装_错误同=" + 转字符串(载["error"] == 手工封))
  打印("装_条数=" + 转字符串(长(载["runtimeErrors"])))
  打印("装_型=" + 转字符串(载["errorType"]))
  打印("装_可重试=" + 转字符串(载["retryable"]))

  设 成功果 为 {"状态": "ok", "结果": 1}
  设 成功载 为 运行时失败载荷(成功果)
  打印("装_成功跳过=" + 转字符串(成功载["skipped"]))
  打印("装_成功判定=" + 转字符串(是运行时失败(成功果)))
  打印("装_成功可重试=" + 转字符串(运行时可否重试(成功果)))

  设 校果 为 {"状态": "failed", "错误码": "PARAM_SCHEMA_INVALID", "错误": {"type": "validation"}}
  打印("装_校验判定=" + 转字符串(是运行时失败(校果)))
  打印("装_校验可重试=" + 转字符串(运行时可否重试(校果)))

  设 ex 为 建执行器(1000, 100000, 0, "滑动窗口")
  具注册工具(ex["注册"], "慢", 级公开, 超时处理)
  具注册工具(ex["注册"], "好", 级公开, 成功处理)
  设 真果 为 执行工具(ex, "慢", "public", "u", {})
  设 真载 为 运行时失败载荷(真果)
  打印("装_真型=" + 转字符串(真载["errorType"]))
  打印("装_真可重试=" + 转字符串(运行时可否重试(真果)))
  打印("装_真trace同=" + 转字符串(真载["traceId"] == 真果["traceId"]))
  设 好果 为 执行工具(ex, "好", "public", "u", {})
  打印("装_好判定=" + 转字符串(是运行时失败(好果)))
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


@pytest.fixture(scope='module')
def 信封端(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0505信封')
    rc, out, kv = _run(ENVELOPE_DRIVER, tmp, 't0505_envelope.light')
    assert rc == 0, out
    return kv, out


@pytest.fixture(scope='module')
def 管线端(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0505管线')
    rc, out, kv = _run(PIPELINE_DRIVER, tmp, 't0505_pipeline.light')
    assert rc == 0, out
    return kv, out


@pytest.fixture(scope='module')
def 异步端(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0505异步')
    rc, out, kv = _run(ASYNC_DRIVER, tmp, 't0505_async.light')
    assert rc == 0, out
    return kv, out


@pytest.fixture(scope='module')
def 装配端(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0505装配')
    rc, out, kv = _run(SURFACE_DRIVER, tmp, 't0505_surface.light')
    assert rc == 0, out
    return kv, out


def _真(v):
    return v in ('True', '真')


def _假(v):
    return v in ('False', '假')


族键 = ['type', 'errorType', 'code', 'field', 'reason', 'message',
       'suggestion', 'retryable', 'traceId', 'details']


# ---------------------------------------------------------------------------
# 1. 契约层：与 T-0504 校验信封同族（同键集，type 区分大类）
# ---------------------------------------------------------------------------
def test_运行时信封键集与校验信封同族(信封端):
    kv, out = 信封端
    assert json.loads(kv['族_键']) == 族键, out
    assert _真(kv['族_同键']), ('运行时信封与校验信封必须同键集，不得两套口径', out)
    assert kv['族_大类'] == 'runtime|validation', out


def test_运行时信封JSON字段固定(信封端):
    kv, out = 信封端
    串 = kv['原始串']
    for piece in ('"type": "runtime"', '"errorType": "timeout"',
                  '"code": "TOOL_TIMEOUT"', '"retryable": true',
                  '"suggestion":', '"traceId": null', '"details": null'):
        assert piece in 串, (piece, 串)
    assert _真(kv['往返']), ('信封应可 JSON 往返', out)


# ---------------------------------------------------------------------------
# 2. 分类层：errorType → 稳定错误码（未知/空值保守归 internal）
# ---------------------------------------------------------------------------
def test_典型运行时异常返回结构化类型与稳定码(信封端):
    kv, out = 信封端
    期望 = {
        'timeout': 'TOOL_TIMEOUT',
        'notFound': 'TOOL_NOT_FOUND',
        'permission': 'TOOL_PERMISSION_DENIED',
        'cancelled': 'TOOL_CANCELLED',
        'internal': 'TOOL_INTERNAL_ERROR',
    }
    for 型, 码 in 期望.items():
        assert kv.get(型 + '_型') == 型, (型, out)
        assert kv.get(型 + '_码') == 码, (型, out)
        assert kv.get(型 + '_建议', '') != '', ('建议不得为空', 型, out)


def test_未知与空类型保守归internal(信封端):
    kv, out = 信封端
    assert kv['怪_型'] == 'internal|TOOL_INTERNAL_ERROR', out
    assert kv['空型_型'] == 'internal', out
    assert kv['归一_未知'] == 'internal', out


# ---------------------------------------------------------------------------
# 3. 重试层：保守白名单（只有 timeout 可原地重试）
# ---------------------------------------------------------------------------
def test_retryable保守白名单只放行超时(信封端):
    kv, out = 信封端
    assert _真(kv['timeout_可重试']), out
    for 型 in ('notFound', 'permission', 'cancelled', 'internal'):
        assert _假(kv[型 + '_可重试']), ('非 timeout 一律不可重试', 型, out)
    assert _假(kv['怪_可重试']), ('未知类型不得判可重试', out)
    assert _假(kv['可重试_未知']), out


def test_显式标注不得越过白名单(信封端):
    kv, out = 信封端
    # notFound 即便调用方硬标「可重试」，也必须保持不可重试（单一出口）
    assert _假(kv['钳_未硬']), ('显式真不得打开白名单外的可重试', out)
    # timeout 显式标「不可重试」应被尊重（更保守）
    assert _假(kv['钳_超否']), out
    assert _真(kv['钳_超真']), out


# ---------------------------------------------------------------------------
# 4. 建议层：按类型分化且可操作（不是一句通用废话）
# ---------------------------------------------------------------------------
def test_建议按错误类型分化(信封端):
    kv, out = 信封端
    建议表 = {型: kv[型 + '_建议'] for 型 in
             ('timeout', 'notFound', 'permission', 'cancelled', 'internal')}
    assert len(set(建议表.values())) == 5, ('五类建议应各不相同', 建议表)
    assert '重试' in 建议表['timeout'], 建议表
    assert '改动' in 建议表['notFound'] or '核对' in 建议表['notFound'], 建议表
    assert '无权限' in 建议表['permission'], 建议表
    assert '取消' in 建议表['cancelled'], 建议表
    assert '换方案' in 建议表['internal'], 建议表


# ---------------------------------------------------------------------------
# 5. 大类判定与失败载荷（与校验失败载荷同形）
# ---------------------------------------------------------------------------
def test_大类归属可区分校验与运行时(信封端):
    kv, out = 信封端
    assert _真(kv['是运_运']) and _假(kv['是运_校']), out
    assert _假(kv['是校_运']), out
    assert kv['归属_运'] == 'runtime' and kv['归属_校'] == 'validation', out
    assert kv['归属_裸'] == '', ('非信封不瞎猜大类', out)


def test_运行时失败载荷与校验载荷同形(信封端):
    kv, out = 信封端
    键 = json.loads(kv['载_键'])
    期望 = ['ok'] + 族键[:-1] + ['error', 'runtimeErrors']
    assert 键 == 期望, ('载荷形状应与 校验失败载荷 同构', 键, 期望, out)
    assert _假(kv['载_ok']), out
    assert _真(kv['载_可重试']), out
    assert kv['载_条数'] == '1', out
    assert _真(kv['载_error同']), ('载荷 error 应是同一只信封', out)


def test_运行时失败文案带建议与重试提示(信封端):
    kv, out = 信封端
    assert '建议：' in kv['载_文案'], out
    assert '可原地重试' in kv['载_文案'], out
    assert '不建议原地重试' in kv['载_文案否'], out


# ---------------------------------------------------------------------------
# 6. 执行管线（同步）：典型运行时异常结构化 + traceId 关联
# ---------------------------------------------------------------------------
def test_执行管线超时返回结构化信封且可重试(管线端):
    kv, out = 管线端
    assert kv['慢_态'] == 'failed', out
    assert json.loads(kv['慢_键']) == 族键, out
    assert kv['慢_型'] == 'timeout', out
    assert kv['慢_码段'] == 'TOOL_TIMEOUT', out
    assert _真(kv['慢_可重试']), out
    assert _真(kv['慢_trace同']), ('信封 traceId 必须与结果 traceId 一致', out)
    assert kv['慢_短键型'] == 'timeout', out


def test_执行管线未找到与权限不可重试(管线端):
    kv, out = 管线端
    for 标, 型, 码 in (('缺', 'notFound', 'TOOL_NOT_FOUND'),
                      ('禁', 'permission', 'TOOL_PERMISSION_DENIED')):
        assert kv[标 + '_型'] == 型, (标, out)
        assert kv[标 + '_码段'] == 码, (标, out)
        assert _假(kv[标 + '_可重试']), (标, out)
        assert _假(kv[标 + '_短键重试']), (标, out)


def test_执行管线内部错误归internal不可重试(管线端):
    kv, out = 管线端
    assert kv['炸_型'] == 'internal', out
    assert kv['炸_码段'] == 'TOOL_INTERNAL_ERROR', out
    assert _假(kv['炸_可重试']), out


def test_失败结果建议带traceId可反查(管线端):
    kv, out = 管线端
    for 标 in ('慢', '缺', '禁', '炸'):
        assert kv[标 + '_trace'] in kv[标 + '_果建议'], (
            标, '失败 suggestion 必须带 traceId 可反查', out)
        assert kv[标 + '_建议'] != '', (标, '信封自带的建议不得为空', out)


# ---------------------------------------------------------------------------
# 7. 参数错与运行时错在契约上可区分
# ---------------------------------------------------------------------------
def test_参数校验失败与运行时异常契约可区分(管线端):
    kv, out = 管线端
    assert kv['校_态'] == 'failed', out
    assert kv['校_码'] == 'PARAM_SCHEMA_INVALID', out
    assert _假(kv['校_有信封']), ('校验失败不应挂运行时信封', out)
    assert kv['校_大类'] == 'validation', out
    assert kv['校_型'] == 'schema', out
    assert _假(kv['校_可重试']), out
    assert kv['校_处理次数'] == '0', ('校验门禁不得执行处理函数', out)
    # 两者同一只信封（同键集），只靠 type/errorType 区分
    assert _真(kv['校_同键']), ('校验与运行时信封必须同键集', out)


def test_校验通过后处理函数才执行(管线端):
    kv, out = 管线端
    assert kv['合_态'] == 'ok', out
    assert kv['合_处理次数'] == '1', out


# ---------------------------------------------------------------------------
# 8. 红线：成功路径返回逐键不变
# ---------------------------------------------------------------------------
def test_成功路径返回结构未变(管线端):
    kv, out = 管线端
    assert json.loads(kv['成_键']) == ['状态', '结果', '错误码', '消息'], (
        '成功路径不得因本卡新增任何字段', kv['成_键'], out)
    assert kv['成_态'] == 'ok', out


# ---------------------------------------------------------------------------
# 9. 兼容：造运行时异常 仍是 T-0515 钉住的 4 键轻量视图
# ---------------------------------------------------------------------------
def test_轻量视图保持四键兼容(管线端):
    kv, out = 管线端
    assert json.loads(kv['轻_键']) == ['errorType', 'message', 'retryable', 'traceId'], out
    assert _真(kv['轻超_可重试']), out
    assert _假(kv['轻钳_可重试']), ('轻量视图同样受白名单约束', out)
    assert json.loads(kv['信封_键']) == 族键, out
    assert kv['信封_型'] == 'runtime|TOOL_TIMEOUT', out


# ---------------------------------------------------------------------------
# 10. 异步 / 并发路径同样结构化（不只同步路径）
# ---------------------------------------------------------------------------
def test_异步执行失败同样返回信封(异步端):
    kv, out = 异步端
    assert kv['异步_态'] == 'failed', out
    assert json.loads(kv['异步_键']) == 族键, out
    assert kv['异步_型'] == 'timeout', out
    assert kv['异步_码'] == 'TOOL_TIMEOUT', out
    assert _真(kv['异步_可重试']), out
    assert _真(kv['异步_trace同']), out


def test_并发执行失败per请求独立结构化(异步端):
    kv, out = 异步端
    assert kv['并发_0态'] == 'failed', out
    assert kv['并发_0型'] == 'timeout', out
    assert _真(kv['并发_0重试']), out
    assert kv['并发_1态'] == 'ok', out
    assert _假(kv['并发_1有信封']), ('成功项不得挂运行时信封', out)


# ---------------------------------------------------------------------------
# 11. 工具面装配：模型面投影与 错误增强 同形（无第三套口径）
# ---------------------------------------------------------------------------
def test_模型面运行时失败载荷与信封同形(装配端, 信封端):
    kv, out = 装配端
    键 = json.loads(kv['装_键'])
    期望 = ['ok'] + 族键[:-1] + ['error', 'runtimeErrors']
    assert 键 == 期望, (键, 期望, out)
    assert json.loads(kv['装_平铺']) == 族键[:-1], out
    assert _假(kv['装_ok']), out
    assert _真(kv['装_错误同']), ('投影应原样携带同一只信封', out)
    assert kv['装_条数'] == '1', out
    assert kv['装_型'] == 'notFound', out


def test_模型面投影与错误增强载荷键集一致(装配端, 信封端):
    装配kv, _ = 装配端
    信封kv, 信封out = 信封端
    # 同一只载荷形状，两处投影不得漂移成两套口径
    assert json.loads(装配kv['装_键']) == json.loads(信封kv['载_键']), 信封out


def test_模型面判定区分成功与校验失败(装配端):
    kv, out = 装配端
    assert _真(kv['装_成功跳过']), out
    assert _假(kv['装_成功判定']), out
    assert _假(kv['装_成功可重试']), out
    assert _假(kv['装_校验判定']), ('校验失败不是运行时失败', out)
    assert _假(kv['装_校验可重试']), out
    assert _假(kv['装_好判定']), out


def test_模型面可从真实执行结果投影且可重试一致(装配端):
    kv, out = 装配端
    assert kv['装_真型'] == 'timeout', out
    assert _真(kv['装_真可重试']), out
    assert _真(kv['装_真trace同']), out
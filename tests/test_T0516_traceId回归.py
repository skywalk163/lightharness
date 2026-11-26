# -*- coding: utf-8 -*-
"""T-0516：traceId 穿插传递与「失败 → 重试 / 失败 → 改方案」关联回归（验收卡）。

本卡不实现新能力，只回归 T-0515 已落地的行为。判据全部走 .light 侧真实
执行管线（子进程 `python 运行.py <driver>`），覆盖四条验收线：

  A. 失败 → 重试：模型依据结构化错误（errorType/retryable/suggestion）判断
     可原样重试，重试请求携带父 traceId；多次重试同根、链逐次增长。
  B. 失败 → 改方案：不可重试的错误（notFound）不再原样重试，换工具/换参数
     重新发起，仍携带父 traceId；父链/根链/链尾都能关联到最初失败。
     模型把 traceId 塞回调用参数（而非显式父链形参）同样成立。
  C. 按 traceId 反查结构化详情：一次失败执行可用 traceId 取回工具名/状态/
     错误信息/建议/链路；未知 id 返回空，不瞎编。
  D. 成功路径不冗余暴露：纯成功结果没有 traceId/suggestion；只有带父链
     （需要关联）时才出现 traceId；错误文案不被 traceId 改写。
     预算包装器（T-0512）不得吞掉 trace 元数据；审计记录带同一 traceId。

反证（见 .hive/summary.md）：把 附trace元数据 的 需暴露 判定恒为假，
test_失败到重试链路同根且链逐次增长 与 test_失败到改方案链路可关联
立红；把 记trace 的父链继承去掉，链增长与改方案链尾用例立红。
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

DRIVER = r'''
从 工具执行 导入 建执行器, 具注册工具, 执行工具, 关联子操作, 追踪详情, 按根追踪
从 工具执行 导入 最后traceId, 具执行工具带预算, 审计查询, 级公开
从 上下文 导入 建用量状态
从 工具面装配 导入 建预算信号配置
从 JSON 导入 序列化JSON

段落 成功处理(参数, 令牌):
  返回 "ok:" + 转字符串(参数["名"])

段落 超时处理(参数, 令牌):
  抛出 新建 错误("timeout: 读取 /srv/data 超时")

段落 未找到处理(参数, 令牌):
  抛出 新建 错误("notFound: /tmp/缺失.txt 不存在")

段落 计数带trace(记录表, 目标id):
  设 数 为 0
  遍历 记录 之 记录表:
    如果 字典包含键(记录, "traceId") == 真:
      如果 记录["traceId"] == 目标id:
        设 数 为 数 + 1
  返回 数

异步 段落 主程():
  # 放宽限流：本驱动单进程连跑十余次执行，避免默认 10/1000ms 误伤判据
  设 ex 为 建执行器(1000, 100000, 0, "滑动窗口")
  具注册工具(ex["注册"], "读文件", 级公开, 成功处理)
  具注册工具(ex["注册"], "read_file", 级公开, 成功处理)
  具注册工具(ex["注册"], "写文件", 级公开, 成功处理)
  具注册工具(ex["注册"], "读超时", 级公开, 超时处理)
  具注册工具(ex["注册"], "读未找到", 级公开, 未找到处理)

  # A. 失败 → 重试：结构化错误给出「可原样重试」，重试携带父 traceId
  设 首败 为 执行工具(ex, "读超时", "public", "u", {"名": "甲"})
  设 二试 为 执行工具(ex, "读超时", "public", "u", {"名": "甲"}, "", 首败["traceId"])
  设 三试 为 执行工具(ex, "读超时", "public", "u", {"名": "甲"}, "", 二试["traceId"])
  打印("首败=" + 序列化JSON(首败))
  打印("二试=" + 序列化JSON(二试))
  打印("三试=" + 序列化JSON(三试))
  打印("首族=" + 序列化JSON(按根追踪(ex, 首败["traceId"])))

  # B. 失败 → 改方案：不可重试错误，换工具继续，仍带父 traceId
  设 未找到 为 执行工具(ex, "读未找到", "public", "u", {"名": "乙"})
  设 改案 为 执行工具(ex, "读文件", "public", "u", {"名": "甲"}, "", 未找到["traceId"])
  # 模型也可把 traceId 直接塞回参数（显式父链形参为空）
  设 参数改案 为 执行工具(ex, "读文件", "public", "u",
    {"名": "丙", "traceId": 未找到["traceId"]})
  打印("未找到=" + 序列化JSON(未找到))
  打印("改案=" + 序列化JSON(改案))
  打印("参数改案=" + 序列化JSON(参数改案))

  # C. 按 traceId 反查结构化详情
  打印("首败详情=" + 序列化JSON(追踪详情(ex, 首败["traceId"])))
  打印("三试详情=" + 序列化JSON(追踪详情(ex, 三试["traceId"])))
  打印("改案详情=" + 序列化JSON(追踪详情(ex, 改案["traceId"])))
  打印("未知详情=" + 序列化JSON(追踪详情(ex, "tr_不存在")))
  打印("未找到族=" + 序列化JSON(按根追踪(ex, 未找到["traceId"])))

  # D. 独立失败不串进别人的链
  设 独败 为 执行工具(ex, "读未找到", "public", "u", {"名": "丁"})
  打印("独败=" + 序列化JSON(独败))
  打印("独族=" + 序列化JSON(按根追踪(ex, 独败["traceId"])))

  # E. 成功路径不冗余；只有需要关联（带父链）时才出现 traceId
  设 纯成功 为 执行工具(ex, "读文件", "public", "u", {"名": "戊"})
  设 纯成功id 为 最后traceId(ex)
  设 同族子 为 关联子操作(ex, 纯成功id, "read_file", "public", "u", {"名": "己"})
  打印("纯成功=" + 序列化JSON(纯成功))
  打印("纯成功id=" + 纯成功id)
  打印("同族子=" + 序列化JSON(同族子))

  # F. 预算包装器（T-0512）不吞 trace 元数据；审计记录带同一 traceId
  设 预算配置 为 建预算信号配置("每轮", 空, 1000, 0, 假)
  设 用量 为 建用量状态(1000)
  设 包装改案 为 具执行工具带预算(ex, "读未找到", "public", 用量, "u",
    {"名": "庚"}, "", 未找到["traceId"], 预算配置)
  设 事件表 为 审计查询(ex["审计"])
  打印("包装改案=" + 序列化JSON(包装改案))
  打印("审计首败数=" + 转字符串(计数带trace(事件表, 首败["traceId"])))
  打印("审计改案数=" + 转字符串(计数带trace(事件表,
    字典获取(改案, "traceId", ""))))

异步 运行 主程()
'''


def _run(tmp_path):
    driver = tmp_path / 't0516_driver.light'
    driver.write_text(DRIVER, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    proc = subprocess.run(
        [sys.executable, RUNNER, str(driver)], cwd=ROOT,
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, env=env,
    )
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc, kv


@pytest.fixture(scope='module')
def 输出(tmp_path_factory):
    proc, kv = _run(tmp_path_factory.mktemp('t0516'))
    assert proc.returncode == 0, (
        'traceId 回归驱动应 rc=0，实际 %s\n--- stdout ---\n%s\n--- stderr ---\n%s'
        % (proc.returncode, proc.stdout[-3000:], proc.stderr[-3000:])
    )
    return kv


def _取(kv, 键):
    assert 键 in kv, '驱动没有打印 %s；实际键：%s' % (键, sorted(kv))
    return json.loads(kv[键])


def test_失败响应给出可重试的结构化判断且文案不被改写(输出):
    首败 = _取(输出, '首败')
    assert 首败['状态'] == 'failed' and 首败['错误码'] == 'failed', 首败
    assert 首败['消息'] == 'timeout: 读取 /srv/data 超时', ('错误文案原样', 首败)
    assert 'traceId=' not in 首败['消息'], ('traceId 不得混进错误文案', 首败)
    异常体 = 首败['运行时异常']
    assert 异常体['errorType'] == 'timeout' and 异常体['retryable'] is True, 异常体
    assert 异常体['code'] == 'TOOL_TIMEOUT', 异常体
    assert '可原样重试' in 异常体['suggestion'], 异常体
    # 模型据此判断「可重试」，且 suggestion 给出可反查的 traceId
    assert 首败['traceId'] in 首败['suggestion'], 首败
    assert 首败['traceId'] in 首败['建议'], 首败
    assert 首败['运行时异常']['traceId'] == 首败['traceId'], 首败


def test_失败到重试链路同根且链逐次增长(输出):
    首败 = _取(输出, '首败')
    二试 = _取(输出, '二试')
    三试 = _取(输出, '三试')
    首 = 首败['traceId']
    次 = 二试['traceId']
    末 = 三试['traceId']
    assert len({首, 次, 末}) == 3, ('每次重试是独立执行，各生成 traceId', 首, 次, 末)
    assert 二试['父traceId'] == 首 and 三试['父traceId'] == 次, (二试, 三试)
    assert 二试['根traceId'] == 首 and 三试['根traceId'] == 首, ('同一失败族同根', 二试, 三试)
    assert 二试['重试链'] == [首, 次], 二试
    assert 三试['重试链'] == [首, 次, 末], 三试
    # 每次重试的 suggestion 指向自身，能继续往下串
    assert 次 in 二试['suggestion'] and 末 in 三试['suggestion'], (二试, 三试)


def test_失败到重试可整族回溯(输出):
    首败 = _取(输出, '首败')
    族 = _取(输出, '首族')
    assert [项['traceId'] for 项 in 族] == [
        首败['traceId'], _取(输出, '二试')['traceId'], _取(输出, '三试')['traceId'],
    ], 族
    assert all(项['根traceId'] == 首败['traceId'] for 项 in 族), 族
    assert all(项['工具名'] == '读超时' for 项 in 族), 族
    assert [项['状态'] for 项 in 族] == ['failed', 'failed', 'failed'], 族


def test_不可重试错误给出改方案依据(输出):
    未找到 = _取(输出, '未找到')
    异常体 = 未找到['运行时异常']
    assert 异常体['errorType'] == 'notFound' and 异常体['retryable'] is False, 异常体
    assert 异常体['code'] == 'TOOL_NOT_FOUND', 异常体
    assert '原样重试无意义' in 异常体['suggestion'], 异常体
    assert 未找到['traceId'] in 未找到['suggestion'], 未找到
    assert 'traceId=' not in 未找到['消息'], 未找到


def test_失败到改方案链路可关联(输出):
    未找到 = _取(输出, '未找到')
    改案 = _取(输出, '改案')
    参数改案 = _取(输出, '参数改案')
    父 = 未找到['traceId']
    for 结果 in (改案, 参数改案):
        assert 结果['状态'] == 'ok', 结果
        assert 结果['traceId'] != 父, ('改方案是一次新执行', 结果)
        assert 结果['父traceId'] == 父, ('改方案必须带上失败 traceId', 结果)
        assert 结果['根traceId'] == 父, 结果
        assert 结果['重试链'] == [父, 结果['traceId']], 结果
    assert 改案['traceId'] != 参数改案['traceId'], (改案, 参数改案)
    assert 改案['结果'] == 'ok:甲' and 参数改案['结果'] == 'ok:丙', (改案, 参数改案)
    # 原来的失败详情仍可按 traceId 取回，改方案不会覆盖父记录
    详情 = _取(输出, '未找到族')
    assert [项['traceId'] for 项 in 详情] == [
        父, 改案['traceId'], 参数改案['traceId'],
    ], 详情
    assert 详情[0]['状态'] == 'failed', 详情


def test_按traceId可取回失败结构化详情(输出):
    首败 = _取(输出, '首败')
    详情 = _取(输出, '首败详情')
    assert 详情['traceId'] == 首败['traceId'], 详情
    assert 详情['工具名'] == '读超时' and 详情['状态'] == 'failed', 详情
    assert 详情['错误信息'] == 首败['消息'], 详情
    assert 首败['traceId'] in 详情['建议'], 详情
    assert 详情['父traceId'] is None and 详情['根traceId'] == 首败['traceId'], 详情
    assert 详情['重试链'] == [首败['traceId']], 详情
    # 链尾（第三次重试）反查同样成立
    尾详情 = _取(输出, '三试详情')
    assert 尾详情['工具名'] == '读超时' and 尾详情['根traceId'] == 首败['traceId'], 尾详情
    assert 尾详情['重试链'] == _取(输出, '三试')['重试链'], 尾详情
    # 改方案的成功执行也可按 traceId 取回
    改案详情 = _取(输出, '改案详情')
    assert 改案详情['工具名'] == '读文件' and 改案详情['状态'] == 'ok', 改案详情
    assert 改案详情['父traceId'] == _取(输出, '未找到')['traceId'], 改案详情
    assert _取(输出, '未知详情') is None, ('未知 traceId 不应瞎编详情', 输出)


def test_独立失败不串链(输出):
    独败 = _取(输出, '独败')
    未找到 = _取(输出, '未找到')
    assert 独败['traceId'] != 未找到['traceId'], (独败, 未找到)
    assert 独败['根traceId'] == 独败['traceId'], ('无父链即为自己的根', 独败)
    assert 独败['重试链'] == [独败['traceId']], 独败
    族 = _取(输出, '独族')
    assert [项['traceId'] for 项 in 族] == [独败['traceId']], ('不得串进他人族链', 族)


def test_成功路径不冗余暴露仅在需要关联时出现(输出):
    纯成功 = _取(输出, '纯成功')
    assert 纯成功['状态'] == 'ok', 纯成功
    assert 'traceId' not in 纯成功 and '根traceId' not in 纯成功, ('纯成功不冗余暴露', 纯成功)
    assert 'suggestion' not in 纯成功 and '建议' not in 纯成功, 纯成功
    同族子 = _取(输出, '同族子')
    assert 同族子['状态'] == 'ok', 同族子
    assert 同族子['父traceId'] == 输出['纯成功id'], ('需要关联时才带 traceId', 同族子)
    assert 同族子['根traceId'] == 输出['纯成功id'], 同族子
    assert 同族子['重试链'] == [输出['纯成功id'], 同族子['traceId']], 同族子


def test_预算包装器不吞trace元数据且审计同源(输出):
    未找到 = _取(输出, '未找到')
    改案 = _取(输出, '改案')
    包装 = _取(输出, '包装改案')
    assert 包装['状态'] == 'failed', 包装
    assert 包装['traceId'] == 未找到['traceId'] or 包装['父traceId'] == 未找到['traceId'], 包装
    assert 包装['父traceId'] == 未找到['traceId'], ('包装器须原样透传父链', 包装)
    assert 包装['根traceId'] == 未找到['traceId'], 包装
    assert '运行时异常' in 包装 and 包装['运行时异常']['traceId'] == 包装['traceId'], 包装
    assert int(输出['审计首败数']) >= 1, ('失败执行的审计应带同一 traceId', 输出)
    assert int(输出['审计改案数']) >= 2, (
        '改方案 start/end 审计应带同一 traceId', 输出)
# -*- coding: utf-8 -*-
"""T-0515：工具执行 traceId 生成与穿插传递判据。

判据全部走 .light 侧真实执行管线（子进程 `python 运行.py <driver>`）：
  1. 每次执行生成唯一 traceId（UUID4 铸造，无 tracing 框架）；
  2. 失败响应带 suggestion（含 traceId）+ W3/T-0505 运行时异常信封的 traceId；
  3. 失败 → 重试：重试请求携带父 traceId，父链/根链/重试链可关联；
  4. 同族子操作（读文件 / read_file 同指 tool-fs-read）继承父 traceId，
     异族操作不串链；
  5. traceId 可由 追踪详情 / 按根追踪 / 审计 反查；
  6. 纯成功结果不新增可见字段（不回归既有成功路径返回结构），
     但异步/并发路径同样生成并记录 traceId。

反证（见 .hive/summary.md）：把 附trace元数据 的 需暴露 判定恒为假，
test_失败响应带suggestion与运行时异常traceId 与
test_失败到重试链路通过traceId关联 立红。
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
从 工具执行 导入 最后traceId, 造运行时异常, 具异步执行, 具并发执行, 级公开, 级私有
从 工具执行 导入 审计查询
从 工具面装配 导入 是同族工具
从 JSON 导入 序列化JSON

段落 成功处理(参数, 令牌):
  返回 "ok:" + 转字符串(参数["名"])

段落 失败处理(参数, 令牌):
  抛出 新建 错误("timeout while reading")

段落 计数带trace(记录表):
  设 数 为 0
  遍历 记录 之 记录表:
    如果 字典包含键(记录, "traceId") == 真:
      设 数 为 数 + 1
  返回 数

异步 段落 主程():
  # 放宽限流：本驱动单进程连跑十余次执行，避免默认 10/1000ms 误伤判据
  设 ex 为 建执行器(1000, 100000, 0, "滑动窗口")
  具注册工具(ex["注册"], "读文件", 级公开, 成功处理)
  具注册工具(ex["注册"], "read_file", 级公开, 成功处理)
  具注册工具(ex["注册"], "bash", 级公开, 成功处理)
  具注册工具(ex["注册"], "boom", 级公开, 失败处理)

  # 1) 每次执行一个唯一 traceId（成功结果本身不暴露）
  设 甲 为 执行工具(ex, "读文件", "public", "u", {"名": "甲"})
  设 甲id 为 最后traceId(ex)
  设 乙 为 执行工具(ex, "read_file", "public", "u", {"名": "乙"})
  设 乙id 为 最后traceId(ex)
  设 丙 为 执行工具(ex, "bash", "public", "u", {"名": "丙"})
  设 丙id 为 最后traceId(ex)
  打印("三次id=" + 序列化JSON([甲id, 乙id, 丙id]))
  打印("纯成功=" + 序列化JSON(甲))
  打印("同族判定=" + 序列化JSON([是同族工具("读文件", "read_file"),
    是同族工具("读文件", "bash")]))

  # 2) 失败 → suggestion → 重试：父链 / 根链 / 重试链
  设 失败 为 执行工具(ex, "boom", "public", "u", {})
  设 失败id 为 失败["traceId"]
  打印("失败=" + 序列化JSON(失败))
  设 重试 为 执行工具(ex, "boom", "public", "u", {}, "", 失败id)
  打印("重试=" + 序列化JSON(重试))
  # 模型也可把 traceId 直接塞回参数里（显式父链优先）
  设 参数重试 为 执行工具(ex, "boom", "public", "u", {"traceId": 失败id})
  打印("参数重试=" + 序列化JSON(参数重试))
  打印("失败详情=" + 序列化JSON(追踪详情(ex, 失败id)))
  打印("重试详情=" + 序列化JSON(追踪详情(ex, 重试["traceId"])))
  打印("未知道具详情=" + 序列化JSON(追踪详情(ex, "tr_不存在")))

  # 3) 同族子操作继承父链，异族不串链
  设 同族子 为 关联子操作(ex, 甲id, "read_file", "public", "u", {"名": "子"})
  设 异族子 为 关联子操作(ex, 甲id, "bash", "public", "u", {"名": "别族"})
  打印("同族子=" + 序列化JSON(同族子))
  打印("异族子=" + 序列化JSON(异族子))
  打印("族链=" + 序列化JSON(按根追踪(ex, 甲id)))

  # 4) 审计记录也带 traceId（可查询，不改既有键）
  设 事件表 为 审计查询(ex["审计"])
  打印("审计总数=" + 转字符串(长(事件表)))
  打印("审计带trace数=" + 转字符串(计数带trace(事件表)))

  # 5) W3/T-0505 运行时异常信封：traceId 由本卡填充，保守 retryable
  打印("异常结构=" + 序列化JSON(造运行时异常("notFound: no such file", "tr_手工")))

  # 6) 权限拒绝路径也算一次执行，有 traceId + suggestion
  设 私器 为 建执行器()
  具注册工具(私器["注册"], "priv", 级私有, 成功处理)
  设 拒绝 为 执行工具(私器, "priv", "public", "u", {})
  打印("拒绝=" + 序列化JSON(拒绝))

  # 7) 异步 / 并发路径同样生成并传递
  设 异步结果 为 等待 具异步执行(ex, "bash", "public", "u", {"名": "异步"})
  设 异步trace 为 最后traceId(ex)
  设 异步失败 为 等待 具异步执行(ex, "boom", "public", "u", {}, "", 失败id)
  设 并发表 为 等待 具并发执行(ex, [
    {"工具名": "bash", "参数": {"名": "并发"}, "父traceId": 甲id}
  ], "public", "u")
  打印("异步结果=" + 序列化JSON(异步结果))
  打印("异步trace=" + 异步trace)
  打印("异步失败=" + 序列化JSON(异步失败))
  打印("并发表=" + 序列化JSON(并发表))

异步 运行 主程()
'''


def _run(tmp_path):
    driver = tmp_path / 't0515_driver.light'
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
    proc, kv = _run(tmp_path_factory.mktemp('t0515'))
    assert proc.returncode == 0, (
        'traceId 驱动应 rc=0，实际 %s\n--- stdout ---\n%s\n--- stderr ---\n%s'
        % (proc.returncode, proc.stdout[-3000:], proc.stderr[-3000:])
    )
    return kv


def _取(kv, 键):
    assert 键 in kv, '驱动没有打印 %s；实际键：%s' % (键, sorted(kv))
    return json.loads(kv[键])


def test_每次执行生成唯一traceId(输出):
    三次 = _取(输出, '三次id')
    assert len(三次) == 3 and len(set(三次)) == 3, ('traceId 应三次都不同', 三次)
    for 编号 in 三次:
        assert 编号.startswith('tr_') and len(编号) > 10, ('traceId 形态', 编号)
    assert 输出['异步trace'].startswith('tr_'), 输出['异步trace']


def test_纯成功路径不冗余暴露traceId(输出):
    成功 = _取(输出, '纯成功')
    assert 成功['状态'] == 'ok', 成功
    assert 'traceId' not in 成功, ('成功结果不得新增可见字段', 成功)
    assert 'suggestion' not in 成功 and '建议' not in 成功, 成功


def test_同族工具判定来自叶子映射(输出):
    判定 = _取(输出, '同族判定')
    assert 判定 == [True, False], ('读文件/read_file 同族，读文件/bash 异族', 判定)


def test_失败响应带suggestion与运行时异常traceId(输出):
    失败 = _取(输出, '失败')
    assert 失败['状态'] == 'failed' and 失败['错误码'] == 'failed', 失败
    trace = 失败['traceId']
    assert trace.startswith('tr_'), 失败
    assert trace in 失败['suggestion'], ('suggestion 必须能反查本次执行', 失败)
    assert trace in 失败['建议'], 失败
    异常体 = 失败['运行时异常']
    assert 异常体['traceId'] == trace, ('T-0505 traceId 字段必须被填充', 异常体)
    assert 异常体['errorType'] == 'timeout', 异常体
    assert 异常体['retryable'] is True, 异常体
    assert 失败['消息'] == 'timeout while reading', ('失败文案不得被 traceId 改写', 失败)
    # 既有键一个不少
    assert 失败['结果'] is None, 失败


def test_失败到重试链路通过traceId关联(输出):
    失败 = _取(输出, '失败')
    重试 = _取(输出, '重试')
    首 = 失败['traceId']
    次 = 重试['traceId']
    assert 首 != 次, ('重试是一次新执行，应有自己的 traceId', 首, 次)
    assert 重试['父traceId'] == 首, ('重试必须携带失败 traceId 作父链', 重试)
    assert 重试['根traceId'] == 首, ('失败→重试应同根', 重试)
    assert 重试['重试链'] == [首, 次], ('重试链应完整', 重试)
    详情 = _取(输出, '重试详情')
    assert 详情['父traceId'] == 首 and 详情['根traceId'] == 首, 详情
    assert 详情['重试链'] == [首, 次], 详情
    assert 次 in 重试['suggestion'] and 次 in 重试['运行时异常']['traceId'], 重试
    assert 首 in 失败['suggestion'], 失败


def test_模型可把traceId塞回参数完成重试(输出):
    失败 = _取(输出, '失败')
    参数重试 = _取(输出, '参数重试')
    assert 参数重试['父traceId'] == 失败['traceId'], 参数重试
    assert 参数重试['根traceId'] == 失败['traceId'], 参数重试
    assert 参数重试['重试链'][0] == 失败['traceId'], 参数重试


def test_同族子操作继承父链异族不串链(输出):
    三次 = _取(输出, '三次id')
    父 = 三次[0]
    同族子 = _取(输出, '同族子')
    异族子 = _取(输出, '异族子')
    assert 同族子['父traceId'] == 父, ('同族子操作必须继承父 traceId', 同族子)
    assert 同族子['根traceId'] == 父, 同族子
    assert 同族子['重试链'] == [父, 同族子['traceId']], 同族子
    assert '父traceId' not in 异族子, ('异族操作不得串进父链', 异族子)
    族链 = _取(输出, '族链')
    assert [项['traceId'] for 项 in 族链] == [父, 同族子['traceId']], 族链
    assert all(项['根traceId'] == 父 for 项 in 族链), 族链


def test_失败详情可按traceId查询未知id返回空(输出):
    失败 = _取(输出, '失败')
    详情 = _取(输出, '失败详情')
    assert 详情['traceId'] == 失败['traceId'], 详情
    assert 详情['状态'] == 'failed' and 详情['工具名'] == 'boom', 详情
    assert 详情['错误信息'] == 失败['消息'], 详情
    assert 失败['traceId'] in 详情['建议'], 详情
    assert _取(输出, '未知道具详情') is None, ('未知 traceId 不应瞎编详情', 输出)


def test_审计记录带traceId可被后续结果消费(输出):
    总数 = int(输出['审计总数'])
    带trace = int(输出['审计带trace数'])
    assert 总数 >= 12, ('每次执行至少 start/end 或一条失败记录', 总数)
    assert 带trace == 总数, ('本卡所有执行路径的审计都应带 traceId', 总数, 带trace)


def test_运行时异常结构保守可重试判定(输出):
    异常体 = _取(输出, '异常结构')
    assert 异常体 == {
        'errorType': 'notFound', 'message': 'notFound: no such file',
        'retryable': False, 'traceId': 'tr_手工',
    }, ('未找到属不可重试，且 traceId 必须来自调用方', 异常体)


def test_权限拒绝路径也带traceId建议(输出):
    拒绝 = _取(输出, '拒绝')
    assert 拒绝['状态'] == 'permission_denied', 拒绝
    assert 拒绝['traceId'].startswith('tr_'), 拒绝
    assert 拒绝['traceId'] in 拒绝['suggestion'], 拒绝
    assert '不建议原地重试' in 拒绝['suggestion'], 拒绝


def test_异步与并发路径同样穿插traceId(输出):
    失败 = _取(输出, '失败')
    异步结果 = _取(输出, '异步结果')
    异步失败 = _取(输出, '异步失败')
    并发表 = _取(输出, '并发表')
    assert 'traceId' not in 异步结果, ('异步纯成功同样不冗余暴露', 异步结果)
    assert 输出['异步trace'].startswith('tr_'), 输出['异步trace']
    assert 异步失败['父traceId'] == 失败['traceId'], 异步失败
    assert 异步失败['根traceId'] == 失败['traceId'], 异步失败
    assert len(并发表) == 1 and 并发表[0]['状态'] == 'ok', 并发表
    assert 并发表[0]['父traceId'] == _取(输出, '三次id')[0], 并发表

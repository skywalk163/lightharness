# -*- coding: utf-8 -*-
"""T-0449 补充判据：编辑文件工具走「真执行管线」（工具注册表 → schema → 派发）。

与 `test_T0449_编辑工具.py` 的分工：
  · 那份直接调 `编辑文件处理`（纯处理面，依赖注入桩，零环境）；
  · 这份走 `工具注册表.注册 / 执行`（模型侧真实入口：别名归一 → JSON Schema 校验 →
    派发 → 结果归一为块表），并且**不开桩**——用 `HARNESS_ROOT` 指到临时目录，
    顺带把真实模式的 `解析安全路径` 越界拦截也压住。

覆盖：
  1. 注册进注册表：名单含「编辑文件」，描述表里 5 个参数键齐全；
  2. 管线成功：isError=假、content 是 text 块、文案含替换次数，文件内容逐字正确；
  3. 别名归一：英文 `file_path` 被归一到 `路径`，`别名归一` 有记录（模型键名漂移兜底）；
  4. schema 门禁：缺 `路径` → PARAM_SCHEMA_INVALID，文案带字段路径与原因；
  5. 业务错误不升级成异常：未命中 → isError=真 且 error 为空（不是 TOOL_EXECUTION_FAILED）；
  6. 真实模式越界：`../escape.txt` → 路径安全校验失败，临时目录外的文件不受影响；
  7. 统计表：调用/成功/失败计数与上面几次调用一致。
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

DRIVER = '''
从 文件系统 导入 读取文件, 写入文件
从 内置核心字典 导入 字典键列表
从 工具 导入 工具注册表
从 工具_编辑文件 导入 注册编辑文件工具

设 根 为 环境变量("T0449_ROOT", "")

段落 跑(注册表, 参数):
  返回 注册表.执行("编辑文件", 序列化JSON(参数))

段落 主程():
  设 注册表 为 新建 工具注册表()
  打印("注册=" + 转字符串(注册编辑文件工具(注册表)))
  打印("名单=" + 序列化JSON(注册表.名单()))
  设 模式 为 注册表.描述表()[0]["parameters"]
  打印("参数键=" + 序列化JSON(字典键列表(模式["properties"])))
  打印("必填=" + 序列化JSON(模式["required"]))

  设 路径 为 根 + "/管线.txt"
  写入文件(路径, "alpha\\nbeta\\n")
  设 成功 为 跑(注册表, ["路径": 路径, "旧文本": "beta", "新文本": "BETA"])
  打印("成功=" + 序列化JSON(成功))
  打印("成功内容=" + 序列化JSON(读取文件(路径)))

  写入文件(路径, "one\\ntwo\\n")
  设 别名 为 跑(注册表, ["file_path": 路径, "旧文本": "two", "新文本": "TWO"])
  打印("别名=" + 序列化JSON(别名))
  打印("别名内容=" + 序列化JSON(读取文件(路径)))

  设 缺参 为 跑(注册表, ["旧文本": "one", "新文本": "ONE"])
  打印("缺参=" + 序列化JSON(缺参))

  设 未命中 为 跑(注册表, ["路径": 路径, "旧文本": "zzz", "新文本": "Z"])
  打印("未命中=" + 序列化JSON(未命中))

  设 越界 为 跑(注册表, ["路径": "../escape.txt", "旧文本": "a", "新文本": "b"])
  打印("越界=" + 序列化JSON(越界))

  设 统计 为 注册表.统计()["编辑文件"]
  打印("统计=" + 序列化JSON(统计))

主程()
'''


def _run(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    driver = tmp_path / 't0449_管线驱动.light'
    driver.write_text(DRIVER, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['T0449_ROOT'] = str(root).replace('\\', '/')
    env['HARNESS_ROOT'] = str(root).replace('\\', '/')
    proc = subprocess.run(
        [sys.executable, RUNNER, str(driver)],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
        errors='replace', timeout=TIMEOUT_SEC, env=env,
    )
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc, kv, root


@pytest.fixture(scope='module')
def 管线(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('t0449管线')
    proc, kv, root = _run(tmp)
    assert proc.returncode == 0, (
        '执行管线驱动应 rc=0，实际 %s\n--- stdout ---\n%s\n--- stderr ---\n%s'
        % (proc.returncode, proc.stdout[-2000:], proc.stderr[-2000:])
    )
    return kv, root.parent / 'escape.txt'


def _取(kv, 键):
    assert 键 in kv, '驱动没有打印 %s，实际键：%s' % (键, sorted(kv))
    return json.loads(kv[键])


def _块文本(结果):
    """执行管线把处理函数返回的裸字符串包成单 text 块（序列化JSON 后入块），这里还原。"""
    块表 = 结果['content']
    assert isinstance(块表, list) and 块表, ('content 契约是块表', 结果)
    assert 块表[0].get('type') == 'text', ('首个块应是 text 块', 结果)
    文本 = 块表[0]['text']
    try:
        还原 = json.loads(文本)
    except ValueError:
        还原 = 文本
    if isinstance(还原, str):
        return 还原
    return 文本


# ---------------------------------------------------------------------------
# 1. 注册进注册表 + schema 形状
# ---------------------------------------------------------------------------
def test_注册后名单含编辑文件且参数键齐全(管线):
    kv, _ = 管线
    assert kv['注册'] == 'True', ('注册应返回 真（转字符串 走英文 True 口径）', kv['注册'])
    assert '编辑文件' in _取(kv, '名单'), _取(kv, '名单')
    assert set(_取(kv, '参数键')) == {'路径', '旧文本', '新文本', '全部替换', '插入行'}, _取(kv, '参数键')
    assert _取(kv, '必填') == ['路径'], _取(kv, '必填')


# ---------------------------------------------------------------------------
# 2. 管线成功：块表 + 文案 + 文件内容
# ---------------------------------------------------------------------------
def test_管线跑通替换且结果归一为文本块(管线):
    kv, _ = 管线
    结果 = _取(kv, '成功')
    assert 结果['isError'] is False, 结果
    assert 结果['concludesTurn'] is False, 结果
    文案 = _块文本(结果)
    assert '替换次数: 1' in 文案, ('管线结果应保留替换次数', 文案)
    assert _取(kv, '成功内容') == 'alpha\nBETA\n', '文件内容应逐字为 alpha/BETA'


# ---------------------------------------------------------------------------
# 3. 别名归一：file_path → 路径
# ---------------------------------------------------------------------------
def test_英文键别名归一到中文参数(管线):
    kv, _ = 管线
    结果 = _取(kv, '别名')
    assert 结果['isError'] is False, ('file_path 应被归一成 路径 后跑通', 结果)
    assert ['file_path', '路径'] in 结果['别名归一'], ('应记录改名', 结果.get('别名归一'))
    assert '替换次数: 1' in _块文本(结果), _块文本(结果)


# ---------------------------------------------------------------------------
# 4. schema 门禁：缺 路径
# ---------------------------------------------------------------------------
def test_缺路径被schema门禁拦住(管线):
    kv, _ = 管线
    结果 = _取(kv, '缺参')
    assert 结果['isError'] is True, 结果
    assert 结果['error']['代码'] == 'PARAM_SCHEMA_INVALID', 结果['error']
    文案 = _块文本(结果)
    assert '路径' in 文案, ('校验失败文案应带字段路径', 文案)


# ---------------------------------------------------------------------------
# 5. 业务错误留在结果里，不升级成 TOOL_EXECUTION_FAILED
# ---------------------------------------------------------------------------
def test_未命中不降级成流水线异常且文案可达(管线):
    kv, _ = 管线
    结果 = _取(kv, '未命中')
    assert 结果['error'] is None, ('处理函数应回 造工具结果 而不是抛错', 结果.get('error'))
    文案 = _块文本(结果)
    assert '未找到' in 文案, 文案
    assert '行号范围' in 文案, 文案
    assert '工具执行失败' not in 文案, ('不该降级成流水线异常文案', 文案)


# ---------------------------------------------------------------------------
# 6. 真实模式越界拦截（HARNESS_ROOT 之外一律拒绝）
# ---------------------------------------------------------------------------
def test_越界路径被拒绝且目录外不受影响(管线):
    kv, 外部文件 = 管线
    结果 = _取(kv, '越界')
    assert '路径安全校验失败' in _块文本(结果), _块文本(结果)
    assert not 外部文件.exists(), '临时目录外的文件不应被创建/写入'


# ---------------------------------------------------------------------------
# 5b. 已知缺口（不属于本卡允许路径，登记给 T-0456 接线）
# ---------------------------------------------------------------------------
@pytest.mark.xfail(
    strict=False,
    reason='src/工具.light 派发分支把 isError 硬写成 假，只传播 content/concludesTurn；'
           '处理函数回 造工具结果(消息, 真) 时模型侧拿到的 isError 仍是假。'
           '本卡不改 工具.light（接线归 T-0456），修好后此用例转 xpass。')
def test_已知缺口_业务错误的isError未传播到管线(管线):
    kv, _ = 管线
    assert _取(kv, '未命中')['isError'] is True
    assert _取(kv, '越界')['isError'] is True


# ---------------------------------------------------------------------------
# 7. 统计表口径
# ---------------------------------------------------------------------------
def test_执行统计与调用次数一致(管线):
    kv, _ = 管线
    统计 = _取(kv, '统计')
    # 5 次执行：成功 / 别名成功 / 缺参 / 未命中 / 越界（缺参在校验阶段就返回，也计调用）
    assert 统计['调用次数'] == 5, 统计
    assert 统计['别名归一次数'] == 1, 统计
    # 成功/失败 两列当前只反映「有没有抛异常」：isError 未传播（见 已知缺口 用例），
    # 所以这里不断言，免得把 工具.light 的缺口写成本卡的期望。
    assert 统计['成功次数'] + 统计['失败次数'] == 5, 统计

# -*- coding: utf-8 -*-
"""T-0499：W1/T1.4 近似工具合并 —— ctx 装配族四合一判据。

差异分析（已发卡面评论）：原 tool_20/21/22/23 = 压缩选块 / 压缩摘要 /
上下文装配 / 上下文装配报告，四者都只作用于 分块列表.light 的不可变
分块链，差异在参数形态与后处理，执行路径同为纯函数；按
(输入, mode, 参数) 缓存与幂等语义不变 → 走【合并路线】。

三层判据：
  1. 能力不丢：mode 四选一覆盖选块 / 截断摘要 / 装配 / 装配报告，
     四个原名作为别名归一到同一入口；
  2. 纯函数与缓存：重复调用结果一致、入参不变、不同参数分流；
  3. 错误契约：非法 mode 返回 T-0504 同字段信封，suggestion 由枚举表
     与决策树推导，并可由 错误增强.造校验错误 注入同一只真信封。

两条 Light 子进程（合并逻辑 + 装配面声明），规避 xdist 下多个
运行.py 同时编译 .light 触发 worker crash（pytest.ini --timeout=60）。

运行方式：python -m pytest -q tests/test_T0499_ctx装配合并.py
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180


def _run(driver, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC,
                          env=env, encoding='utf-8', errors='replace')
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, proc.stdout + proc.stderr, kv


MERGE_DRIVER = '''
从 分块列表 导入 追加分块, 遍历分块, 校验分块, ctx装配, ctx模式表, ctx原名表, ctx别名表, ctx模式归一, ctx建议文本
从 内置核心字符串 导入 字符串包含

段落 逗号连接(表):
  设 文 为 ""
  设 i 为 0
  遍历 项 之 表:
    如果 i > 0:
      设 文 为 文 + ","
    设 文 为 文 + 转字符串(项)
    设 i 为 i + 1
  返回 文

段落 主程():
  设 头 为 空
  设 i 为 0
  当 i < 70:
    设 头 为 追加分块(头, "项" + 转字符串(i))
    设 i 为 i + 1
  打印 "分块校验=" + 转字符串(校验分块(头))
  打印 "展平数=" + 转字符串(长(遍历分块(头)))

  # ---- 1) 选块：跨块边界取 [64,67)，另一路按关键词过滤 ----
  设 选 为 ctx装配(头, "选块", {"起始": 64, "上限": 3})
  打印 "选块模式=" + 选["mode"]
  打印 "选块值=" + 逗号连接(选["结果"])
  设 关 为 ctx装配(头, "选块", {"关键词": "项6"})
  打印 "关键词数=" + 转字符串(长(关["结果"]))

  # ---- 2) 截断摘要：超限加省略标记；未超限原文照返 ----
  设 截 为 ctx装配("这是一段很长的中文文本需要压缩", "截断摘要", {"上限": 6, "省略标记": "..."})
  打印 "截断值=" + 转字符串(截["结果"])
  打印 "截断长=" + 转字符串(长(截["结果"]))
  设 短 为 ctx装配("abc", "截断摘要", {"上限": 6})
  打印 "短值=" + 转字符串(短["结果"])

  # ---- 3) 装配：分隔符 + 前缀 + 后缀 ----
  设 数表 为 ["甲", "乙", "丙"]
  设 装 为 ctx装配(数表, "装配", {"分隔符": "|", "前缀": "[", "后缀": "]"})
  打印 "装配值=" + 转字符串(装["结果"])

  # ---- 4) 装配报告：块数/字符数/是否截断/丢字符数 ----
  设 报 为 ctx装配(数表, "装配报告", {"分隔符": "|", "上限": 3})
  打印 "报块数=" + 转字符串(报["结果"]["块数"])
  打印 "报字符=" + 转字符串(报["结果"]["字符数"])
  打印 "报截断=" + 转字符串(报["结果"]["已截断"])
  打印 "报丢字=" + 转字符串(报["结果"]["丢字符数"])

  # ---- 5) 四原名全部收进别名表，能力零丢失 ----
  遍历 名 之 ctx原名表:
    打印 "别名_" + 名 + "=" + ctx模式归一(名)
  打印 "模式数=" + 转字符串(长(ctx模式表))
  打印 "原名数=" + 转字符串(长(ctx原名表))
  打印 "别名表长=" + 转字符串(长(字典键列表(ctx别名表)))

  # ---- 6) 幂等/缓存：同入参同结果，改参数分流，入参不被改写 ----
  设 a1 为 ctx装配(数表, "装配", {"分隔符": "-"})
  设 a2 为 ctx装配(数表, "装配", {"分隔符": "-"})
  打印 "幂等=" + 转字符串(a1["结果"] == a2["结果"])
  设 d1 为 ctx装配(数表, "装配", {"分隔符": "|"})
  设 d2 为 ctx装配(数表, "装配", {"分隔符": "#"})
  打印 "参数分流=" + 转字符串(d1["结果"] != d2["结果"])
  打印 "原表未变=" + 转字符串(长(数表) == 3 且 数表[0] == "甲" 且 数表[2] == "丙")

  # ---- 7) 非法 mode → T-0504 同字段信封 ----
  设 坏 为 ctx装配(数表, "随便选")
  打印 "坏ok=" + 转字符串(坏["ok"])
  打印 "坏type=" + 转字符串(坏["type"])
  打印 "坏errorType=" + 转字符串(坏["errorType"])
  打印 "坏code=" + 转字符串(坏["code"])
  打印 "坏field=" + 转字符串(坏["field"])
  打印 "坏reason=" + 转字符串(坏["reason"])
  打印 "坏retryable=" + 转字符串(坏["retryable"])
  打印 "坏建议含决策树=" + 转字符串(字符串包含(坏["suggestion"], "mode=选块") 且 字符串包含(坏["suggestion"], "mode=装配报告"))
  打印 "坏建议含原名=" + 转字符串(字符串包含(ctx建议文本("随便选"), "压缩选块"))
主程()
'''

DECISION_DRIVER = '''
从 工具面装配 导入 ctx装配线名, ctx装配原名表, ctx装配模式表, ctx装配别名表, ctx装配决策树, ctx装配描述, ctx装配模式归一, ctx装配建议, ctx装配Schema, ctx装配错误载荷
从 错误增强 导入 造校验错误
从 工具 导入 校验参数
从 内置核心字符串 导入 字符串包含

段落 逗号连接(表):
  设 文 为 ""
  设 i 为 0
  遍历 项 之 表:
    如果 i > 0:
      设 文 为 文 + ","
    设 文 为 文 + 转字符串(项)
    设 i 为 i + 1
  返回 文

段落 主程():
  打印 "线名=" + ctx装配线名
  打印 "模式表=" + 逗号连接(ctx装配模式表)
  打印 "原名表=" + 逗号连接(ctx装配原名表)
  设 树 为 ctx装配决策树()
  设 四意 为 字符串包含(树, "mode=选块") 且 字符串包含(树, "mode=截断摘要") 且 字符串包含(树, "mode=装配") 且 字符串包含(树, "mode=装配报告")
  打印 "树含四意图=" + 转字符串(四意)

  # 描述即决策树：模型按意图选 mode，不必知道实现差异
  设 描 为 ctx装配描述("压缩选块")
  打印 "描述并入=" + 转字符串(字符串包含(描, "ctx_assembly"))
  设 描命中 为 字符串包含(描, "mode=选块") 且 字符串包含(描, "mode=装配报告")
  打印 "描述含决策树=" + 转字符串(描命中)

  # suggestion 由枚举表推导，且与 T-0504 真信封同口径
  设 建 为 ctx装配错误载荷("瞎选")
  打印 "建type=" + 转字符串(建["type"])
  打印 "建errorType=" + 转字符串(建["errorType"])
  打印 "建code=" + 转字符串(建["code"])
  打印 "建field=" + 转字符串(建["field"])
  打印 "建reason=" + 转字符串(建["reason"])
  打印 "建retryable=" + 转字符串(建["retryable"])
  设 注 为 ctx装配错误载荷("瞎选", 空, 造校验错误)
  打印 "注type=" + 转字符串(注["type"])
  打印 "注code=" + 转字符串(注["code"])
  打印 "注入口同建议=" + 转字符串(建["suggestion"] == 注["suggestion"])
  设 建建议 为 字符串包含(建["suggestion"], "mode=选块") 且 字符串包含(建["suggestion"], "改为四选一")
  打印 "建议可操作=" + 转字符串(建建议)

  # schema 的枚举直接取模式表，换表即换建议口径（非硬编码）
  设 模 为 ctx装配Schema()
  设 枚 为 模["properties"]["mode"]["enum"]
  打印 "schema枚举=" + 逗号连接(枚)
  设 载 为 校验参数(模, {"mode": "瞎选"})
  打印 "越界错数=" + 转字符串(长(载))

  # 别名归一覆盖原名与英文意图名；未知不瞎猜
  打印 "别名压缩摘要=" + ctx装配模式归一("压缩摘要")
  打印 "别名report=" + ctx装配模式归一("report")
  打印 "别名未知=" + "[" + ctx装配模式归一("瞎选") + "]"
主程()
'''


def _merge(tmp_path):
    return _run(MERGE_DRIVER, tmp_path, 't0499_merge.light')


def _decision(tmp_path):
    return _run(DECISION_DRIVER, tmp_path, 't0499_decision.light')


def test_四模式覆盖原四工具全部能力(tmp_path):
    rc, out, kv = _merge(tmp_path)
    assert rc == 0, out
    assert kv.get('分块校验') == 'True' and kv.get('展平数') == '70', out
    # 选块跨块边界：头块满 64 后新块从 项64 起
    assert kv.get('选块模式') == '选块', out
    assert kv.get('选块值') == '项64,项65,项66', out
    assert int(kv.get('关键词数', '0')) >= 10, out
    # 截断摘要：超限加省略标记且总长=上限，未超限原文照返
    assert kv.get('截断值') == '这是一...', out
    assert kv.get('截断长') == '6', out
    assert kv.get('短值') == 'abc', out
    # 装配：分隔符 + 前后缀
    assert kv.get('装配值') == '[甲|乙|丙]', out
    # 装配报告：5 字符超 3 上限 → 截断，丢 2 字符
    assert kv.get('报块数') == '3' and kv.get('报字符') == '5', out
    assert kv.get('报截断') == 'True' and kv.get('报丢字') == '2', out


def test_四原名保留且幂等缓存不破坏(tmp_path):
    rc, out, kv = _merge(tmp_path)
    assert rc == 0, out
    assert kv.get('模式数') == '4' and kv.get('原名数') == '4', out
    assert int(kv.get('别名表长', '0')) >= 4, out
    for name, mode in [('压缩选块', '选块'), ('压缩摘要', '截断摘要'),
                       ('上下文装配', '装配'), ('上下文装配报告', '装配报告')]:
        assert kv.get('别名_' + name) == mode, (name, out)
    assert kv.get('幂等') == 'True', out
    assert kv.get('参数分流') == 'True', out
    assert kv.get('原表未变') == 'True', out


def test_非法mode返回T0504同字段信封(tmp_path):
    rc, out, kv = _merge(tmp_path)
    assert rc == 0, out
    assert kv.get('坏ok') == 'False', out
    assert kv.get('坏type') == 'validation', out
    assert kv.get('坏errorType') == 'schema', out
    assert kv.get('坏code') == 'PARAM_SCHEMA_INVALID', out
    assert kv.get('坏field') == '参数.mode', out
    assert kv.get('坏reason') == 'enum', out
    assert kv.get('坏retryable') == 'False', out
    assert kv.get('坏建议含决策树') == 'True', out
    assert kv.get('坏建议含原名') == 'True', out


def test_装配面决策树与建议口径对齐(tmp_path):
    rc, out, kv = _decision(tmp_path)
    assert rc == 0, out
    assert kv.get('线名') == 'ctx_assembly', out
    assert kv.get('模式表') == '选块,截断摘要,装配,装配报告', out
    assert kv.get('原名表') == '压缩选块,压缩摘要,上下文装配,上下文装配报告', out
    assert kv.get('树含四意图') == 'True', out
    assert kv.get('描述并入') == 'True' and kv.get('描述含决策树') == 'True', out
    # 与 T-0504 信封同字段：不另起一套 suggestion 口径
    assert kv.get('建type') == 'validation' and kv.get('建errorType') == 'schema', out
    assert kv.get('建code') == 'PARAM_SCHEMA_INVALID' and kv.get('建field') == '参数.mode', out
    assert kv.get('建reason') == 'enum' and kv.get('建retryable') == 'False', out
    assert kv.get('注type') == 'validation' and kv.get('注code') == 'PARAM_SCHEMA_INVALID', out
    assert kv.get('注入口同建议') == 'True', out
    assert kv.get('建议可操作') == 'True', out
    assert kv.get('schema枚举') == '选块,截断摘要,装配,装配报告', out
    assert int(kv.get('越界错数', '0')) > 0, out
    assert kv.get('别名压缩摘要') == '截断摘要' and kv.get('别名report') == '装配报告', out
    assert kv.get('别名未知') == '[]', out

# -*- coding: utf-8 -*-
"""W3/T3.1 契约回归：错误增强 v3 JSON 契约（校验信封与运行时信封同族）。

这张测试是 T-0504 卡面 verify 点名的契约闸门（tests/test_T0450_错误增强_v3_json_contract.py）。
仓内历史 T-0450 是「作业工具」卡，本文件此前不存在；按 verify 要求补齐为**契约测试**，
不新增实现，只钉住：

  1. R18 既有结构化错误契约不回归：{码,消息,详情,时间} 形状 / JSON 串抛出 / 解析还原 /
     错误码·错误消息提取 / 带名错误 name 比较；
  2. W3 新信封（造校验错误）JSON 键名固定：type/errorType/code/field/reason/message/
     suggestion/retryable/traceId/details；
  3. 同族：校验信封与运行时信封（造错误信封 传 runtime）**键集完全相同**，只有取值不同，
     避免 T-0504 / T-0505 两套 schema。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 240

DRIVER = '''
从 错误增强 导入 造结构化错误, 抛出结构化错误, 解析错误消息, 获取最后异常, 错误码, 错误消息, 造带名错误, 错误名, 是名错误, 造错误信封, 造校验错误, 是校验错误, 信封可否重试
从 JSON 导入 序列化JSON, 解析JSON

段落 触发结构化抛出():
  抛出结构化错误("E_DEMO", "出错了", {"字段": "x"})

段落 触发带名抛出():
  抛出带名错误("DemoError", "带名出错", "DEMO", {"字段": "y"})

段落 主程():
  设 e1 为 造结构化错误("E_DEMO", "出错了", {"字段": "x"})
  打印 "旧_键=" + 转字符串(字典键列表(e1))
  打印 "旧_码=" + 转字符串(错误码(e1))
  打印 "旧_消息=" + 转字符串(错误消息(e1))
  打印 "旧_时间=" + 转字符串(e1["时间"])

  设 旧串 为 序列化JSON(e1)
  打印 "旧_串键=" + 转字符串(字典键列表(解析错误消息(旧串)))

  设 抛出异常 为 ""
  尝试:
    触发结构化抛出()
  捕获 异常 为 e:
    设 抛出异常 为 转字符串(e)
  打印 "抛_解析码=" + 转字符串(错误码(抛出异常))
  打印 "抛_解析消息=" + 转字符串(错误消息(抛出异常))
  打印 "抛_最后异常一致=" + 转字符串(获取最后异常() == 抛出异常)

  设 带名 为 造带名错误("DemoError", "带名出错", "DEMO", {"字段": "y"})
  打印 "名_错误名=" + 转字符串(错误名(带名))
  打印 "名_是名=" + 转字符串(是名错误(带名, "DemoError"))
  打印 "名_非名=" + 转字符串(是名错误(带名, "OtherError"))

  设 校验 为 造校验错误("参数.秒", "missing", "参数.秒：缺少必需字段 秒",
    "缺少必填字段 秒（number）", {"路径": ["参数", "秒"]})
  设 校验串 为 序列化JSON(校验)
  打印 "校_串=" + 校验串
  打印 "校_键=" + 转字符串(字典键列表(校验))
  打印 "校_是=" + 转字符串(是校验错误(校验))
  打印 "校_可重试=" + 转字符串(信封可否重试(校验))
  打印 "校_往返一致=" + 转字符串(解析JSON(校验串) == 校验)

  设 运行 为 造错误信封("runtime", "timeout", "TOOL_TIMEOUT", "执行超时",
    "可原样重试一次", 真, 空, 空, "trace-1", {"毫秒": 30000})
  打印 "运_键=" + 转字符串(字典键列表(运行))
  打印 "运_可重试=" + 转字符串(信封可否重试(运行))
  打印 "族_键数=" + 转字符串(长(字典键列表(校验)))
  打印 "族_同键=" + 转字符串(字典键列表(校验) == 字典键列表(运行))
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


def test_旧结构化错误契约不回归(tmp_path):
    rc, out, kv = _run(DRIVER, tmp_path, 't0450_old.light')
    assert rc == 0, out
    assert kv.get('旧_键') == "['码', '消息', '详情', '时间']", out
    assert kv.get('旧_码') == 'E_DEMO', out
    assert kv.get('旧_消息') == '出错了', out
    assert kv.get('旧_时间') != '', out
    assert kv.get('旧_串键') == "['码', '消息', '详情', '时间']", out


def test_抛出与解析契约不回归(tmp_path):
    rc, out, kv = _run(DRIVER, tmp_path, 't0450_throw.light')
    assert rc == 0, out
    assert kv.get('抛_解析码') == 'E_DEMO', out
    assert kv.get('抛_解析消息') == '出错了', out
    assert kv.get('抛_最后异常一致') in ('True', '真'), out


def test_带名错误契约不回归(tmp_path):
    rc, out, kv = _run(DRIVER, tmp_path, 't0450_named.light')
    assert rc == 0, out
    assert kv.get('名_错误名') == 'DemoError', out
    assert kv.get('名_是名') in ('True', '真'), out
    assert kv.get('名_非名') in ('False', '假'), out


def test_校验信封JSON键名固定(tmp_path):
    rc, out, kv = _run(DRIVER, tmp_path, 't0450_envelope.light')
    assert rc == 0, out
    assert kv.get('校_键') == ("['type', 'errorType', 'code', 'field', 'reason', "
                            "'message', 'suggestion', 'retryable', 'traceId', 'details']"), out
    assert kv.get('校_是') in ('True', '真'), out
    assert kv.get('校_可重试') in ('False', '假'), out
    assert kv.get('校_往返一致') in ('True', '真'), out
    for piece in ('"type": "validation"', '"errorType": "schema"',
                  '"code": "PARAM_SCHEMA_INVALID"', '"field": "参数.秒"',
                  '"retryable": false', '"traceId": null'):
        assert piece in kv.get('校_串', ''), (piece, out)


def test_校验与运行时信封同族(tmp_path):
    rc, out, kv = _run(DRIVER, tmp_path, 't0450_family.light')
    assert rc == 0, out
    assert kv.get('族_同键') in ('True', '真'), out
    assert kv.get('族_键数') == '10', out
    assert kv.get('运_可重试') in ('True', '真'), out

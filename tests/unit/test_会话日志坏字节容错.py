# -*- coding: utf-8 -*-
"""回归：会话日志尾部出现非法 UTF-8 坏字节时，读入与增量保存不应整段失败。

复现现场：~/.lightharness/legacy/.../session.jsonl 末尾留下 b'\\xa5\\xe5\\x85\\xb7"}}}'
（0xa5 非法起始字节），web 保存走「读全文 -> 追加 -> 覆写」路径时严格 UTF-8
解码抛 UnicodeDecodeError，包装成「会话保存失败」。修复后坏行跳过，正常行保留。
"""
from test_support import run_light_source, assert_success, out_contains


_SETUP = '''
从 持久化 导入 日志路径
从 文件系统 导入 创建目录
段落 主程序:
  创建目录("probe_root/--proj--/sess1")
  设 路径 为 日志路径("probe_root", "proj", "sess1")
  设 f 为 打开文件(路径, "wb")
  f.write(b'{"type": "session", "version": {"major": 3, "minor": 0}, "id": "sess1", "createdAt": 1000, "cwd": "proj", "delegationDepth": 0}\\n{"type": "user/message", "seq": 1, "time": 1001, "data": {"text": "hi"}}\\n\\xa5\\xe5\\x85\\xb7"}}}\\n')
  f.close()
'''


def test_坏字节尾行_宽容读入跳过坏行保留有效事件():
    r = run_light_source('''
从 持久化 导入 日志路径, 读入会话宽容
从 文件系统 导入 创建目录
段落 主程序:
  创建目录("probe_root/--proj--/sess1")
  设 f 为 打开文件(日志路径("probe_root", "proj", "sess1"), "wb")
  f.write(b'{"type": "session", "version": {"major": 3, "minor": 0}, "id": "sess1", "createdAt": 1000, "cwd": "proj", "delegationDepth": 0}\\n{"type": "user/message", "seq": 1, "time": 1001, "data": {"text": "hi"}}\\n\\xa5\\xe5\\x85\\xb7"}}}\\n')
  f.close()
  设 s 为 读入会话宽容("probe_root", "proj", "sess1")
  打印("EVENTS=" + 转字符串(长度(s.事件表)))
''')
    assert_success(r)
    out_contains(r, "EVENTS=1")


def test_坏字节尾行_追加事件仍成功():
    r = run_light_source('''
从 持久化 导入 日志路径, 追加事件行, 读入会话宽容
从 文件系统 导入 创建目录
段落 主程序:
  创建目录("probe_root/--proj--/sess1")
  设 f 为 打开文件(日志路径("probe_root", "proj", "sess1"), "wb")
  f.write(b'{"type": "session", "version": {"major": 3, "minor": 0}, "id": "sess1", "createdAt": 1000, "cwd": "proj", "delegationDepth": 0}\\n{"type": "user/message", "seq": 1, "time": 1001, "data": {"text": "hi"}}\\n\\xa5\\xe5\\x85\\xb7"}}}\\n')
  f.close()
  追加事件行("probe_root", "proj", "sess1", {"类型": "user/message", "序号": 2, "时间": 1002, "数据": {"text": "again"}})
  设 s 为 读入会话宽容("probe_root", "proj", "sess1")
  打印("EVENTS=" + 转字符串(长度(s.事件表)))
''')
    assert_success(r)
    out_contains(r, "EVENTS=2")


def test_合法日志_读入行为不变():
    r = run_light_source('''
从 持久化 导入 日志路径, 读入会话宽容
从 文件系统 导入 创建目录
段落 主程序:
  创建目录("probe_root/--proj--/clean")
  设 f 为 打开文件(日志路径("probe_root", "proj", "clean"), "wb")
  f.write(b'{"type": "session", "version": {"major": 3, "minor": 0}, "id": "clean", "createdAt": 1000, "cwd": "proj", "delegationDepth": 0}\\n{"type": "user/message", "seq": 1, "time": 1001, "data": {"text": "hi"}}\\n')
  f.close()
  设 s 为 读入会话宽容("probe_root", "proj", "clean")
  打印("EVENTS=" + 转字符串(长度(s.事件表)))
''')
    assert_success(r)
    out_contains(r, "EVENTS=1")

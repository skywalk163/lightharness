# -*- coding: utf-8 -*-
"""会话持久化JSONL：行格式 / 事件往返 / 生成序列 / 迁移校验。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_是安全序号_零与正数():
    r = run_light_source('''
从 会话持久化JSONL 导入 是安全序号
段落 主程序:
  设 a 为 "NO"
  如果 是安全序号(0): 设 a 为 "YES"
  设 b 为 "NO"
  如果 是安全序号(4294967295): 设 b 为 "YES"
  打印("ZERO=" + a)
  打印("BIG=" + b)
''')
    assert_success(r)
    out_contains(r, "ZERO=YES")
    out_contains(r, "BIG=YES")


def test_是安全序号_负数为假():
    r = run_light_source('''
从 会话持久化JSONL 导入 是安全序号
段落 主程序:
  设 a 为 "NO"
  如果 是安全序号(-1) == 假: 设 a 为 "YES"
  打印("NEG=" + a)
''')
    assert_success(r)
    out_contains(r, "NEG=YES")


def test_是安全序号_非整数为假():
    r = run_light_source('''
从 会话持久化JSONL 导入 是安全序号
段落 主程序:
  设 n1 为 "NO"
  如果 是安全序号(1.5) == 假: 设 n1 为 "YES"
  设 n2 为 "NO"
  如果 是安全序号("5") == 假: 设 n2 为 "YES"
  设 n3 为 "NO"
  如果 是安全序号(真) == 假: 设 n3 为 "YES"
  打印("FLOAT=" + n1)
  打印("STR=" + n2)
  打印("BOOL=" + n3)
''')
    assert_success(r)
    out_contains(r, "FLOAT=YES")
    out_contains(r, "STR=YES")
    out_contains(r, "BOOL=YES")


def test_造头行_解析头行往返():
    r = run_light_source('''
从 会话持久化JSONL 导入 造头行, 解析头行, 行序列化
段落 主程序:
  设 头 为 {}
  头["id"] 为 "sess-abc"
  头["createdAt"] 为 1700000000000
  头["isSeeded"] 为 假
  设 行 为 造头行(头, 0)
  设 文本 为 序列化JSON(行)
  设 果 为 解析头行(文本)
  打印("ID=" + 果["头"]["id"])
  打印("VER=" + 转字符串(果["头"]["version"]))
  打印("SEEDED=" + 转字符串(果["头"]["isSeeded"]))
''')
    assert_success(r)
    out_contains(r, "ID=sess-abc")
    out_contains(r, "VER=3")


def test_造头行_未播种非零继承报错():
    r = run_light_source('''
从 会话持久化JSONL 导入 造头行
段落 主程序:
  设 头 为 {}
  头["id"] 为 "x"
  头["createdAt"] 为 1
  头["isSeeded"] 为 假
  设 行 为 造头行(头, 7)
  打印(转字符串(行))
''')
    assert_failure(r)


def test_解析头行_坏JSON报错():
    r = run_light_source('''
从 会话持久化JSONL 导入 解析头行
段落 主程序:
  设 果 为 解析头行("{not json")
  打印(转字符串(果))
''')
    assert_failure(r)


def test_解析头行_版本不匹配报错():
    r = run_light_source('''
从 会话持久化JSONL 导入 解析头行
段落 主程序:
  设 坏 为 序列化JSON({"type":"session","version":99,"id":"z","createdAt":1,"isSeeded":假,"delegationDepth":0})
  设 果 为 解析头行(坏)
  打印(转字符串(果))
''')
    assert_failure(r)


def test_事件到行_行到事件往返():
    r = run_light_source('''
从 会话持久化JSONL 导入 事件到行字典, 行到事件
段落 主程序:
  设 事件 为 {}
  事件["序号"] 为 5
  事件["种类"] 为 "turn/start"
  事件["数据"] 为 {"a": 1}
  设 行 为 事件到行字典(事件)
  设 回 为 行到事件(行)
  打印("SEQ=" + 转字符串(回["序号"]))
  打印("TYPE=" + 回["种类"])
''')
    assert_success(r)
    out_contains(r, "SEQ=5")
    out_contains(r, "TYPE=turn/start")


def test_行序列化_带尾换行():
    r = run_light_source('''
从 会话持久化JSONL 导入 行序列化
段落 主程序:
  设 文本 为 行序列化({"seq":0,"type":"turn/start","data":{}})
  设 末 为 字符串获取(文本, 字符串长度(文本)-1)
  打印("END=" + 末)
''')
    assert_success(r)
    out_contains(r, "END=\n")


def test_编码段_安全字符原样():
    r = run_light_source('''
从 会话持久化JSONL 导入 编码段
段落 主程序:
  设 s 为 编码段("abc_123-")
  打印("ENC=" + s)
''')
    assert_success(r)
    out_contains(r, "ENC=abc_123-")


def test_编码段_空段报错():
    r = run_light_source('''
从 会话持久化JSONL 导入 编码段
段落 主程序:
  设 s 为 编码段("")
  打印(s)
''')
    assert_failure(r)


def test_编码段_点段转义():
    r = run_light_source('''
从 会话持久化JSONL 导入 编码段
段落 主程序:
  设 a 为 编码段(".")
  设 b 为 编码段("..")
  打印("DOT=" + a)
  打印("DOT2=" + b)
''')
    assert_success(r)
    out_contains(r, "DOT=~002E")
    out_contains(r, "DOT2=~002E~002E")


def test_投影键_折叠分隔并包壳():
    r = run_light_source('''
从 会话持久化JSONL 导入 投影键
段落 主程序:
  设 k 为 投影键("/home/user/proj")
  打印("KEY=" + k)
''')
    assert_success(r)
    out_contains(r, "KEY=--home-user-proj--")


def test_投影目录_空cwd():
    r = run_light_source('''
从 会话持久化JSONL 导入 投影目录
段落 主程序:
  设 a 为 投影目录(空)
  打印("NOWD=" + a)
''')
    assert_success(r)
    out_contains(r, "NOWD=_no-cwd")


def test_排序事件表_按序号升序():
    r = run_light_source('''
从 会话持久化JSONL 导入 排序事件表
段落 主程序:
  设 e1 为 {"序号": 3, "种类": "turn/start", "数据": {}}
  设 e2 为 {"序号": 1, "种类": "turn/start", "数据": {}}
  设 e3 为 {"序号": 2, "种类": "turn/start", "数据": {}}
  设 表 为 排序事件表([e1, e2, e3])
  设 out 为 ""
  遍历 e 之 表:
    设 out 为 out + 转字符串(e["序号"]) + ","
  打印("ORDER=" + out)
''')
    assert_success(r)
    out_contains(r, "ORDER=1,2,3,")


def test_生成行序列_头行加事件行():
    r = run_light_source('''
从 会话持久化JSONL 导入 生成行序列
段落 主程序:
  设 头 为 {}
  头["id"] 为 "g1"
  头["createdAt"] 为 1700000000000
  头["isSeeded"] 为 假
  设 e 为 {"序号": 0, "种类": "turn/start", "数据": {}}
  设 表 为 生成行序列(头, 0, [e])
  打印("COUNT=" + 转字符串(列表长度(表)))
  打印("L0=" + 表[0])
''')
    assert_success(r)
    out_contains(r, "COUNT=2")
    out_contains(r, "session")
    out_contains(r, "g1")


def test_增量行序列_只取起始之后():
    r = run_light_source('''
从 会话持久化JSONL 导入 增量行序列
段落 主程序:
  设 e0 为 {"序号": 0, "种类": "turn/start", "数据": {}}
  设 e1 为 {"序号": 1, "种类": "turn/start", "数据": {}}
  设 e2 为 {"序号": 2, "种类": "turn/start", "数据": {}}
  设 表 为 增量行序列([e2, e0, e1], 1)
  打印("N=" + 转字符串(列表长度(表)))
''')
    assert_success(r)
    out_contains(r, "N=1")


def test_行号映射_映射到seq():
    r = run_light_source('''
从 会话持久化JSONL 导入 行号映射
段落 主程序:
  设 表 为 [
    "{\\"type\\":\\"session\\"}",
    "{\\"seq\\":0,\\"type\\":\\"turn/start\\",\\"data\\":{}}",
    "{\\"seq\\":1,\\"type\\":\\"turn/start\\",\\"data\\":{}}"
  ]
  设 m 为 行号映射(表)
  打印("N=" + 转字符串(列表长度(m)))
  打印("FIRST=" + 转字符串(m[0]["seq"]))
''')
    assert_success(r)
    out_contains(r, "N=2")
    out_contains(r, "FIRST=0")


def test_校验迁移_合法日志通过():
    r = run_light_source('''
从 会话持久化JSONL 导入 生成行序列, 校验迁移
段落 主程序:
  设 头 为 {}
  头["id"] 为 "ok1"
  头["createdAt"] 为 1700000000000
  头["isSeeded"] 为 假
  设 e0 为 {"序号": 0, "种类": "turn/start", "数据": {}}
  设 e1 为 {"序号": 1, "种类": "turn/end", "数据": {"原因": "done"}}
  设 行表 为 生成行序列(头, 0, [e0, e1])
  设 日志 为 连接字符串(行表, "")
  设 果 为 校验迁移(日志)
  打印("PASS=" + 转字符串(果["通过"]))
''')
    assert_success(r)
    out_contains(r, "PASS=真")


def test_校验迁移_序号不连续失败():
    r = run_light_source('''
从 会话持久化JSONL 导入 生成行序列, 校验迁移
段落 主程序:
  设 头 为 {}
  头["id"] 为 "bad1"
  头["createdAt"] 为 1700000000000
  头["isSeeded"] 为 假
  设 e0 为 {"序号": 0, "种类": "turn/start", "数据": {}}
  设 e1 为 {"序号": 5, "种类": "turn/start", "数据": {}}
  设 行表 为 生成行序列(头, 0, [e0, e1])
  设 日志 为 连接字符串(行表, "")
  设 果 为 校验迁移(日志)
  打印("PASS=" + 转字符串(果["通过"]))
  打印("ERRN=" + 转字符串(列表长度(果["错误表"])))
''')
    assert_success(r)
    out_contains(r, "PASS=假")
    out_contains(r, "ERRN=1")


def test_校验迁移_未知类型失败():
    r = run_light_source('''
从 会话持久化JSONL 导入 生成行序列, 校验迁移
段落 主程序:
  设 头 为 {}
  头["id"] 为 "bad2"
  头["createdAt"] 为 1700000000000
  头["isSeeded"] 为 假
  设 e0 为 {"序号": 0, "种类": "turn/start", "数据": {}}
  设 e1 为 {"序号": 1, "种类": "nope/unknown", "数据": {}}
  设 行表 为 生成行序列(头, 0, [e0, e1])
  设 日志 为 连接字符串(行表, "")
  设 果 为 校验迁移(日志)
  打印("PASS=" + 转字符串(果["通过"]))
''')
    assert_success(r)
    out_contains(r, "PASS=假")

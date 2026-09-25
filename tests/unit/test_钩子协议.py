# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_判通配_三态():
    r = run_light_source('''
从 钩子协议 导入 判通配
段落 主程序:
  打印("A=" + 转字符串(判通配(空)))
  打印("B=" + 转字符串(判通配("")))
  打印("C=" + 转字符串(判通配("*")))
  打印("D=" + 转字符串(判通配("Bash")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")
    out_contains(r, "C=真")
    out_contains(r, "D=假")


def test_判字面式():
    r = run_light_source('''
从 钩子协议 导入 判字面式
段落 主程序:
  打印("A=" + 转字符串(判字面式("Bash|Edit")))
  打印("B=" + 转字符串(判字面式("a b")))
  打印("C=" + 转字符串(判字面式(123)))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")
    out_contains(r, "C=假")


def test_甄别命中_通配恒真():
    r = run_light_source('''
从 钩子协议 导入 甄别命中, 方言科德
段落 主程序:
  打印("A=" + 转字符串(甄别命中("*", "任意工具", 方言科德)))
  打印("B=" + 转字符串(甄别命中(空, "任意工具", 方言科德)))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")


def test_甄别命中_克劳德字面竖线():
    r = run_light_source('''
从 钩子协议 导入 甄别命中, 方言克劳德
段落 主程序:
  打印("A=" + 转字符串(甄别命中("Bash|Edit", "Bash", 方言克劳德)))
  打印("B=" + 转字符串(甄别命中("Bash|Edit", "Read", 方言克劳德)))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")


def test_甄别命中_正则与非法():
    r = run_light_source('''
从 钩子协议 导入 甄别命中, 方言科德
段落 主程序:
  打印("A=" + 转字符串(甄别命中("^git ", "git status", 方言科德)))
  打印("B=" + 转字符串(甄别命中("^git ", "ls", 方言科德)))
  打印("C=" + 转字符串(甄别命中("([unclosed", "x", 方言科德)))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")
    out_contains(r, "C=假")


def test_读字符串_缺省与类型():
    r = run_light_source('''
从 钩子协议 导入 读字符串
段落 主程序:
  设 t 为 {"a":"hello", "b":123}
  打印("A=" + 读字符串(t, "a"))
  如果 读字符串(t, "missing") == 空:
    打印("B=空")
  否则:
    打印("B=非空")
  如果 读字符串(t, "b") == 空:
    打印("C=空")
  否则:
    打印("C=非空")
''')
    assert_success(r)
    out_contains(r, "A=hello")
    out_contains(r, "B=空")
    out_contains(r, "C=空")


def test_读布尔_严格bool():
    r = run_light_source('''
从 钩子协议 导入 读布尔
段落 主程序:
  设 t 为 {"a":真, "b":1}
  打印("A=" + 转字符串(读布尔(t, "a")))
  如果 读布尔(t, "b") == 空:
    打印("B=空")
  否则:
    打印("B=非空")
  如果 读布尔(t, "missing") == 空:
    打印("C=空")
  否则:
    打印("C=非空")
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=空")
    out_contains(r, "C=空")


def test_读对象_仅字典():
    r = run_light_source('''
从 钩子协议 导入 读对象
段落 主程序:
  设 d 为 {"x":1}
  打印("A=" + 转字符串(读对象(d) == d))
  如果 读对象([1,2]) == 空:
    打印("B=空")
  否则:
    打印("B=非空")
  如果 读对象(空) == 空:
    打印("C=空")
  否则:
    打印("C=非空")
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=空")
    out_contains(r, "C=空")


def test_顶层裁定与许可裁定值():
    r = run_light_source('''
从 钩子协议 导入 顶层裁定, 许可裁定值
段落 主程序:
  打印("A=" + 顶层裁定("approve"))
  打印("B=" + 顶层裁定("block"))
  如果 顶层裁定("deny") == 空:
    打印("C=空")
  否则:
    打印("C=非空")
  打印("D=" + 许可裁定值("allow"))
  打印("E=" + 许可裁定值("ask"))
  如果 许可裁定值("maybe") == 空:
    打印("F=空")
  否则:
    打印("F=非空")
''')
    assert_success(r)
    out_contains(r, "A=approve")
    out_contains(r, "B=block")
    out_contains(r, "C=空")
    out_contains(r, "D=allow")
    out_contains(r, "E=ask")
    out_contains(r, "F=空")


def test_解析钩子产出_阻断退出码2():
    r = run_light_source('''
从 钩子协议 导入 解析钩子产出
段落 主程序:
  设 o 为 解析钩子产出(2, "", "禁止操作", 空)
  打印("裁定=" + o["裁定"])
  打印("缘由=" + o["缘由"])
''')
    assert_success(r)
    out_contains(r, "裁定=block")
    out_contains(r, "缘由=禁止操作")


def test_解析钩子产出_JSON裁定():
    r = run_light_source('''
从 钩子协议 导入 解析钩子产出
从 JSON 导入 序列化JSON
段落 主程序:
  设 stdout 为 序列化JSON({"decision":"block", "reason":"不安全"})
  设 o 为 解析钩子产出(0, stdout, "", 空)
  打印("裁定=" + o["裁定"])
  打印("缘由=" + o["缘由"])
''')
    assert_success(r)
    out_contains(r, "裁定=block")
    out_contains(r, "缘由=不安全")


def test_解析钩子产出_普通stdout无裁定():
    r = run_light_source('''
从 钩子协议 导入 解析钩子产出
段落 主程序:
  设 o 为 解析钩子产出(0, "普通输出", "", 空)
  设 有裁定 为 字典包含键(o, "裁定")
  打印("有=" + 转字符串(有裁定))
''')
    assert_success(r)
    out_contains(r, "有=假")


def test_裁定等级与等级裁定():
    r = run_light_source('''
从 钩子协议 导入 裁定等级, 等级裁定
段落 主程序:
  打印("A=" + 转字符串(裁定等级("deny")))
  打印("B=" + 转字符串(裁定等级("block")))
  打印("C=" + 转字符串(裁定等级("ask")))
  打印("D=" + 转字符串(裁定等级("allow")))
  打印("E=" + 等级裁定(3))
  打印("F=" + 等级裁定(0))
''')
    assert_success(r)
    out_contains(r, "A=3")
    out_contains(r, "B=3")
    out_contains(r, "C=2")
    out_contains(r, "D=1")
    out_contains(r, "E=deny")
    out_contains(r, "F=none")


def test_合并钩子产出_deny胜出():
    r = run_light_source('''
从 钩子协议 导入 合并钩子产出
段落 主程序:
  设 a 为 {"裁定":"allow", "缘由":"ok"}
  设 b 为 {"裁定":"deny", "缘由":"bad"}
  设 m 为 合并钩子产出([a, b])
  打印("裁定=" + m["裁定"])
  打印("缘由=" + m["缘由"])
''')
    assert_success(r)
    out_contains(r, "裁定=deny")
    out_contains(r, "缘由=bad")


def test_合并钩子产出_空表为none():
    r = run_light_source('''
从 钩子协议 导入 合并钩子产出
段落 主程序:
  设 m 为 合并钩子产出([])
  打印("裁定=" + m["裁定"])
''')
    assert_success(r)
    out_contains(r, "裁定=none")


def test_插件根标记与替换指令():
    r = run_light_source('''
从 钩子协议 导入 插件根标记, 替换指令
段落 主程序:
  打印("标记=" + 插件根标记())
  设 t 为 替换指令("run " + 插件根标记(), "/myplugin", "")
  打印("替换=" + t)
''')
    assert_success(r)
    out_contains(r, "标记=${CLAUDE_PLUGIN_ROOT}")
    out_contains(r, "替换=run /myplugin")


def test_概要化标准错误():
    r = run_light_source('''
从 钩子协议 导入 概要化标准错误
段落 主程序:
  如果 概要化标准错误("   ", 100) == 空:
    打印("空=空")
  否则:
    打印("空=非空")
  设 long 为 "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  设 s 为 概要化标准错误(long, 10)
  打印("截=" + 转字符串(字符串长度(s) > 10))
''')
    assert_success(r)
    out_contains(r, "空=空")
    out_contains(r, "截=真")


def test_运行时长毫秒与落码归一():
    r = run_light_source('''
从 钩子协议 导入 运行时长毫秒, 落码归一, 默认钩子时长
段落 主程序:
  打印("A=" + 转字符串(运行时长毫秒(30, 默认钩子时长)))
  打印("B=" + 转字符串(运行时长毫秒(空, 默认钩子时长)))
  打印("C=" + 转字符串(落码归一(5)))
  如果 落码归一(空) == 空:
    打印("D=空")
  否则:
    打印("D=非空")
''')
    assert_success(r)
    out_contains(r, "A=30000")
    out_contains(r, "B=600000")
    out_contains(r, "C=5")
    out_contains(r, "D=空")

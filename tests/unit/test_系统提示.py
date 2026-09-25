# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_校验变量名_合法():
    r = run_light_source('''
从 系统提示 导入 校验变量名
段落 主程序:
  打印("A=" + 转字符串(校验变量名("abc")))
  打印("B=" + 转字符串(校验变量名("a1_b2")))
  打印("C=" + 转字符串(校验变量名("x")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")
    out_contains(r, "C=真")


def test_校验变量名_非法():
    r = run_light_source('''
从 系统提示 导入 校验变量名
段落 主程序:
  打印("A=" + 转字符串(校验变量名("")))
  打印("B=" + 转字符串(校验变量名("Abc")))
  打印("C=" + 转字符串(校验变量名("1abc")))
  打印("D=" + 转字符串(校验变量名("_ab")))
  打印("E=" + 转字符串(校验变量名(123)))
''')
    assert_success(r)
    out_contains(r, "A=假")
    out_contains(r, "B=假")
    out_contains(r, "C=假")
    out_contains(r, "D=假")
    out_contains(r, "E=假")


def test_扫描变量引用():
    r = run_light_source('''
从 系统提示 导入 扫描变量引用
段落 主程序:
  设 表 为 扫描变量引用("hi {{name}} bye {{greet}}")
  打印("数=" + 转字符串(长度(表)))
  打印("一=" + 表[0]["名字"])
  打印("二=" + 表[1]["名字"])
''')
    assert_success(r)
    out_contains(r, "数=2")
    out_contains(r, "一=name")
    out_contains(r, "二=greet")


def test_扫描变量引用_残缺不计():
    r = run_light_source('''
从 系统提示 导入 扫描变量引用
段落 主程序:
  设 表 为 扫描变量引用("open {{ but no close")
  打印("数=" + 转字符串(长度(表)))
''')
    assert_success(r)
    out_contains(r, "数=0")


def test_比较工具名字():
    r = run_light_source('''
从 系统提示 导入 比较工具名字
段落 主程序:
  打印("A=" + 转字符串(比较工具名字("alpha", "beta")))
  打印("B=" + 转字符串(比较工具名字("beta", "alpha")))
  打印("C=" + 转字符串(比较工具名字("same", "same")))
''')
    assert_success(r)
    out_contains(r, "A=-1")
    out_contains(r, "B=1")
    out_contains(r, "C=0")


def test_校验工具排序_空与合法():
    r = run_light_source('''
从 系统提示 导入 校验工具排序, 工具排序未列出标记
段落 主程序:
  如果 校验工具排序(空) == 空:
    打印("空=空")
  否则:
    打印("空=非空")
  设 ok 为 校验工具排序(["b", "a", 工具排序未列出标记])
  打印("长=" + 转字符串(长度(ok)))
''')
    assert_success(r)
    out_contains(r, "空=空")
    out_contains(r, "长=3")


def test_校验工具排序_缺rest报错():
    r = run_light_source('''
从 系统提示 导入 校验工具排序
段落 主程序:
  设 x 为 校验工具排序(["a", "b"])
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "MISSING_REST")


def test_校验工具排序_重复报错():
    r = run_light_source('''
从 系统提示 导入 校验工具排序, 工具排序未列出标记
段落 主程序:
  设 x 为 校验工具排序(["a", "a", 工具排序未列出标记])
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "DUPLICATE_TOOL_ORDER")


def test_排序工具_无配置按名字序():
    r = run_light_source('''
从 系统提示 导入 排序工具
段落 主程序:
  设 表 为 [{"name":"beta"}, {"name":"alpha"}, {"name":"mid"}]
  设 出 为 排序工具(表)
  打印("一=" + 出[0]["name"])
  打印("二=" + 出[1]["name"])
''')
    assert_success(r)
    out_contains(r, "一=alpha")
    out_contains(r, "二=beta")


def test_排序工具_按配置顺序():
    r = run_light_source('''
从 系统提示 导入 排序工具, 工具排序未列出标记
段落 主程序:
  设 表 为 [{"name":"alpha"}, {"name":"beta"}, {"name":"gamma"}]
  设 序 为 ["beta", 工具排序未列出标记, "alpha"]
  设 出 为 排序工具(表, 序)
  打印("一=" + 出[0]["name"])
  打印("二=" + 出[1]["name"])
  打印("三=" + 出[2]["name"])
''')
    assert_success(r)
    out_contains(r, "一=beta")
    out_contains(r, "二=gamma")
    out_contains(r, "三=alpha")


def test_排序工具_保留名报错():
    r = run_light_source('''
从 系统提示 导入 排序工具, 工具排序未列出标记
段落 主程序:
  设 表 为 [{"name":工具排序未列出标记}]
  设 x 为 排序工具(表)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "RESERVED_TOOL_NAME")


def test_插值_变量替换():
    r = run_light_source('''
从 系统提示 导入 插值
段落 主程序:
  设 out 为 插值("hi {{name}}, age {{age}}", {"name":"bob", "age":30})
  打印("OUT=" + out)
''')
    assert_success(r)
    out_contains(r, "OUT=hi bob, age 30")


def test_插值_未知变量保留原样():
    r = run_light_source('''
从 系统提示 导入 插值
段落 主程序:
  设 out 为 插值("hi {{nope}}", {})
  打印("OUT=" + out)
''')
    assert_success(r)
    out_contains(r, "OUT=hi {{nope}}")


def test_插值_非法变量名报错():
    r = run_light_source('''
从 系统提示 导入 插值
段落 主程序:
  设 out 为 插值("{{BadName}}", {})
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_VARIABLE_NAME")


def test_插值_花括号畸形报错():
    r = run_light_source('''
从 系统提示 导入 插值
段落 主程序:
  设 out 为 插值("{{a{b}}}", {})
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "MALFORMED_VARIABLE_REF")


def test_节顺序常量表_含键():
    r = run_light_source('''
从 系统提示 导入 节顺序常量表
段落 主程序:
  打印("H=" + 转字符串(节顺序常量表["HARNESS_IDENTITY"]))
  打印("S=" + 转字符串(节顺序常量表["DEPLOYMENT_PERSONA_SUFFIX"]))
''')
    assert_success(r)
    out_contains(r, "H=-1000")
    out_contains(r, "S=10200")


def test_注册节_重复报错():
    r = run_light_source('''
从 系统提示 导入 建系统提示注册表, 注册节
段落 主程序:
  设 reg 为 建系统提示注册表()
  注册节(reg, "sec1", 1, "文本一")
  注册节(reg, "sec1", 2, "文本二")
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "DUPLICATE_SECTION")


def test_注册变量_非法名报错():
    r = run_light_source('''
从 系统提示 导入 建系统提示注册表, 注册变量
段落 主程序:
  设 reg 为 建系统提示注册表()
  注册变量(reg, "BadName", "v")
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_VARIABLE_NAME")


def test_组装系统提示_节排序():
    r = run_light_source('''
从 系统提示 导入 建系统提示注册表, 注册节, 注册变量, 组装系统提示, 渲染提示
段落 主程序:
  设 reg 为 建系统提示注册表()
  注册节(reg, "b", 200, "第二节")
  注册节(reg, "a", 100, "第一节")
  注册变量(reg, "who", "世界")
  注册节(reg, "c", 300, "你好{{who}}")
  设 装配 为 组装系统提示(reg)
  设 出 为 渲染提示(装配)
  打印("文本=" + 出)
''')
    assert_success(r)
    out_contains(r, "第一节\n\n第二节\n\n你好世界")


def test_处理完整节_多个报错():
    r = run_light_source('''
从 系统提示 导入 处理完整节
段落 主程序:
  设 装配 为 {"节列表":[
    {"名字":"x", "顺序":1, "文本":"t", "完整":真},
    {"名字":"y", "顺序":2, "文本":"u", "完整":真}
  ]}
  设 x 为 处理完整节(装配)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "MULTIPLE_COMPLETE_SECTIONS")

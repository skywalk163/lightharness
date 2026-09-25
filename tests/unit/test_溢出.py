# -*- coding: utf-8 -*-
from test_support import run_light_source, assert_success, assert_failure, out_contains, out_not_contains


def test_最大_取较大值():
    r = run_light_source('''
从 溢出 导入 最大
段落 主程序:
  打印("R=" + 转字符串(最大(3, 7)))
  打印("S=" + 转字符串(最大(10, -2)))
''')
    assert_success(r)
    out_contains(r, "R=7")
    out_contains(r, "S=10")


def test_最小_取较小值():
    r = run_light_source('''
从 溢出 导入 最小
段落 主程序:
  打印("R=" + 转字符串(最小(3, 7)))
  打印("S=" + 转字符串(最小(-5, 2)))
''')
    assert_success(r)
    out_contains(r, "R=3")
    out_contains(r, "S=-5")


def test_字符宽度_ASCII为1():
    r = run_light_source('''
从 溢出 导入 字符宽度
段落 主程序:
  打印("A=" + 转字符串(字符宽度("a")))
  打印("Z=" + 转字符串(字符宽度("Z")))
''')
    assert_success(r)
    out_contains(r, "A=1")
    out_contains(r, "Z=1")


def test_字符宽度_两字节字符为2():
    # U+00E9 é = 233 < 2048 => 2 bytes
    r = run_light_source('''
从 溢出 导入 字符宽度
段落 主程序:
  打印("E=" + 转字符串(字符宽度("é")))
''')
    assert_success(r)
    out_contains(r, "E=2")


def test_字符宽度_CJK为3():
    r = run_light_source('''
从 溢出 导入 字符宽度
段落 主程序:
  打印("C=" + 转字符串(字符宽度("中")))
''')
    assert_success(r)
    out_contains(r, "C=3")


def test_字符宽度_emoji为4():
    # U+1F600 => 4 bytes
    r = run_light_source('''
从 溢出 导入 字符宽度
段落 主程序:
  打印("M=" + 转字符串(字符宽度("😀")))
''')
    assert_success(r)
    out_contains(r, "M=4")


def test_字节长度_混合串():
    r = run_light_source('''
从 溢出 导入 字节长度
段落 主程序:
  打印("A=" + 转字符串(字节长度("abc")))
  打印("B=" + 转字符串(字节长度("ab中")))
''')
    assert_success(r)
    out_contains(r, "A=3")
    out_contains(r, "B=5")


def test_取前N字节_不劈开多字节字符():
    # "ab中" = 1+1+3=5 bytes; budget 3 => after a(1)b(1)=2, next char 中=3 would exceed => "ab"
    r = run_light_source('''
从 溢出 导入 取前N字节
段落 主程序:
  打印("P=[" + 取前N字节("ab中", 3) + "]")
  打印("Q=[" + 取前N字节("ab中", 5) + "]")
''')
    assert_success(r)
    out_contains(r, "P=[ab]")
    out_contains(r, "Q=[ab中]")


def test_取后N字节_后缀不劈开字符():
    r = run_light_source('''
从 溢出 导入 取后N字节
段落 主程序:
  打印("S=[" + 取后N字节("ab中", 3) + "]")
  打印("Z=[" + 取后N字节("abc", 0) + "]")
''')
    assert_success(r)
    # "ab中" suffix budget 3 => exactly "中"
    out_contains(r, "S=[中]")
    out_contains(r, "Z=[]")


def test_扁平化纯文本_合并文本块():
    r = run_light_source('''
从 溢出 导入 扁平化纯文本
段落 主程序:
  设 块 为 [{"类型":"text", "文本":"hello"}, {"类型":"text", "文本":" world"}]
  设 结果 为 扁平化纯文本(块)
  打印("OUT=[" + 结果 + "]")
''')
    assert_success(r)
    out_contains(r, "OUT=[hello world]")


def test_扁平化纯文本_遇非文本块返回空():
    r = run_light_source('''
从 溢出 导入 扁平化纯文本
段落 主程序:
  设 块 为 [{"类型":"text", "文本":"a"}, {"类型":"image", "文本":"x"}]
  设 结果 为 扁平化纯文本(块)
  如果 结果 == 空:
    打印("GOT=空")
  否则:
    打印("GOT=" + 结果)
''')
    assert_success(r)
    out_contains(r, "GOT=空")


def test_校验上限_合法值通过():
    r = run_light_source('''
从 溢出 导入 校验上限
段落 主程序:
  打印("Z=" + 转字符串(校验上限(0)))
  打印("N=" + 转字符串(校验上限(1024)))
''')
    assert_success(r)
    out_contains(r, "Z=真")
    out_contains(r, "N=真")


def test_校验上限_负数报错():
    r = run_light_source('''
从 溢出 导入 校验上限
段落 主程序:
  校验上限(-1)
''')
    assert_failure(r)


def test_校验上限_非整数报错():
    r = run_light_source('''
从 溢出 导入 校验上限
段落 主程序:
  校验上限(1.5)
''')
    assert_failure(r)


def test_构造预览_零预算全省略():
    r = run_light_source('''
从 溢出 导入 构造预览
段落 主程序:
  设 结果 为 构造预览("abc", 0)
  打印("T=[" + 结果["文本"] + "]")
  打印("K=" + 结果["省略"]["种类"])
  打印("N=" + 转字符串(结果["省略"]["计数"]))
''')
    assert_success(r)
    out_contains(r, "T=[]")
    out_contains(r, "K=精确")
    out_contains(r, "N=3")


def test_构造预览_充足预算原样返回():
    r = run_light_source('''
从 溢出 导入 构造预览
段落 主程序:
  设 结果 为 构造预览("abc", 100)
  打印("T=[" + 结果["文本"] + "]")
  打印("K=" + 结果["省略"]["种类"])
''')
    assert_success(r)
    out_contains(r, "T=[abc]")
    out_contains(r, "K=无")


def test_构造预览_部分预算头尾拼接():
    # "abcdef"=6 bytes, budget 4 => head 2, tail 2 => "abef", omitted 2
    r = run_light_source('''
从 溢出 导入 构造预览
段落 主程序:
  设 结果 为 构造预览("abcdef", 4)
  打印("T=[" + 结果["文本"] + "]")
  打印("K=" + 结果["省略"]["种类"])
  打印("N=" + 转字符串(结果["省略"]["计数"]))
''')
    assert_success(r)
    out_contains(r, "T=[abef]")
    out_contains(r, "K=精确")
    out_contains(r, "N=2")


def test_描述省略_无省略返回空串():
    r = run_light_source('''
从 溢出 导入 描述省略
段落 主程序:
  设 s 为 描述省略({"种类":"无"}, "bytes")
  打印("OUT=[" + s + "]")
''')
    assert_success(r)
    out_contains(r, "OUT=[]")


def test_描述省略_精确计数句子():
    r = run_light_source('''
从 溢出 导入 描述省略
段落 主程序:
  设 s 为 描述省略({"种类":"精确", "计数":5}, "bytes")
  打印("OUT=[" + s + "]")
''')
    assert_success(r)
    out_contains(r, "OUT=[Omitted 5 bytes.]")


def test_描述省略_未知种类句子():
    r = run_light_source('''
从 溢出 导入 描述省略
段落 主程序:
  设 s 为 描述省略({"种类":"unknown"}, "bytes")
  打印("OUT=[" + s + "]")
''')
    assert_success(r)
    out_contains(r, "OUT=[More bytes were omitted.]")


def test_溢出提示_拼装定位符():
    r = run_light_source('''
从 溢出 导入 溢出提示
段落 主程序:
  设 引 为 {"定位符":"spill://s1/part1", "检索提示":"Read the full file to see all content."}
  设 s 为 溢出提示({"种类":"精确", "计数":5}, 引)
  打印("OUT=" + s)
''')
    assert_success(r)
    out_contains(r, "Omitted 5 bytes.")
    out_contains(r, "spill://s1/part1")
    out_contains(r, "Read the full file to see all content.")


def test_模拟保存文本_返回引用三元组():
    r = run_light_source('''
从 溢出 导入 模拟保存文本
段落 主程序:
  设 输入 为 {"拥有者":{"会话id":"s1"}, "建议名":"part1", "内容":"abc"}
  设 引 为 模拟保存文本(输入)
  打印("LOC=" + 引["定位符"])
  打印("LEN=" + 转字符串(引["字节长度"]))
  打印("HINT=" + 引["检索提示"])
''')
    assert_success(r)
    out_contains(r, "LOC=spill://s1/part1")
    out_contains(r, "LEN=3")
    out_contains(r, "HINT=Read the full file to see all content.")


def test_溢出替换_充足预算返回预览加提示():
    r = run_light_source('''
从 溢出 导入 溢出替换
段落 主程序:
  设 引 为 {"定位符":"spill://s1/p", "检索提示":"Read the full file to see all content."}
  设 结果 为 溢出替换("abc", 3, 200, 引)
  如果 结果 == 空:
    打印("GOT=空")
  否则:
    打印("GOT=" + 结果)
''')
    assert_success(r)
    out_not_contains(r, "GOT=空")
    out_contains(r, "spill://s1/p")


def test_溢出替换_极小预算返回空():
    # cap=1: notice alone far exceeds => 返回 空 (保留内联)
    r = run_light_source('''
从 溢出 导入 溢出替换
段落 主程序:
  设 引 为 {"定位符":"spill://s1/p", "检索提示":"Read the full file to see all content."}
  设 结果 为 溢出替换("abc", 3, 1, 引)
  如果 结果 == 空:
    打印("GOT=空")
  否则:
    打印("GOT=" + 结果)
''')
    assert_success(r)
    out_contains(r, "GOT=空")

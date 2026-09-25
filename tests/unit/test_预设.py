# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_分类行标识符():
    r = run_light_source('''
从 预设 导入 分类行标识符
段落 主程序:
  打印("A=" + 分类行标识符("cordis:x")["种类"])
  打印("B=" + 分类行标识符("./local")["种类"])
  打印("C=" + 分类行标识符("/abs/path")["种类"])
  打印("D=" + 分类行标识符("@scope/pkg")["种类"])
  打印("E=" + 分类行标识符("plainpkg")["种类"])
''')
    assert_success(r)
    out_contains(r, "A=builtin")
    out_contains(r, "B=preset")
    out_contains(r, "C=file")
    out_contains(r, "D=package")
    out_contains(r, "E=package")


def test_是绝对():
    r = run_light_source('''
从 预设 导入 是绝对
段落 主程序:
  打印("A=" + 转字符串(是绝对("/a/b")))
  打印("B=" + 转字符串(是绝对("C:/a/b")))
  打印("C=" + 转字符串(是绝对("rel/path")))
  打印("D=" + 转字符串(是绝对("")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")
    out_contains(r, "C=假")
    out_contains(r, "D=假")


def test_前缀是():
    r = run_light_source('''
从 预设 导入 前缀是
段落 主程序:
  打印("A=" + 转字符串(前缀是("/home/u/p", "/home/u")))
  打印("B=" + 转字符串(前缀是("/other/p", "/home/u")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")


def test_标识合法():
    r = run_light_source('''
从 预设 导入 标识合法
段落 主程序:
  打印("A=" + 转字符串(标识合法("my-preset")))
  打印("B=" + 转字符串(标识合法("v2")))
  打印("C=" + 转字符串(标识合法("")))
  打印("D=" + 转字符串(标识合法("-bad")))
  打印("E=" + 转字符串(标识合法("UPPER")))
  打印("F=" + 转字符串(标识合法("has space")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")
    out_contains(r, "C=假")
    out_contains(r, "D=假")
    out_contains(r, "E=假")
    out_contains(r, "F=假")


def test_可用文本():
    r = run_light_source('''
从 预设 导入 可用文本
段落 主程序:
  打印("A=" + 可用文本([]))
  打印("B=" + 可用文本(["standard", "ptc"]))
''')
    assert_success(r)
    out_contains(r, "A=none")
    out_contains(r, "B=standard")


def test_文本清洗():
    r = run_light_source('''
从 预设 导入 文本
段落 主程序:
  打印("A=" + 文本("  hi  "))
  如果 文本(123) == 空:
    打印("B=空")
  否则:
    打印("B=非空")
  如果 文本("   ") == 空:
    打印("C=空")
  否则:
    打印("C=非空")
''')
    assert_success(r)
    out_contains(r, "A=hi")
    out_contains(r, "B=空")
    out_contains(r, "C=空")


def test_提取显示元数据():
    r = run_light_source('''
从 预设 导入 提取显示元数据
段落 主程序:
  设 m 为 提取显示元数据({"name":" 我的预设 ", "description":"desc", "order":5, "junk":9})
  打印("名=" + m["name"])
  打印("述=" + m["description"])
  打印("序=" + 转字符串(m["order"]))
''')
    assert_success(r)
    out_contains(r, "名=我的预设")
    out_contains(r, "述=desc")
    out_contains(r, "序=5")


def test_行启用():
    r = run_light_source('''
从 预设 导入 行启用
段落 主程序:
  打印("A=" + 转字符串(行启用({"name":"x"})))
  打印("B=" + 转字符串(行启用({"name":"y", "disabled":真})))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")


def test_条目列表问题_合法列表():
    r = run_light_source('''
从 预设 导入 条目列表问题
段落 主程序:
  设 表 为 [{"name":"a"}, {"name":"b"}]
  设 p 为 条目列表问题(表, "")
  如果 p == 空:
    打印("问题=空")
  否则:
    打印("问题=" + p)
''')
    assert_success(r)
    out_contains(r, "问题=空")


def test_条目列表问题_非列表():
    r = run_light_source('''
从 预设 导入 条目列表问题
段落 主程序:
  设 p 为 条目列表问题({}, "")
  打印("问题=" + p)
''')
    assert_success(r)
    out_contains(r, "top-level list of plugin rows")


def test_条目列表问题_缺name():
    r = run_light_source('''
从 预设 导入 条目列表问题
段落 主程序:
  设 p 为 条目列表问题([{"group":真, "config":[]}], "")
  打印("问题=" + p)
''')
    assert_success(r)
    out_contains(r, "names no plugin")


def test_应前_按order再id():
    r = run_light_source('''
从 预设 导入 应前
段落 主程序:
  设 a 为 {"id":"a", "order":2}
  设 b 为 {"id":"b", "order":1}
  打印("A=" + 转字符串(应前(a, b)))
  设 c 为 {"id":"a"}
  设 d 为 {"id":"b"}
  打印("B=" + 转字符串(应前(c, d)))
''')
    assert_success(r)
    out_contains(r, "A=假")
    out_contains(r, "B=真")


def test_扫描根排序():
    r = run_light_source('''
从 预设 导入 扫描根排序
从 JSON 导入 序列化JSON
段落 主程序:
  设 表 为 [{"id":"z", "order":2}, {"id":"a", "order":1}, {"id":"m", "order":1}]
  设 排 为 扫描根排序(表)
  设 序 为 []
  遍历 项 之 排: 列表追加(序, 项["id"])
  打印("序=" + 序列化JSON(序))
''')
    assert_success(r)
    out_contains(r, '序=["a", "m", "z"]')


def test_发现预设_去重():
    r = run_light_source('''
从 预设 导入 发现预设
从 JSON 导入 序列化JSON
段落 主程序:
  设 根表 为 [
    {"预设列表":[{"id":"a","name":"A"}, {"id":"b","name":"B"}]},
    {"预设列表":[{"id":"a","name":"A2"}, {"id":"c","name":"C"}]}
  ]
  设 找 为 发现预设(根表)
  设 序 为 []
  遍历 项 之 找: 列表追加(序, 项["id"])
  打印("序=" + 序列化JSON(序))
''')
    assert_success(r)
    out_contains(r, '序=["a", "b", "c"]')


def test_在纤维内_沿父链():
    r = run_light_source('''
从 预设 导入 在纤维内
段落 主程序:
  设 表 为 {"b":{"父标识":"a"}, "a":{"父标识":"root"}}
  打印("A=" + 转字符串(在纤维内(表, "b", "root")))
  打印("B=" + 转字符串(在纤维内(表, "b", "other")))
  打印("C=" + 转字符串(在纤维内(表, "root", "root")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")
    out_contains(r, "C=真")


def test_排序名():
    r = run_light_source('''
从 预设 导入 排序名
从 JSON 导入 序列化JSON
段落 主程序:
  设 出 为 排序名(["b", "a", "c"])
  打印("出=" + 序列化JSON(出))
''')
    assert_success(r)
    out_contains(r, '出=["a", "b", "c"]')


def test_可写根_有user():
    r = run_light_source('''
从 预设 导入 可写根
段落 主程序:
  设 根表 为 [{"trust":"system", "path":"/sys"}, {"trust":"user", "path":"/home/u"}]
  打印("根=" + 可写根(根表))
''')
    assert_success(r)
    out_contains(r, "根=/home/u")


def test_可写根_无user报错():
    r = run_light_source('''
从 预设 导入 可写根
段落 主程序:
  设 根表 为 [{"trust":"system", "path":"/sys"}]
  设 x 为 可写根(根表)
  打印("不应到达")
''')
    assert_failure(r)


def test_可删判定_合法():
    r = run_light_source('''
从 预设 导入 可删判定
段落 主程序:
  设 p 为 {"trust":"user", "id":"my", "path":"/home/u/my"}
  打印("可删=" + 转字符串(可删判定(p, "/home/u")))
''')
    assert_success(r)
    out_contains(r, "可删=真")


def test_可删判定_内置不可删():
    r = run_light_source('''
从 预设 导入 可删判定
段落 主程序:
  设 p 为 {"trust":"system", "id":"std", "path":"/sys/std"}
  设 x 为 可删判定(p, "/home/u")
  打印("不应到达")
''')
    assert_failure(r)


def test_可复制元数据():
    r = run_light_source('''
从 预设 导入 可复制元数据
段落 主程序:
  设 r 为 可复制元数据({"description":"保留描述"}, "新名")
  打印("名=" + r["name"])
  打印("述=" + r["description"])
''')
    assert_success(r)
    out_contains(r, "名=新名")
    out_contains(r, "述=保留描述")

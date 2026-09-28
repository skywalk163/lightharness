# -*- coding: utf-8 -*-
"""工具_写文件：模式/定义/写处理IO + 绳侧块差异/参数/信封。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_写文件模式_含必选字段():
    r = run_light_source('''
从 工具_写文件 导入 写文件模式
段落 主程序:
  设 m 为 写文件模式()
  打印("TYPE=" + m["type"])
''')
    assert_success(r)
    out_contains(r, "TYPE=object")


def test_造写文件工具定义_名称():
    r = run_light_source('''
从 工具_写文件 导入 造写文件工具定义
段落 主程序:
  设 d 为 造写文件工具定义()
  打印("N=" + d["name"])
''')
    assert_success(r)
    out_contains(r, "N=写文件")


def test_写文件处理_新建文件():
    r = run_light_source('''
从 工具_写文件 导入 写文件处理
段落 主程序:
  设 res 为 写文件处理({"路径": "sub/dir/a.txt", "内容": "hello"})
  打印("B=" + 转字符串(res["写入字节数"]))
  设 c 为 "NO"
  如果 res["覆盖"]: 设 c 为 "YES"
  打印("OV=" + c)
''')
    assert_success(r)
    out_contains(r, "B=5")
    out_contains(r, "OV=NO")


def test_写文件处理_第二次覆盖():
    r = run_light_source('''
从 工具_写文件 导入 写文件处理
段落 主程序:
  写文件处理({"路径": "a.txt", "内容": "one"})
  设 res 为 写文件处理({"路径": "a.txt", "内容": "two"})
  设 c 为 "NO"
  如果 res["覆盖"]: 设 c 为 "YES"
  打印("OV=" + c)
''')
    assert_success(r)
    out_contains(r, "OV=YES")


def test_写文件处理_越界路径拒绝():
    r = run_light_source('''
从 工具_写文件 导入 写文件处理
段落 主程序:
  设 res 为 写文件处理({"路径": "../escape.txt", "内容": "x"})
  打印(转字符串(res))
''')
    assert_failure(r)


def test_绳计算块差异_替换中间行():
    r = run_light_source('''
从 工具_写文件 导入 绳计算块差异
段落 主程序:
  设 块 为 绳计算块差异("f", "a\\nb\\nc", "a\\nx\\nc")
  打印("N=" + 转字符串(列表长度(块)))
  打印("OLD=" + 块[0]["旧文本"])
  打印("NEW=" + 块[0]["新文本"])
''')
    assert_success(r)
    out_contains(r, "N=1")
    out_contains(r, "OLD=b")
    out_contains(r, "NEW=x")


def test_绳计算块差异_无变更为空():
    r = run_light_source('''
从 工具_写文件 导入 绳计算块差异
段落 主程序:
  设 块 为 绳计算块差异("f", "a\\nb", "a\\nb")
  打印("N=" + 转字符串(列表长度(块)))
''')
    assert_success(r)
    out_contains(r, "N=0")


def test_绳计算块差异_纯新增():
    r = run_light_source('''
从 工具_写文件 导入 绳计算块差异
段落 主程序:
  设 块 为 绳计算块差异("f", "a", "a\\nb\\nc")
  打印("N=" + 转字符串(列表长度(块)))
  打印("NEW=" + 块[0]["新文本"])
''')
    assert_success(r)
    out_contains(r, "N=1")
    out_contains(r, "b\nc")


def test_绳解析写参数_合法():
    r = run_light_source('''
从 工具_写文件 导入 绳解析写参数
段落 主程序:
  设 p 为 绳解析写参数("f.txt", "内容")
  打印("P=" + p["路径"])
''')
    assert_success(r)
    out_contains(r, "P=f.txt")


def test_绳解析写参数_空串抛错():
    r = run_light_source('''
从 工具_写文件 导入 绳解析写参数
段落 主程序:
  设 p 为 绳解析写参数("", "x")
  打印(p)
''')
    assert_failure(r)


def test_绳解析写参数_非字符串抛错():
    r = run_light_source('''
从 工具_写文件 导入 绳解析写参数
段落 主程序:
  设 p 为 绳解析写参数(123, "x")
  打印(p)
''')
    assert_failure(r)


def test_绳格式化写输出_created():
    r = run_light_source('''
从 工具_写文件 导入 绳格式化写输出
段落 主程序:
  设 s 为 绳格式化写输出("f.txt", "create")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "Created")


def test_绳格式化写输出_updated():
    r = run_light_source('''
从 工具_写文件 导入 绳格式化写输出
段落 主程序:
  设 s 为 绳格式化写输出("f.txt", "update")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "Updated")

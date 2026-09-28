# -*- coding: utf-8 -*-
"""类型系统.light 单元测试。

环境绕过说明：本模块顶层 `从 字符串工具 导入 去除首尾空白` 在「入口文件位于
临时目录」时会被编译器自带 stdlib 的损坏 字符串工具.light 遮蔽（`No module named
'_light_re'`）。实测：把 .light 片段写到 lightharness 根目录、再以其为入口运行时，
stdlib 引导可命中 lightharness/stdlib，导入链正常。故本文件用本地 helper 把片段写到
根目录临时文件 `_frag.light` 后经 run_light_file 运行（不在 src/stdlib/runner 上做任何改动）。
"""
import os
from test_support import (
    run_light_file, ROOT,
    assert_success, assert_failure, out_contains,
)

FRAG = os.path.join(ROOT, "_frag.light")


def run_tp(source):
    with open(FRAG, "w", encoding="utf-8") as fh:
        fh.write(source)
    return run_light_file("_frag.light")


def test_是词符_小写字母为真():
    r = run_tp('''
从 类型系统 导入 是词符
段落 主程序:
  打印("A=" + 转字符串(是词符("a")))
''')
    assert_success(r)
    out_contains(r, "A=True")


def test_是词符_数字与下划线为真():
    r = run_tp('''
从 类型系统 导入 是词符
段落 主程序:
  打印("D=" + 转字符串(是词符("7")))
  打印("U=" + 转字符串(是词符("_")))
  打印("S=" + 转字符串(是词符("$")))
''')
    assert_success(r)
    out_contains(r, "D=True")
    out_contains(r, "U=True")
    out_contains(r, "S=True")


def test_是词符_标点为假():
    r = run_tp('''
从 类型系统 导入 是词符
段落 主程序:
  打印("P=" + 转字符串(是词符(".")))
  打印("H=" + 转字符串(是词符("-")))
  打印("E=" + 转字符串(是词符("!")))
''')
    assert_success(r)
    out_contains(r, "P=False")
    out_contains(r, "H=False")
    out_contains(r, "E=False")


def test_是空白符_空格换行制表为真():
    r = run_tp('''
从 类型系统 导入 是空白符
段落 主程序:
  打印("S=" + 转字符串(是空白符(" ")))
  打印("N=" + 转字符串(是空白符("\\n")))
  打印("L=" + 转字符串(是空白符("a")))
''')
    assert_success(r)
    out_contains(r, "S=True")
    out_contains(r, "N=True")
    out_contains(r, "L=False")


def test_是段字符_点与减号为真():
    r = run_tp('''
从 类型系统 导入 是段字符
段落 主程序:
  打印("D=" + 转字符串(是段字符(".")))
  打印("H=" + 转字符串(是段字符("-")))
  打印("S=" + 转字符串(是段字符("/")))
''')
    assert_success(r)
    out_contains(r, "D=True")
    out_contains(r, "H=True")
    out_contains(r, "S=False")


def test_定位子串_找到返回下标():
    r = run_tp('''
从 类型系统 导入 定位子串
段落 主程序:
  打印("I=" + 转字符串(定位子串("hello world", "world")))
''')
    assert_success(r)
    out_contains(r, "I=6")


def test_定位子串_未找到返回负一():
    r = run_tp('''
从 类型系统 导入 定位子串
段落 主程序:
  打印("I=" + 转字符串(定位子串("abc", "xyz")))
''')
    assert_success(r)
    out_contains(r, "I=-1")


def test_是合法方法_已知为真():
    r = run_tp('''
从 类型系统 导入 是合法方法
段落 主程序:
  打印("A=" + 转字符串(是合法方法("analyze")))
  打印("R=" + 转字符串(是合法方法("listSymbols")))
''')
    assert_success(r)
    out_contains(r, "A=True")
    out_contains(r, "R=True")


def test_是合法方法_未知为假():
    r = run_tp('''
从 类型系统 导入 是合法方法
段落 主程序:
  打印("X=" + 转字符串(是合法方法("destroy")))
''')
    assert_success(r)
    out_contains(r, "X=False")


def test_是合法远程段_普通段为真():
    r = run_tp('''
从 类型系统 导入 是合法远程段
段落 主程序:
  打印("A=" + 转字符串(是合法远程段("a.b")))
  打印("B=" + 转字符串(是合法远程段("Ab9_$")))
''')
    assert_success(r)
    out_contains(r, "A=True")
    out_contains(r, "B=True")


def test_是合法远程段_点双点空串为假():
    r = run_tp('''
从 类型系统 导入 是合法远程段
段落 主程序:
  打印("D=" + 转字符串(是合法远程段(".")))
  打印("E=" + 转字符串(是合法远程段("..")))
  打印("Z=" + 转字符串(是合法远程段("")))
''')
    assert_success(r)
    out_contains(r, "D=False")
    out_contains(r, "E=False")
    out_contains(r, "Z=False")


def test_取字段_多键取首个存在():
    r = run_tp('''
从 类型系统 导入 取字段
段落 主程序:
  设 表 为 {"b": 2, "c": 3}
  打印("V=" + 转字符串(取字段(表, ["a", "b", "c"], -1)))
''')
    assert_success(r)
    out_contains(r, "V=2")


def test_取字段_都缺返回默认():
    r = run_tp('''
从 类型系统 导入 取字段
段落 主程序:
  设 表 为 {"x": 1}
  打印("V=" + 转字符串(取字段(表, ["a", "b"], "def")))
''')
    assert_success(r)
    out_contains(r, "V=def")


def test_有字段_存在为真():
    r = run_tp('''
从 类型系统 导入 有字段
段落 主程序:
  设 表 为 {"a": 1}
  打印("H=" + 转字符串(有字段(表, ["z", "a"])))
''')
    assert_success(r)
    out_contains(r, "H=True")


def test_有字段_都无为假():
    r = run_tp('''
从 类型系统 导入 有字段
段落 主程序:
  设 表 为 {"a": 1}
  打印("H=" + 转字符串(有字段(表, ["z", "q"])))
''')
    assert_success(r)
    out_contains(r, "H=False")


def test_造消息ID_req前缀():
    r = run_tp('''
从 类型系统 导入 造消息ID
段落 主程序:
  打印("ID=" + 造消息ID(42))
''')
    assert_success(r)
    out_contains(r, "ID=req_42")


def test_造请求_合法方法返回形状():
    r = run_tp('''
从 类型系统 导入 造请求
段落 主程序:
  设 m 为 造请求("req_1", "render", [1, 2])
  打印("K=" + m["kind"])
  打印("M=" + m["method"])
  打印("ID=" + m["id"])
''')
    assert_success(r)
    out_contains(r, "K=request")
    out_contains(r, "M=render")
    out_contains(r, "ID=req_1")


def test_造请求_非法方法抛错():
    r = run_tp('''
从 类型系统 导入 造请求
段落 主程序:
  造请求("req_1", "bogus", [])
''')
    assert_failure(r)


def test_造响应与错误响应形状():
    r = run_tp('''
从 类型系统 导入 造响应, 造错误响应
段落 主程序:
  设 a 为 造响应("r1", 99)
  设 b 为 造错误响应("r2", 404, "nf")
  打印("AK=" + a["kind"])
  打印("BK=" + b["kind"])
  打印("BC=" + 转字符串(b["error"]["code"]))
''')
    assert_success(r)
    out_contains(r, "AK=response")
    out_contains(r, "BK=error")
    out_contains(r, "BC=404")


def test_造通知_非法方法抛错():
    r = run_tp('''
从 类型系统 导入 造通知
段落 主程序:
  造通知("nope", [])
''')
    assert_failure(r)


def test_造远程错误_是远程错误识别():
    r = run_tp('''
从 类型系统 导入 造远程错误, 是远程错误
段落 主程序:
  设 e 为 造远程错误("E1", "boom", {"d": 1})
  打印("Y=" + 转字符串(是远程错误(e)))
  设 plain 为 {"a": 1}
  打印("N=" + 转字符串(是远程错误(plain)))
''')
    assert_success(r)
    out_contains(r, "Y=True")
    out_contains(r, "N=False")


def test_造符号表与注册查找往返():
    r = run_tp('''
从 类型系统 导入 造符号表, 注册符号, 有符号, 查找符号
段落 主程序:
  设 表 为 造符号表("pkg")
  注册符号(表, {"名称":"A", "种类":"class"})
  打印("H=" + 转字符串(有符号(表, "A")))
  设 s 为 查找符号(表, "A")
  打印("K=" + s["种类"])
  设 miss 为 查找符号(表, "ZZ")
  如果 miss == 空:
    打印("MISS=空")
''')
    assert_success(r)
    out_contains(r, "H=True")
    out_contains(r, "K=class")
    out_contains(r, "MISS=空")


def test_注册符号_重复抛错():
    r = run_tp('''
从 类型系统 导入 造符号表, 注册符号
段落 主程序:
  设 表 为 造符号表("pkg")
  注册符号(表, {"名称":"A", "种类":"class"})
  注册符号(表, {"名称":"A", "种类":"class"})
''')
    assert_failure(r)


def test_名比较与排序名():
    r = run_tp('''
从 类型系统 导入 名比较, 排序名, 连接文本
段落 主程序:
  打印("C=" + 转字符串(名比较("b", "a")))
  设 out 为 连接文本(排序名(["b", "a", "c"]), ",")
  打印("S=[" + out + "]")
''')
    assert_success(r)
    out_contains(r, "C=1")
    out_contains(r, "S=[a,b,c]")


def test_声明文件头_常量():
    r = run_tp('''
从 类型系统 导入 声明文件头
段落 主程序:
  打印("H=" + 声明文件头())
''')
    assert_success(r)
    out_contains(r, "Generated by")


def test_渲染节点_原语返回名():
    r = run_tp('''
从 类型系统 导入 造原语, 渲染节点
段落 主程序:
  设 n 为 造原语("string")
  打印("V=" + 渲染节点(n))
''')
    assert_success(r)
    out_contains(r, "V=string")


def test_渲染节点_数组带方括号():
    r = run_tp('''
从 类型系统 导入 造原语, 造数组, 渲染节点
段落 主程序:
  设 n 为 造数组(造原语("number"))
  打印("V=" + 渲染节点(n))
''')
    assert_success(r)
    out_contains(r, "V=number[]")


def test_分析声明_提取类名与种类():
    r = run_tp('''
从 类型系统 导入 分析声明
段落 主程序:
  设 s 为 分析声明("export class Foo {}", "pkg")
  打印("N=" + s["名称"])
  打印("K=" + s["种类"])
  打印("E=" + 转字符串(s["导出"]))
''')
    assert_success(r)
    out_contains(r, "N=Foo")
    out_contains(r, "K=class")
    out_contains(r, "E=True")

# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_是有效模式_合法():
    r = run_light_source('''
从 沙箱策略 导入 是有效模式
段落 主程序:
  打印("A=" + 转字符串(是有效模式("read-only")))
  打印("B=" + 转字符串(是有效模式("workspace-write")))
  打印("C=" + 转字符串(是有效模式("danger-full-access")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")
    out_contains(r, "C=真")


def test_是有效模式_非法():
    r = run_light_source('''
从 沙箱策略 导入 是有效模式
段落 主程序:
  打印("A=" + 转字符串(是有效模式("")))
  打印("B=" + 转字符串(是有效模式(空)))
  打印("C=" + 转字符串(是有效模式("no-such-mode")))
''')
    assert_success(r)
    out_contains(r, "A=假")
    out_contains(r, "B=假")
    out_contains(r, "C=假")


def test_折叠绝对路径_消解点点点():
    r = run_light_source('''
从 沙箱策略 导入 折叠绝对路径
段落 主程序:
  打印("A=" + 折叠绝对路径("/a/b/../c"))
  打印("B=" + 折叠绝对路径("/a/./b//c/"))
  打印("C=" + 折叠绝对路径("/.."))
  打印("D=" + 折叠绝对路径("/a/../../.."))
''')
    assert_success(r)
    out_contains(r, "A=/a/c")
    out_contains(r, "B=/a/b/c")
    out_contains(r, "C=/")
    out_contains(r, "D=/")


def test_折叠绝对路径_盘符():
    r = run_light_source('''
从 沙箱策略 导入 折叠绝对路径
段落 主程序:
  打印("A=" + 折叠绝对路径("C:/a/b/../c"))
  打印("B=" + 折叠绝对路径("C:\\\\a\\\\b\\\\..\\\\c"))
''')
    assert_success(r)
    out_contains(r, "A=C:/a/c")
    out_contains(r, "B=C:/a/c")


def test_规范路径_合法绝对():
    r = run_light_source('''
从 沙箱策略 导入 规范路径
段落 主程序:
  打印("A=" + 规范路径("/ws/project"))
  打印("B=" + 规范路径("/ws/./x/../y"))
''')
    assert_success(r)
    out_contains(r, "A=/ws/project")
    out_contains(r, "B=/ws/y")


def test_规范路径_空报错():
    r = run_light_source('''
从 沙箱策略 导入 规范路径
段落 主程序:
  设 x 为 规范路径("")
  打印("不应到达")
''')
    assert_failure(r)


def test_规范路径_相对路径报错():
    r = run_light_source('''
从 沙箱策略 导入 规范路径
段落 主程序:
  设 x 为 规范路径("relative/path")
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "必须是绝对")


def test_规范策略_合法read_only():
    r = run_light_source('''
从 沙箱策略 导入 规范策略
段落 主程序:
  设 p 为 规范策略({"模式":"read-only", "工作区根":"/ws"})
  打印("模式=" + p["模式"])
  打印("根=" + p["工作区根"])
''')
    assert_success(r)
    out_contains(r, "模式=read-only")
    out_contains(r, "根=/ws")


def test_规范策略_透传会话Id():
    r = run_light_source('''
从 沙箱策略 导入 规范策略
段落 主程序:
  设 p 为 规范策略({"模式":"workspace-write", "工作区根":"/ws", "会话Id":"s-1"})
  打印("会话=" + p["会话Id"])
''')
    assert_success(r)
    out_contains(r, "会话=s-1")


def test_规范策略_缺模式报错():
    r = run_light_source('''
从 沙箱策略 导入 规范策略
段落 主程序:
  设 p 为 规范策略({"工作区根":"/ws"})
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "策略缺少模式")


def test_规范策略_非法模式报错():
    r = run_light_source('''
从 沙箱策略 导入 规范策略
段落 主程序:
  设 p 为 规范策略({"模式":"yolo", "工作区根":"/ws"})
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "非法模式")


def test_规范策略_缺工作区根报错():
    r = run_light_source('''
从 沙箱策略 导入 规范策略
段落 主程序:
  设 p 为 规范策略({"模式":"read-only"})
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "工作区根必填")


def test_可写根_仅workspace_write():
    r = run_light_source('''
从 沙箱策略 导入 可写根
段落 主程序:
  设 a 为 可写根({"模式":"workspace-write", "工作区根":"/ws"})
  设 b 为 可写根({"模式":"read-only", "工作区根":"/ws"})
  设 c 为 可写根({"模式":"danger-full-access", "工作区根":"/ws"})
  打印("A=" + a)
  如果 b == 空:
    打印("B=空")
  否则:
    打印("B=非空")
  如果 c == 空:
    打印("C=空")
  否则:
    打印("C=非空")
''')
    assert_success(r)
    out_contains(r, "A=/ws")
    out_contains(r, "B=空")
    out_contains(r, "C=空")


def test_危险全访问判定():
    r = run_light_source('''
从 沙箱策略 导入 危险全访问
段落 主程序:
  打印("A=" + 转字符串(危险全访问({"模式":"danger-full-access"})))
  打印("B=" + 转字符串(危险全访问({"模式":"read-only"})))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")


def test_渲染策略上下文_三模式():
    r = run_light_source('''
从 沙箱策略 导入 渲染策略上下文
段落 主程序:
  设 t1 为 渲染策略上下文({"模式":"read-only"})
  设 t2 为 渲染策略上下文({"模式":"workspace-write", "工作区根":"/ws"})
  设 t3 为 渲染策略上下文({"模式":"danger-full-access"})
  打印("R=" + 转字符串(字符串包含(t1, "read-only")))
  打印("W=" + 转字符串(字符串包含(t2, "/ws")))
  打印("D=" + 转字符串(字符串包含(t3, "does not restrict")))
''')
    assert_success(r)
    out_contains(r, "R=真")
    out_contains(r, "W=真")
    out_contains(r, "D=真")

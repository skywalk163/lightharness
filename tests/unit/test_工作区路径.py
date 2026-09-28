# -*- coding: utf-8 -*-
"""工作区路径：路径分类/拼接/缩写/标题/分部 + file-address 编解码。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_是Windows风格路径_盘符():
    r = run_light_source('''
从 工作区路径 导入 是Windows风格路径
段落 主程序:
  设 a 为 "NO"
  如果 是Windows风格路径("C:\\\\x"): 设 a 为 "YES"
  设 b 为 "NO"
  如果 是Windows风格路径("/home/x"): 设 b 为 "YES"
  打印("WIN=" + a)
  打印("POSIX=" + b)
''')
    assert_success(r)
    out_contains(r, "WIN=YES")
    out_contains(r, "POSIX=NO")


def test_是绝对工作区路径():
    r = run_light_source('''
从 工作区路径 导入 是绝对工作区路径
段落 主程序:
  设 a 为 "NO"
  如果 是绝对工作区路径("/home/x"): 设 a 为 "YES"
  设 b 为 "NO"
  如果 是绝对工作区路径("rel/path"): 设 b 为 "YES"
  打印("ABS=" + a)
  打印("REL=" + b)
''')
    assert_success(r)
    out_contains(r, "ABS=YES")
    out_contains(r, "REL=NO")


def test_去尾分隔():
    r = run_light_source('''
从 工作区路径 导入 去尾分隔
段落 主程序:
  设 s 为 去尾分隔("/a/b/")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=/a/b")


def test_去头分隔():
    r = run_light_source('''
从 工作区路径 导入 去头分隔
段落 主程序:
  设 s 为 去头分隔("//a/b")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=a/b")


def test_解析工作区路径_相对拼接():
    r = run_light_source('''
从 工作区路径 导入 解析工作区路径
段落 主程序:
  设 s 为 解析工作区路径("/home/user/proj", "src/main.py")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=/home/user/proj/src/main.py")


def test_解析工作区路径_绝对原样():
    r = run_light_source('''
从 工作区路径 导入 解析工作区路径
段落 主程序:
  设 s 为 解析工作区路径("/home/user/proj", "/etc/hosts")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=/etc/hosts")


def test_缩写主目录路径_本身为波浪号():
    r = run_light_source('''
从 工作区路径 导入 缩写主目录路径
段落 主程序:
  设 s 为 缩写主目录路径("/home/u", "/home/u")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=~")


def test_缩写主目录路径_后代():
    r = run_light_source('''
从 工作区路径 导入 缩写主目录路径
段落 主程序:
  设 s 为 缩写主目录路径("/home/u/proj/a.py", "/home/u")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=~/proj/a.py")


def test_工作区标题():
    r = run_light_source('''
从 工作区路径 导入 工作区标题
段落 主程序:
  设 s 为 工作区标题("/home/user/proj")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=proj")


def test_路径分部():
    r = run_light_source('''
从 工作区路径 导入 路径分部
段落 主程序:
  设 p 为 路径分部("/home/user/a/b.txt")
  打印("DIR=" + p["目录"])
  打印("NAME=" + p["名字"])
''')
    assert_success(r)
    out_contains(r, "DIR=/home/user/a/")
    out_contains(r, "NAME=b.txt")


def test_会话文件地址_与会话解析往返():
    r = run_light_source('''
从 工作区路径 导入 会话文件地址, 解析文件地址
段落 主程序:
  设 addr 为 会话文件地址("sess1", "src/main.py")
  设 back 为 解析文件地址(addr)
  打印("SCOPE=" + back["scope"])
  打印("ID=" + back["sessionId"])
  打印("P=" + back["path"])
''')
    assert_success(r)
    out_contains(r, "SCOPE=session")
    out_contains(r, "ID=sess1")
    out_contains(r, "P=src/main.py")


def test_解析文件地址_坏前缀返回空():
    r = run_light_source('''
从 工作区路径 导入 解析文件地址
段落 主程序:
  设 v 为 解析文件地址("http://example.com/x")
  设 s 为 "NO"
  如果 v == 空: 设 s 为 "YES"
  打印("BAD=" + s)
''')
    assert_success(r)
    out_contains(r, "BAD=YES")


def test_文件地址For_相对路径走会话域():
    r = run_light_source('''
从 工作区路径 导入 文件地址For, 解析文件地址
段落 主程序:
  设 addr 为 文件地址For("sid", "/home/u/proj", "rel/file.py")
  设 back 为 解析文件地址(addr)
  打印("SCOPE=" + back["scope"])
  打印("P=" + back["path"])
''')
    assert_success(r)
    out_contains(r, "SCOPE=session")
    out_contains(r, "P=rel/file.py")


def test_相对化到cwd_剥根():
    r = run_light_source('''
从 工作区路径 导入 相对化到cwd
段落 主程序:
  设 s 为 相对化到cwd("/home/u/proj/src/main.py", "/home/u/proj")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "S=src/main.py")

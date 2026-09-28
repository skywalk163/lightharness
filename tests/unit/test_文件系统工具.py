# -*- coding: utf-8 -*-
"""文件系统工具：读参数/守卫/窗口渲染/图类型/写判定/编辑施加/行差分。"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_提示读错误_未观察():
    r = run_light_source('''
从 文件系统工具 导入 提示读错误
段落 主程序:
  设 s 为 提示读错误("FS_NOT_OBSERVED", "f.txt", "")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "has not been read")


def test_守卫编辑前提_未观察拒绝():
    r = run_light_source('''
从 文件系统工具 导入 守卫编辑前提
段落 主程序:
  设 g 为 守卫编辑前提(假, 空, 空, "f.txt")
  设 s 为 "NO"
  如果 g["许可"]: 设 s 为 "YES"
  打印("ALLOW=" + s)
''')
    assert_success(r)
    out_contains(r, "ALLOW=NO")


def test_守卫编辑前提_版本过期拒绝():
    r = run_light_source('''
从 文件系统工具 导入 守卫编辑前提
段落 主程序:
  设 g 为 守卫编辑前提(真, 3, 5, "f.txt")
  设 s 为 "NO"
  如果 g["许可"]: 设 s 为 "YES"
  打印("ALLOW=" + s)
''')
    assert_success(r)
    out_contains(r, "ALLOW=NO")


def test_守卫编辑前提_许可():
    r = run_light_source('''
从 文件系统工具 导入 守卫编辑前提
段落 主程序:
  设 g 为 守卫编辑前提(真, 空, 空, "f.txt")
  设 s 为 "NO"
  如果 g["许可"]: 设 s 为 "YES"
  打印("ALLOW=" + s)
''')
    assert_success(r)
    out_contains(r, "ALLOW=YES")


def test_解析读参数_默认值():
    r = run_light_source('''
从 文件系统工具 导入 解析读参数
段落 主程序:
  设 p 为 解析读参数({"file_path": "f.txt"}, 2000)
  打印("P=" + p["路径"])
  打印("OFF=" + 转字符串(p["偏移"]))
''')
    assert_success(r)
    out_contains(r, "P=f.txt")
    out_contains(r, "OFF=1")


def test_解析读参数_缺path抛错():
    r = run_light_source('''
从 文件系统工具 导入 解析读参数
段落 主程序:
  设 p 为 解析读参数({}, 2000)
  打印(p)
''')
    assert_failure(r)


def test_解析读参数_limit超限抛错():
    r = run_light_source('''
从 文件系统工具 导入 解析读参数
段落 主程序:
  设 p 为 解析读参数({"file_path": "f", "limit": 99999}, 2000)
  打印(p)
''')
    assert_failure(r)


def test_判读目标_找不到():
    r = run_light_source('''
从 文件系统工具 导入 判读目标
段落 主程序:
  设 s 为 判读目标(空, "f.txt")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "not found")


def test_判读目标_非文件():
    r = run_light_source('''
从 文件系统工具 导入 判读目标
段落 主程序:
  设 s 为 判读目标({"类型": "目录", "大小": 0, "版本": 1}, "d")
  打印("S=" + s)
''')
    assert_success(r)
    out_contains(r, "not a regular file")


def test_造读窗口_偏移与上限():
    r = run_light_source('''
从 文件系统工具 导入 造读窗口
段落 主程序:
  设 w 为 造读窗口(["l1", "l2", "l3"], 1, 2, "f", 2000, 51200)
  打印("N=" + 转字符串(列表长度(w["行表"])))
  打印("TOT=" + 转字符串(w["总行数"]))
''')
    assert_success(r)
    out_contains(r, "N=2")
    out_contains(r, "TOT=3")


def test_造读窗口_offset越界抛错():
    r = run_light_source('''
从 文件系统工具 导入 造读窗口
段落 主程序:
  设 w 为 造读窗口(["l1"], 99, 10, "f", 2000, 51200)
  打印(转字符串(w))
''')
    assert_failure(r)


def test_语言自路径_py():
    r = run_light_source('''
从 文件系统工具 导入 语言自路径
段落 主程序:
  设 s 为 语言自路径("a/b/c.py")
  打印("L=" + s)
''')
    assert_success(r)
    out_contains(r, "L=py")


def test_图媒体类型_png扩展名():
    r = run_light_source('''
从 文件系统工具 导入 图媒体类型
段落 主程序:
  设 t 为 图媒体类型("photo.png", [])
  打印("T=" + t)
''')
    assert_success(r)
    out_contains(r, "T=image/png")


def test_图媒体类型_不支持抛错():
    r = run_light_source('''
从 文件系统工具 导入 图媒体类型
段落 主程序:
  设 t 为 图媒体类型("x.bmp", [1, 2, 3])
  打印(t)
''')
    assert_failure(r)


def test_写操作判定_create与update():
    r = run_light_source('''
从 文件系统工具 导入 写操作判定, 写后信封
段落 主程序:
  设 a 为 写操作判定(假)
  设 b 为 写操作判定(真)
  设 env 为 写后信封("f", a)
  打印("A=" + a)
  打印("B=" + b)
  打印("ENV=" + env)
''')
    assert_success(r)
    out_contains(r, "A=create")
    out_contains(r, "B=update")
    out_contains(r, "Created")


def test_判写参数_缺content抛错():
    r = run_light_source('''
从 文件系统工具 导入 判写参数
段落 主程序:
  设 p 为 判写参数({"file_path": "f"})
  打印(p)
''')
    assert_failure(r)


def test_施加编辑_单次替换():
    r = run_light_source('''
从 文件系统工具 导入 施加编辑
段落 主程序:
  设 r 为 施加编辑("hello world", "world", "there", 假)
  设 s 为 "NO"
  如果 r["许可"]: 设 s 为 "YES"
  打印("OK=" + s)
  打印("C=" + r["内容"])
''')
    assert_success(r)
    out_contains(r, "OK=YES")
    out_contains(r, "C=hello there")


def test_施加编辑_无命中():
    r = run_light_source('''
从 文件系统工具 导入 施加编辑
段落 主程序:
  设 r 为 施加编辑("abc", "xyz", "q", 假)
  设 s 为 "NO"
  如果 r["许可"]: 设 s 为 "YES"
  打印("OK=" + s)
''')
    assert_success(r)
    out_contains(r, "OK=NO")


def test_渲染统一差异文本_含头():
    r = run_light_source('''
从 文件系统工具 导入 行差分表, 渲染统一差异文本
段落 主程序:
  设 块 为 行差分表("a\\nb", "a\\nc")
  设 s 为 渲染统一差异文本("f.txt", 块)
  打印("H=" + s)
''')
    assert_success(r)
    out_contains(r, "--- a/f.txt")
    out_contains(r, "@@")

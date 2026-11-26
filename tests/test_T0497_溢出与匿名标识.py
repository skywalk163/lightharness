# -*- coding: utf-8 -*-
"""T-0520：溢出与匿名标识三条确定性契约缺陷的回归判据。

本文件补的是门禁里长期缺失的那一层——把「实现与上游语义契约」写死成断言：

  1. 匿名标识：后缀必须**恰好 8 位**（构造出的 ID 必须能通过自己的校验，
     且同一标识长度恰为 5+8=13；不同盐必须产出不同标识，不能被截断抹平）。
  2. 构造预览：预算不足时做**头尾各留一部分**的部分拼接（"abcdef"/预算 4 → "abef"），
     省略计数按字节精确；预算 0 全省略、预算充足原样返回。
  3. 保留内容：小预算必须**留满预算字数**（预算 6 就留 6 字，省略 = 总长 - 6），
     且边界预算（1/2/3）不越界、不出负数切片。

全部用例都走真实执行管线（python 运行.py <driver>），不是对 Python 侧实现的直调。
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "unit"))

from test_support import (  # noqa: E402
    run_light_source, assert_success, out_contains,
)


# ---------- 1. 匿名标识 ----------

def test_匿名标识_长度恰为13且自校验通过():
    r = run_light_source('''
从 安全策略 导入 构造匿名标识, 校验匿名标识
段落 主程序:
  设 id 为 构造匿名标识("seed1", "salt1")
  打印("ID=" + id)
  打印("LEN=" + 转字符串(字符串长度(id)))
  打印("合法=" + 转字符串(校验匿名标识(id)))
''')
    assert_success(r)
    out_contains(r, "ID=anon-")
    # 5(anon-) + 8(十六进制后缀) = 13，后缀不截断就是自相矛盾
    out_contains(r, "LEN=13")
    out_contains(r, "合法=True")


def test_匿名标识_不同盐不撞车():
    r = run_light_source('''
从 安全策略 导入 构造匿名标识
段落 主程序:
  设 a 为 构造匿名标识("seed1", "salt1")
  设 b 为 构造匿名标识("seed1", "salt2")
  打印("SAME=" + 转字符串(a == b))
  打印("LA=" + 转字符串(字符串长度(a)))
  打印("LB=" + 转字符串(字符串长度(b)))
''')
    assert_success(r)
    # 截断只保留高位、哈希不取模时，两个不同盐会撞成同一个前缀——这里钉死不复现
    out_contains(r, "SAME=False")
    out_contains(r, "LA=13")
    out_contains(r, "LB=13")


def test_匿名标识_确定性():
    r = run_light_source('''
从 安全策略 导入 构造匿名标识
段落 主程序:
  打印("R=" + 转字符串(构造匿名标识("seed1", "salt1") == 构造匿名标识("seed1", "salt1")))
''')
    assert_success(r)
    out_contains(r, "R=True")


# ---------- 2. 构造预览 ----------

def test_构造预览_部分预算头尾拼接():
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


def test_构造预览_奇数预算头尾拼接():
    r = run_light_source('''
从 溢出 导入 构造预览
段落 主程序:
  设 结果 为 构造预览("abcdefgh", 5)
  打印("T=[" + 结果["文本"] + "]")
  打印("N=" + 转字符串(结果["省略"]["计数"]))
''')
    assert_success(r)
    # ceil(5/2)=3 前 + floor(5/2)=2 后 → "abcgh"，省略 3 字节
    out_contains(r, "T=[abcgh]")
    out_contains(r, "N=3")


def test_构造预览_零预算与充足预算边界():
    r = run_light_source('''
从 溢出 导入 构造预览
段落 主程序:
  设 零 为 构造预览("abcdef", 0)
  设 足 为 构造预览("abcdef", 6)
  打印("Z=[" + 零["文本"] + "]" + 零["省略"]["种类"] + 转字符串(零["省略"]["计数"]))
  打印("F=[" + 足["文本"] + "]" + 足["省略"]["种类"])
''')
    assert_success(r)
    out_contains(r, "Z=[]精确6")
    out_contains(r, "F=[abcdef]无")


# ---------- 3. 保留内容 ----------

def test_保留内容_小预算留满预算字数():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  设 收 为 保留内容([{"类型": "文本", "文本": "ABCDEFGHIJ"}], 6)
  打印("H=" + 收["头"][0]["文本"])
  打印("T=" + 收["尾"][0]["文本"])
  打印("B=" + 转字符串(收["省略字节"]))
''')
    assert_success(r)
    # 预算 6 → 头 ceil(6/2)=3 字、尾 floor(6/2)=3 字，留满 6 字，省略 10-6=4
    out_contains(r, "H=ABC")
    out_contains(r, "T=HIJ")
    out_contains(r, "B=4")


def test_保留内容_边界预算不越界():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  遍历 预算 之 [1, 2, 3]:
    设 收 为 保留内容([{"类型": "文本", "文本": "ABCDEFGHIJ"}], 预算)
    设 头文 为 ""
    如果 列表长度(收["头"]) > 0: 设 头文 为 收["头"][0]["文本"]
    设 尾文 为 ""
    如果 列表长度(收["尾"]) > 0: 设 尾文 为 收["尾"][0]["文本"]
    设 留 为 字符串长度(头文) + 字符串长度(尾文)
    打印("B=" + 转字符串(预算) + " 留=" + 转字符串(留) + " O=" + 转字符串(收["省略字节"]))
''')
    assert_success(r)
    # 每个预算都恰好留满，不出现负数切片 / 越界
    out_contains(r, "B=1 留=1 O=9")
    out_contains(r, "B=2 留=2 O=8")
    out_contains(r, "B=3 留=3 O=7")


def test_保留内容_预算零与充足预算():
    r = run_light_source('''
从 溢出保留 导入 保留内容
段落 主程序:
  设 零 为 保留内容([{"类型": "文本", "文本": "abc"}], 0)
  设 足 为 保留内容([{"类型": "文本", "文本": "abc"}], 100)
  打印("Z=" + 转字符串(零["省略字节"]))
  打印("F=" + 转字符串(足["省略字节"]))
''')
    assert_success(r)
    out_contains(r, "Z=3")
    out_contains(r, "F=0")
# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_校验凭证名_合法():
    r = run_light_source('''
从 安全策略 导入 校验凭证名
段落 主程序:
  打印("A=" + 转字符串(校验凭证名("MY_KEY")))
  打印("B=" + 转字符串(校验凭证名("_abc123")))
  打印("C=" + 转字符串(校验凭证名("k")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")
    out_contains(r, "C=真")


def test_校验凭证名_非法():
    r = run_light_source('''
从 安全策略 导入 校验凭证名
段落 主程序:
  打印("A=" + 转字符串(校验凭证名("")))
  打印("B=" + 转字符串(校验凭证名("1abc")))
  打印("C=" + 转字符串(校验凭证名("has-dash")))
  打印("D=" + 转字符串(校验凭证名("has space")))
''')
    assert_success(r)
    out_contains(r, "A=假")
    out_contains(r, "B=假")
    out_contains(r, "C=假")
    out_contains(r, "D=假")


def test_判定敏感名_命中():
    r = run_light_source('''
从 安全策略 导入 判定敏感名
段落 主程序:
  设 黑 为 ["secret", "token", "password"]
  打印("A=" + 转字符串(判定敏感名("my_secret_key", 黑)))
  打印("B=" + 转字符串(判定敏感名("api_token", 黑)))
  打印("C=" + 转字符串(判定敏感名("normal_name", 黑)))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")
    out_contains(r, "C=假")


def test_脱敏值_保留首尾():
    r = run_light_source('''
从 安全策略 导入 脱敏值
段落 主程序:
  打印("A=" + 脱敏值("sk-1234567890abcdef", 2, 2))
''')
    assert_success(r)
    out_contains(r, "A=sk***ef")


def test_脱敏值_太短返回星号():
    r = run_light_source('''
从 安全策略 导入 脱敏值
段落 主程序:
  打印("A=" + 脱敏值("abc", 2, 2))
  打印("B=" + 脱敏值("ab", 2, 2))
''')
    assert_success(r)
    out_contains(r, "A=***")
    out_contains(r, "B=***")


def test_脱敏文本_替换前缀():
    r = run_light_source('''
从 安全策略 导入 脱敏文本
段落 主程序:
  设 t 为 "token is sk-1234567890xyz here"
  设 out 为 脱敏文本(t, ["sk-"], [])
  打印("OUT=" + out)
''')
    assert_success(r)
    out_contains(r, "sk***yz")
    out_not_contains(r, "1234567890xyz")


def test_脱敏文本_白名单跳过():
    r = run_light_source('''
从 安全策略 导入 脱敏文本
段落 主程序:
  设 t 为 "token is sk-allowed123 done"
  设 out 为 脱敏文本(t, ["sk-"], ["sk-allowed123"])
  打印("OUT=" + out)
''')
    assert_success(r)
    out_contains(r, "sk-allowed123")


def test_判定已脱敏():
    r = run_light_source('''
从 安全策略 导入 判定已脱敏
段落 主程序:
  打印("A=" + 转字符串(判定已脱敏("abc***def")))
  打印("B=" + 转字符串(判定已脱敏("plain text")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")


def test_计算哈希_确定性():
    r = run_light_source('''
从 安全策略 导入 计算哈希
段落 主程序:
  设 h1 为 计算哈希("hello world")
  设 h2 为 计算哈希("hello world")
  设 h3 为 计算哈希("different")
  打印("SAME=" + 转字符串(h1 == h2))
  打印("DIFF=" + 转字符串(h1 == h3))
''')
    assert_success(r)
    out_contains(r, "SAME=真")
    out_contains(r, "DIFF=假")


def test_转十六进制():
    r = run_light_source('''
从 安全策略 导入 转十六进制
段落 主程序:
  打印("A=" + 转十六进制(255))
  打印("B=" + 转十六进制(0))
  打印("C=" + 转十六进制(16))
''')
    assert_success(r)
    out_contains(r, "A=ff")
    out_contains(r, "B=0")
    out_contains(r, "C=10")


def test_构造匿名标识_往返校验():
    r = run_light_source('''
从 安全策略 导入 构造匿名标识, 校验匿名标识, 判定标识一致
段落 主程序:
  设 id 为 构造匿名标识("seed1", "salt1")
  打印("ID=" + id)
  打印("合法=" + 转字符串(校验匿名标识(id)))
  打印("一致=" + 转字符串(判定标识一致("seed1", "salt1", id)))
  打印("不一致=" + 转字符串(判定标识一致("seed1", "salt2", id)))
''')
    assert_success(r)
    out_contains(r, "ID=anon-")
    out_contains(r, "合法=真")
    out_contains(r, "一致=真")
    out_contains(r, "不一致=假")


def test_校验匿名标识_非法格式():
    r = run_light_source('''
从 安全策略 导入 校验匿名标识
段落 主程序:
  打印("A=" + 转字符串(校验匿名标识("plain")))
  打印("B=" + 转字符串(校验匿名标识("anon-1234567")))
  打印("C=" + 转字符串(校验匿名标识("anon-XXXXXXXX")))
''')
    assert_success(r)
    out_contains(r, "A=假")
    out_contains(r, "B=假")
    out_contains(r, "C=假")


def test_策略谓词_默认与规则():
    r = run_light_source('''
从 安全策略 导入 策略谓词
段落 允许tmp(上下文):
  返回 上下文["路径"] == "/tmp"
段落 主程序:
  设 p 为 新建 策略谓词(真)
  打印("默认=" + 转字符串(p.判定("写", {"路径":"/elsewhere"})))
  p.添加规则("写", 允许tmp, 假)
  打印("拒绝=" + 转字符串(p.判定("写", {"路径":"/tmp"})))
  打印("回退=" + 转字符串(p.判定("读", {"路径":"/tmp"})))
''')
    assert_success(r)
    out_contains(r, "默认=真")
    out_contains(r, "拒绝=假")
    out_contains(r, "回退=真")


def test_解析界限规则_合法():
    r = run_light_source('''
从 安全策略 导入 解析界限规则
段落 主程序:
  设 r1 为 解析界限规则("SID-1:read:allow")
  设 r2 为 解析界限规则("SID-2:write:deny")
  打印("主体=" + r1.主体)
  打印("权限=" + r1.权限)
  打印("允许1=" + 转字符串(r1.允许))
  打印("允许2=" + 转字符串(r2.允许))
''')
    assert_success(r)
    out_contains(r, "主体=SID-1")
    out_contains(r, "权限=read")
    out_contains(r, "允许1=真")
    out_contains(r, "允许2=假")


def test_解析界限规则_格式错误():
    r = run_light_source('''
从 安全策略 导入 解析界限规则
段落 主程序:
  设 x 为 解析界限规则("only-two:parts")
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "界限规则格式错误")


def test_解析界限规则_动作错误():
    r = run_light_source('''
从 安全策略 导入 解析界限规则
段落 主程序:
  设 x 为 解析界限规则("SID:read:maybe")
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "动作必须为")


def test_界限判定器_拒绝优先():
    r = run_light_source('''
从 安全策略 导入 解析界限规则, 界限判定器
段落 主程序:
  设 d 为 新建 界限判定器()
  d.添加规则(解析界限规则("U1:read:allow"))
  d.添加规则(解析界限规则("U1:read:deny"))
  d.添加规则(解析界限规则("U2:*:allow"))
  打印("拒绝优先=" + 转字符串(d.判定("U1", "read")))
  打印("通配=" + 转字符串(d.判定("U2", "write")))
  打印("无规则=" + 转字符串(d.判定("U3", "read")))
''')
    assert_success(r)
    out_contains(r, "拒绝优先=假")
    out_contains(r, "通配=真")
    out_contains(r, "无规则=假")


def test_构造溢出目录名与超阈():
    r = run_light_source('''
从 安全策略 导入 构造溢出目录名, 判定超阈
段落 主程序:
  设 n 为 构造溢出目录名("spill", "sess1", 3)
  打印("名=" + n)
  打印("超=" + 转字符串(判定超阈(200, 100)))
  打印("未超=" + 转字符串(判定超阈(50, 100)))
''')
    assert_success(r)
    out_contains(r, "名=spill-sess1-3")
    out_contains(r, "超=真")
    out_contains(r, "未超=假")


def test_判定超阈_负数上限报错():
    r = run_light_source('''
从 安全策略 导入 判定超阈
段落 主程序:
  设 x 为 判定超阈(10, -1)
  打印("不应到达")
''')
    assert_failure(r)


def test_整理清理顺序_按时间戳():
    r = run_light_source('''
从 安全策略 导入 溢出条目, 整理清理顺序
段落 主程序:
  设 表 为 []
  列表追加(表, 新建 溢出条目("c", 50, 300))
  列表追加(表, 新建 溢出条目("a", 50, 100))
  列表追加(表, 新建 溢出条目("b", 50, 200))
  设 序 为 整理清理顺序(表)
  打印("序=" + 序列化JSON(序))
''')
    assert_success(r)
    out_contains(r, '序=["a", "b", "c"]')


def test_计算清理目标_最旧先清():
    r = run_light_source('''
从 安全策略 导入 溢出条目, 计算清理目标
段落 主程序:
  设 表 为 []
  列表追加(表, 新建 溢出条目("old", 50, 100))
  列表追加(表, 新建 溢出条目("mid", 50, 200))
  列表追加(表, 新建 溢出条目("new", 50, 300))
  设 目标 为 计算清理目标(表, 70)
  打印("目标=" + 序列化JSON(目标))
''')
    assert_success(r)
    out_contains(r, '目标=["old", "mid"]')

# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_具规整级别_中文归一():
    r = run_light_source('''
从 工具执行 导入 具规整级别
段落 主程序:
  打印("A=" + 具规整级别("公开"))
  打印("B=" + 具规整级别("内部"))
  打印("C=" + 具规整级别("私有"))
  打印("D=" + 具规整级别("public"))
''')
    assert_success(r)
    out_contains(r, "A=public")
    out_contains(r, "B=internal")
    out_contains(r, "C=private")
    out_contains(r, "D=public")


def test_具是级别():
    r = run_light_source('''
从 工具执行 导入 具是级别
段落 主程序:
  打印("A=" + 转字符串(具是级别("public")))
  打印("B=" + 转字符串(具是级别("公开")))
  打印("C=" + 转字符串(具是级别("bogus")))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=真")
    out_contains(r, "C=假")


def test_具注册工具_可取回():
    r = run_light_source('''
从 工具执行 导入 建注册表, 具注册工具, 取工具, 级公开
段落 主程序:
  设 reg 为 建注册表()
  具注册工具(reg, "t1", 级公开)
  设 t 为 取工具(reg, "t1")
  打印("名=" + t["名称"])
  打印("级=" + t["级别"])
''')
    assert_success(r)
    out_contains(r, "名=t1")
    out_contains(r, "级=public")


def test_具注册工具_空名报错():
    r = run_light_source('''
从 工具执行 导入 建注册表, 具注册工具, 级公开
段落 主程序:
  设 reg 为 建注册表()
  具注册工具(reg, "", 级公开)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "INVALID_TOOL_NAME")


def test_具注册工具_重名报错():
    r = run_light_source('''
从 工具执行 导入 建注册表, 具注册工具, 级公开
段落 主程序:
  设 reg 为 建注册表()
  具注册工具(reg, "dup", 级公开)
  具注册工具(reg, "dup", 级公开)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "DUPLICATE_TOOL")


def test_具注册工具_未知级别报错():
    r = run_light_source('''
从 工具执行 导入 建注册表, 具注册工具
段落 主程序:
  设 reg 为 建注册表()
  具注册工具(reg, "t", "yolo")
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "UNKNOWN_LEVEL")


def test_具可否见_可见矩阵():
    r = run_light_source('''
从 工具执行 导入 具可否见, 级公开, 级内部, 级私有
段落 主程序:
  打印("A=" + 转字符串(具可否见(级公开, 级公开)))
  打印("B=" + 转字符串(具可否见(级内部, 级公开)))
  打印("C=" + 转字符串(具可否见(级私有, 级内部)))
  打印("D=" + 转字符串(具可否见(级内部, 级私有)))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")
    out_contains(r, "C=假")
    out_contains(r, "D=真")


def test_权限判定_公开放行():
    r = run_light_source('''
从 工具执行 导入 建注册表, 具注册工具, 取工具, 权限判定, 级公开
段落 主程序:
  设 reg 为 建注册表()
  具注册工具(reg, "pub", 级公开)
  设 t 为 取工具(reg, "pub")
  设 d 为 权限判定(t, "public")
  打印("可见=" + 转字符串(d["可见"]))
  打印("可调=" + 转字符串(d["可调用"]))
''')
    assert_success(r)
    out_contains(r, "可见=真")
    out_contains(r, "可调=真")


def test_权限判定_私有拒绝():
    r = run_light_source('''
从 工具执行 导入 建注册表, 具注册工具, 取工具, 权限判定, 级私有
段落 主程序:
  设 reg 为 建注册表()
  具注册工具(reg, "priv", 级私有)
  设 t 为 取工具(reg, "priv")
  设 d 为 权限判定(t, "public")
  打印("可调=" + 转字符串(d["可调用"]))
  打印("码=" + d["错误码"])
''')
    assert_success(r)
    out_contains(r, "可调=假")
    out_contains(r, "码=PERMISSION_DENIED")


def test_权限判定_工具不存在():
    r = run_light_source('''
从 工具执行 导入 权限判定
段落 主程序:
  设 d 为 权限判定(空, "public")
  打印("码=" + d["错误码"])
''')
    assert_success(r)
    out_contains(r, "码=TOOL_NOT_FOUND")


def test_取消令牌_流程():
    r = run_light_source('''
从 工具执行 导入 建取消令牌, 是否取消, 请求取消
段落 主程序:
  设 tok 为 建取消令牌()
  打印("初始=" + 转字符串(是否取消(tok)))
  请求取消(tok, "用户中止")
  打印("取消后=" + 转字符串(是否取消(tok)))
  请求取消(tok, "再次")
  打印("仍取消=" + 转字符串(是否取消(tok)))
''')
    assert_success(r)
    out_contains(r, "初始=假")
    out_contains(r, "取消后=真")
    out_contains(r, "仍取消=真")


def test_检查取消_抛出():
    r = run_light_source('''
从 工具执行 导入 建取消令牌, 请求取消, 检查取消
段落 主程序:
  设 tok 为 建取消令牌()
  请求取消(tok, "x")
  设 x 为 检查取消(tok)
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "TOOL_CANCELLED")


def test_审计日志_环形容量():
    r = run_light_source('''
从 工具执行 导入 建审计日志, 具记审计, 审计条数, 审计开始
段落 主程序:
  设 log 为 建审计日志(2)
  具记审计(log, 审计开始, "t1", "c", "start")
  具记审计(log, 审计开始, "t2", "c", "start")
  具记审计(log, 审计开始, "t3", "c", "start")
  打印("条数=" + 转字符串(审计条数(log)))
''')
    assert_success(r)
    out_contains(r, "条数=2")


_HELPERS = '''
段落 处理回显(参数, 令牌):
  返回 "got:" + 参数["x"]
段落 处理爆炸(参数, 令牌):
  抛出 新建 错误("boom")
'''


def test_执行工具_成功():
    r = run_light_source('''
从 工具执行 导入 建执行器, 具注册工具, 执行工具, 级公开
''' + _HELPERS + '''
段落 主程序:
  设 ex 为 建执行器()
  具注册工具(ex["注册"], "echo", 级公开, 处理回显)
  设 res 为 执行工具(ex, "echo", "public", "c", {"x":"world"})
  打印("态=" + res["状态"])
  打印("果=" + 转字符串(res["结果"]))
''')
    assert_success(r)
    out_contains(r, "态=ok")
    out_contains(r, "果=got:world")


def test_执行工具_权限拒绝():
    r = run_light_source('''
从 工具执行 导入 建执行器, 具注册工具, 执行工具, 级私有
''' + _HELPERS + '''
段落 主程序:
  设 ex 为 建执行器()
  具注册工具(ex["注册"], "priv", 级私有, 处理回显)
  设 res 为 执行工具(ex, "priv", "public", "c", {"x":"w"})
  打印("态=" + res["状态"])
''')
    assert_success(r)
    out_contains(r, "态=permission_denied")


def test_执行工具_处理失败():
    r = run_light_source('''
从 工具执行 导入 建执行器, 具注册工具, 执行工具, 级公开
''' + _HELPERS + '''
段落 主程序:
  设 ex 为 建执行器()
  具注册工具(ex["注册"], "boom", 级公开, 处理爆炸)
  设 res 为 执行工具(ex, "boom", "public", "c", {})
  打印("态=" + res["状态"])
''')
    assert_success(r)
    out_contains(r, "态=failed")


def test_具造预决_与allow带理由报错():
    r = run_light_source('''
从 工具执行 导入 具造预决, 决放行, 决拒绝, 决询问
段落 主程序:
  设 a 为 具造预决(决放行)
  设 d 为 具造预决(决拒绝, "危险")
  打印("A=" + a["种类"])
  打印("D=" + d["种类"])
  打印("R=" + d["理由"])
''')
    assert_success(r)
    out_contains(r, "A=allow")
    out_contains(r, "D=deny")
    out_contains(r, "R=危险")


def test_具造预决_allow带理由报错():
    r = run_light_source('''
从 工具执行 导入 具造预决, 决放行
段落 主程序:
  设 x 为 具造预决(决放行, "不该有理由")
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "ALLOW_WITH_REASON")


def test_具询问收敛_ask审批():
    r = run_light_source('''
从 工具执行 导入 具造预决, 具询问收敛, 决询问, 批准放行, 批准拒绝
段落 主程序:
  设 q 为 具造预决(决询问, "需要审批")
  设 r1 为 具询问收敛(q, 批准放行, 真)
  设 r2 为 具询问收敛(q, 批准拒绝, 真)
  设 r3 为 具询问收敛(q, 空, 假)
  打印("A=" + r1["种类"])
  打印("D=" + r2["种类"])
  打印("无通道=" + r3["种类"])
''')
    assert_success(r)
    out_contains(r, "A=allow")
    out_contains(r, "D=deny")
    out_contains(r, "无通道=deny")


def test_具守卫裁决_否决优先():
    r = run_light_source('''
从 工具执行 导入 具造预决, 具守卫裁决, 决放行
段落 主程序:
  设 ok 为 具造预决(决放行)
  设 r 为 具守卫裁决("被守卫否决", ok)
  打印("类=" + r["种类"])
  打印("由=" + r["理由"])
''')
    assert_success(r)
    out_contains(r, "类=deny")
    out_contains(r, "由=被守卫否决")

# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_解析profile目录_合法():
    r = run_light_source('''
从 启动配置 导入 解析profile目录
段落 主程序:
  设 p 为 解析profile目录("myprof", "/home/u")
  打印("路径=" + p)
''')
    assert_success(r)
    out_contains(r, "profiles")
    out_contains(r, "myprof")


def test_解析profile目录_空名报错():
    r = run_light_source('''
从 启动配置 导入 解析profile目录
段落 主程序:
  设 p 为 解析profile目录("", "/home/u")
  打印("不应到达")
''')
    assert_failure(r)


def test_解析profile目录_斜杠报错():
    r = run_light_source('''
从 启动配置 导入 解析profile目录
段落 主程序:
  设 p 为 解析profile目录("a/b", "/home/u")
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "invalid profile name")


def test_解析profile目录_node_modules报错():
    r = run_light_source('''
从 启动配置 导入 解析profile目录
段落 主程序:
  设 p 为 解析profile目录("node_modules", "/home/u")
  打印("不应到达")
''')
    assert_failure(r)


def test_合并配置_浅覆盖():
    r = run_light_source('''
从 启动配置 导入 合并配置
段落 主程序:
  设 entry 为 {"id":"x", "a":1}
  设 patch 为 {"config":{"a":9, "b":2}}
  合并配置(entry, patch)
  打印("A=" + 转字符串(entry["a"]))
  打印("B=" + 转字符串(entry["b"]))
''')
    assert_success(r)
    out_contains(r, "A=9")
    out_contains(r, "B=2")


def test_合并配置_非对象报错():
    r = run_light_source('''
从 启动配置 导入 合并配置
段落 主程序:
  设 entry 为 {"id":"x"}
  设 patch 为 {"config":"notobj"}
  合并配置(entry, patch)
  打印("不应到达")
''')
    assert_failure(r)


def test_应用补丁_新建entry():
    r = run_light_source('''
从 启动配置 导入 应用补丁
段落 主程序:
  设 顺序表 为 []
  设 索引表 为 {}
  应用补丁({"id":"x", "config":{"k":1}}, 顺序表, 索引表)
  打印("数=" + 转字符串(长度(顺序表)))
  打印("K=" + 转字符串(顺序表[0]["k"]))
''')
    assert_success(r)
    out_contains(r, "数=1")
    out_contains(r, "K=1")


def test_应用补丁_同id覆盖():
    r = run_light_source('''
从 启动配置 导入 应用补丁
段落 主程序:
  设 顺序表 为 []
  设 索引表 为 {}
  应用补丁({"id":"x", "config":{"k":1}}, 顺序表, 索引表)
  应用补丁({"id":"x", "config":{"k":2}}, 顺序表, 索引表)
  打印("数=" + 转字符串(长度(顺序表)))
  打印("K=" + 转字符串(顺序表[0]["k"]))
''')
    assert_success(r)
    out_contains(r, "数=1")
    out_contains(r, "K=2")


def test_应用补丁_insert子条目():
    r = run_light_source('''
从 启动配置 导入 应用补丁
从 JSON 导入 序列化JSON
段落 主程序:
  设 顺序表 为 []
  设 索引表 为 {}
  应用补丁({"id":"base", "config":{"a":1}}, 顺序表, 索引表)
  设 补丁 为 {"id":"base", "insert":[{"id":"child", "config":{"b":2}}]}
  应用补丁(补丁, 顺序表, 索引表)
  打印("数=" + 转字符串(长度(顺序表)))
  打印("ID=" + 顺序表[1]["id"])
''')
    assert_success(r)
    out_contains(r, "数=2")
    out_contains(r, "ID=child")


def test_组合条目_多层叠加():
    r = run_light_source('''
从 启动配置 导入 组合条目
段落 主程序:
  设 layers 为 [
    [{"id":"base", "config":{"a":1}}],
    [{"id":"base", "config":{"b":2}}, {"id":"extra", "config":{"c":3}}]
  ]
  设 表 为 组合条目(layers)
  打印("数=" + 转字符串(长度(表)))
  打印("A=" + 转字符串(表[0]["a"]))
  打印("B=" + 转字符串(表[0]["b"]))
''')
    assert_success(r)
    out_contains(r, "数=2")
    out_contains(r, "A=1")
    out_contains(r, "B=2")


def test_解析启动参数_基本profile():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
段落 主程序:
  设 o 为 解析启动参数(["--profile", "tui"])
  打印("模式=" + o["模式"])
  打印("档=" + o["profile"])
''')
    assert_success(r)
    out_contains(r, "模式=profile")
    out_contains(r, "档=tui")


def test_解析启动参数_缺profile报错():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
段落 主程序:
  设 o 为 解析启动参数([])
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "--profile <name> is required")


def test_解析启动参数_多patch收集():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
从 JSON 导入 序列化JSON
段落 主程序:
  设 o 为 解析启动参数(["--profile", "p", "--patch", "a", "--patch", "b"])
  打印("补丁=" + 序列化JSON(o["patches"]))
''')
    assert_success(r)
    out_contains(r, '"a"')
    out_contains(r, '"b"')


def test_解析启动参数_innerargs透传():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
从 JSON 导入 序列化JSON
段落 主程序:
  设 o 为 解析启动参数(["--profile", "p", "run", "--verbose"])
  打印("参数=" + 序列化JSON(o["args"]))
''')
    assert_success(r)
    out_contains(r, "run")
    out_contains(r, "--verbose")


def test_解析启动参数_version短路():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
段落 主程序:
  设 o 为 解析启动参数(["-V"])
  打印("模式=" + o["模式"])
''')
    assert_success(r)
    out_contains(r, "模式=version")


def test_解析启动参数_dump_config():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
段落 主程序:
  设 o 为 解析启动参数(["--dump-config", "--profile", "p"])
  打印("模式=" + o["模式"])
''')
    assert_success(r)
    out_contains(r, "模式=dump-config")


def test_解析启动参数_dump互斥报错():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
段落 主程序:
  设 o 为 解析启动参数(["--dump-config", "--dump-default-config", "--profile", "p"])
  打印("不应到达")
''')
    assert_failure(r)
    out_contains(r, "mutually exclusive")


def test_解析启动参数_plugin子命令():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
段落 主程序:
  设 o 为 解析启动参数(["plugin", "--profile", "p", "add", "pkg"])
  打印("模式=" + o["模式"])
  打印("档=" + o["profile"])
''')
    assert_success(r)
    out_contains(r, "模式=plugin")
    out_contains(r, "档=p")


def test_解析启动参数_plugin缺profile报错():
    r = run_light_source('''
从 启动配置 导入 解析启动参数
段落 主程序:
  设 o 为 解析启动参数(["plugin", "add", "pkg"])
  打印("不应到达")
''')
    assert_failure(r)


def test_已发布模板_含acp():
    r = run_light_source('''
从 启动配置 导入 已发布模板
段落 主程序:
  设 b 为 已发布模板["acp"]["bundles"]
  打印("首=" + 列表获取(b, 0))
''')
    assert_success(r)
    out_contains(r, "首=@deepseek-ai/dsh-base")

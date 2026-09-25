# -*- coding: utf-8 -*-
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains, out_not_contains,
)


def test_默认预设_按类别():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("预设=" + mgr.当前预设())
''')
    assert_success(r)
    out_contains(r, "预设=按类别")


def test_环境变量_全放行预设():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("预设=" + mgr.当前预设())
''', env={"HARNESS_PERMISSION_MODE": "全放行"})
    assert_success(r)
    out_contains(r, "预设=全放行")


def test_全放行预设_检查恒放行():
    r = run_light_source('''
从 权限 导入 权限管理器, 预设全放行
段落 主程序:
  设 mgr 为 新建 权限管理器()
  mgr.设置预设(预设全放行)
  打印("A=" + mgr.检查("写文件", {"路径":"x"}))
  打印("B=" + mgr.检查("bash", {"command":"rm -rf /"}))
''')
    assert_success(r)
    out_contains(r, "A=放行")
    out_contains(r, "B=放行")


def test_全拒绝预设_检查恒拒绝():
    r = run_light_source('''
从 权限 导入 权限管理器, 预设全拒绝
段落 主程序:
  设 mgr 为 新建 权限管理器()
  mgr.设置预设(预设全拒绝)
  打印("A=" + mgr.检查("读文件", {"路径":"x"}))
  打印("B=" + mgr.检查("ls", {}))
''')
    assert_success(r)
    out_contains(r, "A=拒绝")
    out_contains(r, "B=拒绝")


def test_按类别_读文件放行():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类工具("读文件", {"路径":"x"}))
  打印("B=" + mgr.分类工具("搜索文件", {"模式":"x"}))
  打印("C=" + mgr.分类工具("ls", {}))
''')
    assert_success(r)
    out_contains(r, "A=放行")
    out_contains(r, "B=放行")
    out_contains(r, "C=放行")


def test_按类别_写文件审批():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类工具("写文件", {"路径":"x"}))
  打印("B=" + mgr.分类工具("删除文件", {"路径":"x"}))
  打印("C=" + mgr.分类工具("未知工具", {}))
''')
    assert_success(r)
    out_contains(r, "A=审批")
    out_contains(r, "B=审批")
    out_contains(r, "C=审批")


def test_bash_只读命令放行():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类bash命令("ls -la"))
  打印("B=" + mgr.分类bash命令("grep foo bar"))
  打印("C=" + mgr.分类bash命令("pwd"))
''')
    assert_success(r)
    out_contains(r, "A=放行")
    out_contains(r, "B=放行")
    out_contains(r, "C=放行")


def test_bash_修改与网络命令审批():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类bash命令("rm a.txt"))
  打印("B=" + mgr.分类bash命令("mkdir d"))
  打印("C=" + mgr.分类bash命令("curl http://x"))
  打印("D=" + mgr.分类bash命令("wget http://y"))
''')
    assert_success(r)
    out_contains(r, "A=审批")
    out_contains(r, "B=审批")
    out_contains(r, "C=审批")
    out_contains(r, "D=审批")


def test_bash_危险命令拒绝():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类bash命令("rm -rf /"))
  打印("B=" + mgr.分类bash命令("mkfs.ext4 /dev/sda1"))
  打印("C=" + mgr.分类bash命令("shutdown -h now"))
''')
    assert_success(r)
    out_contains(r, "A=拒绝")
    out_contains(r, "B=拒绝")
    out_contains(r, "C=拒绝")


def test_bash_git子命令分级():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类bash命令("git status"))
  打印("B=" + mgr.分类bash命令("git log --oneline"))
  打印("C=" + mgr.分类bash命令("git commit -m x"))
  打印("D=" + mgr.分类bash命令("git push origin main"))
''')
    assert_success(r)
    out_contains(r, "A=放行")
    out_contains(r, "B=放行")
    out_contains(r, "C=审批")
    out_contains(r, "D=审批")


def test_bash_空命令放行():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类bash命令(""))
  打印("B=" + mgr.分类bash命令(空))
''')
    assert_success(r)
    out_contains(r, "A=放行")
    out_contains(r, "B=放行")


def test_是危险命令_正反():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + 转字符串(mgr.是危险命令("rm -rf /")))
  打印("B=" + 转字符串(mgr.是危险命令("ls")))
  打印("C=" + 转字符串(mgr.是危险命令("")))
  打印("D=" + 转字符串(mgr.是危险命令(空)))
''')
    assert_success(r)
    out_contains(r, "A=真")
    out_contains(r, "B=假")
    out_contains(r, "C=假")
    out_contains(r, "D=假")


def test_工具bash_按参数命令分类():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类工具("bash", {"command":"cat f.txt"}))
  打印("B=" + mgr.分类工具("sh", {"cmd":"rm x"}))
  打印("C=" + mgr.分类工具("bash", {"command":"rm -rf /"}))
''')
    assert_success(r)
    out_contains(r, "A=放行")
    out_contains(r, "B=审批")
    out_contains(r, "C=拒绝")


def test_自定义预设_自定义表覆盖():
    r = run_light_source('''
从 权限 导入 权限管理器, 预设自定义, 分类放行, 分类拒绝
段落 主程序:
  设 mgr 为 新建 权限管理器()
  mgr.设置预设(预设自定义)
  mgr.设置自定义("内部工具", 分类放行)
  mgr.设置自定义("危险工具", 分类拒绝)
  打印("A=" + mgr.检查("内部工具", {}))
  打印("B=" + mgr.检查("危险工具", {}))
  打印("C=" + mgr.检查("读文件", {"路径":"x"}))
''')
    assert_success(r)
    out_contains(r, "A=放行")
    out_contains(r, "B=拒绝")
    out_contains(r, "C=放行")


def test_空工具名_审批():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("A=" + mgr.分类工具("", {}))
  打印("B=" + mgr.分类工具(空, {}))
''')
    assert_success(r)
    out_contains(r, "A=审批")
    out_contains(r, "B=审批")


def test_追加危险模式_生效():
    r = run_light_source('''
从 权限 导入 权限管理器
段落 主程序:
  设 mgr 为 新建 权限管理器()
  打印("前=" + 转字符串(mgr.是危险命令("我的危险串")))
  mgr.追加危险模式("我的危险串")
  打印("后=" + 转字符串(mgr.是危险命令("包含我的危险串")))
''')
    assert_success(r)
    out_contains(r, "前=假")
    out_contains(r, "后=真")

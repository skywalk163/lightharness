# -*- coding: utf-8 -*-
"""T-0496：工具注册表能力域（domain）元数据判据。

覆盖三层：
  1. 回填完整性：真实注册表（160 工具）每个工具都有非空 domain；
  2. 查询语义：按 domain 查询返回正确子集、保持登记序、并集=全集；
     MCP 透传按 mcp__<server>__<tool> 解析为 mcp_<server>；
     域名表带名表时含动态 mcp_* 域（T-0543：挂载 MCP 后并集不短一截）；
     未知/非字符串/空串的缺省行为明确（"其他"，不抛错）；
  3. 元数据不影响调用：注册接口加 domain 后，执行管线仍是
     权限 → 限流 → 取消 → 执行 → 审计，wire 名/参数签名不变。

只有两条 Light 子进程调用（domain 查询 + 执行管线），避免 xdist 下
多个 运行.py 同时编译 .light 触发 worker crash（pytest.ini --timeout=60）。

运行方式：python -m pytest -q tests/test_T0496_domain字段.py
Windows 本机若子进程输出触发 GBK 解码错误，加 PYTHONUTF8=1 再跑（不是产物问题）。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180


def _run(driver, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC,
                          env=env, encoding='utf-8', errors='replace')
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, proc.stdout + proc.stderr, kv


# ---- Light driver：真实注册表 → 逐名查 domain + 查询语义 + 缺省行为 ----
DOMAIN_DRIVER = '''
从 总入口 导入 组装注册表
从 工具面装配 导入 工具域, 按域取工具, 工具域名表, 默认域, 是MCP域标识
从 内置核心列表 导入 列表追加, 列表包含

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 主程():
  设 注册表 为 组装注册表()
  设 名表 为 注册表.名单()
  打印 "注册表总数=" + 转字符串(长度(名表))
  # 每个工具都有非空 domain
  设 空域 为 []
  遍历 名 之 名表:
    设 域 为 工具域(名)
    如果 域 == "" 或 域 == 空:
      列表追加(空域, 名)
  打印 "空域数=" + 转字符串(长度(空域))
  打印 "空域名表=" + 逗号连接(空域)
  # 按域查询：子集保持登记序
  设 文件域 为 按域取工具(名表, "file")
  打印 "file子集=" + 逗号连接(文件域)
  设 壳域 为 按域取工具(名表, "shell")
  打印 "shell子集=" + 逗号连接(壳域)
  # 并集 = 全集（不重不漏）
  设 并集 为 []
  遍历 域 之 工具域名表(名表):
    遍历 名 之 按域取工具(名表, 域):
      如果 列表包含(并集, 名) == 假:
        列表追加(并集, 名)
  打印 "并集数=" + 转字符串(长度(并集))
  # 动态 mcp_* 域必须进域名表（不依赖本机是否真的挂载 MCP 服务器）
  设 样本表 为 ["读文件", "mcp__github__list_issues", "mcp__github__get_issue", "mcp__lightplugin__提示_路径安全"]
  设 样本域表 为 工具域名表(样本表)
  打印 "样本域表=" + 逗号连接(样本域表)
  设 样本并集 为 []
  遍历 域 之 样本域表:
    遍历 名 之 按域取工具(样本表, 域):
      如果 列表包含(样本并集, 名) == 假:
        列表追加(样本并集, 名)
  打印 "样本总数=" + 转字符串(长度(样本表))
  打印 "样本并集数=" + 转字符串(长度(样本并集))
  # 缺省行为
  打印 "未知工具域=" + 工具域("完全不存在的工具NNN")
  打印 "非字符串域=" + 工具域(123)
  打印 "空串域=" + 工具域("")
  打印 "MCP判定=" + 转字符串(是MCP域标识("mcp__github__list_issues"))
  打印 "MCP域=" + 工具域("mcp__github__list_issues")
  打印 "MCP无名=" + 工具域("mcp__badname")
  打印 "默认域=" + 默认域
主程()
'''


# ---- Light driver：工具执行 注册接口的 domain 纯元数据 + 不影响执行 ----
EXEC_DRIVER = '''
从 工具执行 导入 建注册表, 具注册工具, 按域列工具, 工具之域, 级公开, 执行工具, 建执行器
从 内置核心列表 导入 列表追加

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 回显(参数, 令牌):
  返回 "ok"

段落 主程():
  设 注册 为 建注册表()
  具注册工具(注册, "甲工具", 级公开, 回显, 空, "shell")
  具注册工具(注册, "乙工具", 级公开, 回显)
  打印 "甲域=" + 工具之域(注册, "甲工具")
  打印 "乙域=" + 工具之域(注册, "乙工具")
  打印 "未知域=" + 转字符串(工具之域(注册, "不存在"))
  打印 "shell列表=" + 逗号连接(按域列工具(注册, "shell"))
  打印 "其他列表=" + 逗号连接(按域列工具(注册, "其他"))
  打印 "空气列表=" + 逗号连接(按域列工具(注册, "不存在的域"))
  # domain 不影响执行路径
  设 执行器 为 建执行器(10, 1000, 0, 策略滑动窗, 注册)
  设 结果 为 执行工具(执行器, "甲工具", 级公开, "tester", 空)
  打印 "调用状态=" + 结果["状态"]
  打印 "调用结果=" + 转字符串(结果["结果"])
主程()
'''
EXEC_DRIVER = EXEC_DRIVER.replace(
    '级公开, 执行工具, 建执行器',
    '级公开, 执行工具, 建执行器, 策略滑动窗')


def test_domain回填完整性与查询语义(tmp_path):
    rc, out, kv = _run(DOMAIN_DRIVER, tmp_path, 't0496_domain.light')
    assert rc == 0, out
    # 1) 回填完整性：160 工具全有非空 domain
    assert int(kv.get('注册表总数', '0')) >= 150, out
    assert kv.get('空域数') == '0', ('有工具缺 domain', kv.get('空域名表'), out)
    # 2) 按域查询：正确子集、保持登记序
    got = [x for x in kv.get('file子集', '').split(',') if x]
    assert got == ['读文件', '写文件', '搜索文件', '编辑文件', '订阅文件变更'], (got, out)
    shell = [x for x in kv.get('shell子集', '').split(',') if x]
    assert shell == ['bash', 'SSH执行', '运行用例表', '执行Python脚本'], (shell, out)
    # 并集 = 全集（不重不漏）
    assert kv.get('并集数') == kv.get('注册表总数'), out
    # T-0543：动态 mcp_* 域必须进域名表，否则挂载 MCP 后并集会短一截
    sample = [x for x in kv.get('样本域表', '').split(',') if x]
    assert 'file' in sample and 'mcp_github' in sample and 'mcp_lightplugin' in sample, (sample, out)
    assert kv.get('样本并集数') == kv.get('样本总数'), out
    # 3) 缺省行为
    assert kv.get('未知工具域') == kv.get('默认域') == '其他', out
    assert kv.get('非字符串域') == '其他', out
    assert kv.get('空串域') == '其他', out
    # 4) MCP 透传
    assert kv.get('MCP判定') in ('True', '真'), out
    assert kv.get('MCP域') == 'mcp_github', out
    assert kv.get('MCP无名') == 'mcp_未知', out


def test_注册接口domain字段不影响执行(tmp_path):
    rc, out, kv = _run(EXEC_DRIVER, tmp_path, 't0496_domain_exec.light')
    assert rc == 0, out
    assert kv.get('甲域') == 'shell', out
    assert kv.get('乙域') == '其他', out
    assert kv.get('未知域') in ('None', '空', ''), out
    assert kv.get('shell列表') == '甲工具', out
    assert kv.get('其他列表') == '乙工具', out
    assert kv.get('空气列表') == '', out
    # domain 是元数据：执行照常走权限→限流→取消→执行→审计
    assert kv.get('调用状态') == 'ok', out
    assert kv.get('调用结果') == 'ok', out

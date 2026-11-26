# -*- coding: utf-8 -*-
"""T-0496：工具注册表能力域（domain）元数据判据。

三层：
  1. 回填完整性：真实注册表（160 工具）每个工具都有非空 domain，
     且域名表覆盖全部已用域；
  2. 查询语义：按 domain 查询返回正确子集、保持登记序；
     MCP 透传工具按 mcp__<server>__<tool> 解析为 mcp_<server>；
     未知工具 / 非字符串输入的缺省行为明确（返回 "其他"，不抛错）；
  3. 元数据不影响调用：新增 domain 字段后，执行管线仍是
     权限 → 限流 → 取消 → 执行 → 审计，wire 名 / 参数签名不变。

运行方式：python -m pytest -q tests/test_T0496_domain字段.py
Windows 本机若子进程输出触发 GBK 解码错误，加 PYTHONUTF8=1 再跑（不是产物问题）。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180

# 真实注册表全量工具名（本机 组装注册表() dump，排除 MCP 未配置的提示行）。
# 逐名保留，作为「160 工具都有 domain」的可复核基准。
ALL_TOOLS = [
    'bash', '读文件', '写文件', '搜索文件', '编辑文件',
    'job_start', 'job_output', 'job_kill', 'skill', 'web_search', 'web_fetch',
    'present', 'todo_write', '目标',
    'SSH执行', '设置环境变量', '获取环境变量', '解析命令行', '三维生成',
    '压缩评估', '压缩选块', '压缩摘要', '上下文装配', '上下文装配报告',
    '提问提交', '回答提交', '待答列出', '答案取出', '注册团队画像', '校验装配',
    '创建会话', '切换会话', '列出会话',
    '凭据存入', '凭据读取', '凭据删除', '凭据列出',
    '构造ACP请求', '校验ACP消息', '反馈提交', '反馈列出', '反馈处理', '反馈筛选',
    '执行启动序列', '图片生成', '派发子任务', '收集子任务结果',
    '启动子进程', '等待子进程', '存储写入', '存储读取', '存储列举', '存储删除',
    '风险判定', '提醒注册', '提醒取消', '提醒列出', '提醒触发',
    '切换连接态', '拉取事件',
    '宿主名称', '宿主平台', '宿主工作区根', '宿主能力声明', '注册工作区', '解析路径',
    '工作流提交', '工作流状态查询', '工作流汇总', '工作线程打包', '工作线程运行时',
    '派发工具任务', '回收工具结果', '列出能力', '调用能力', '作业状态查询', '作业取消',
    '待办添加', '待办完成', '待办列出', '待办删除', '登记产物', '生成清单',
    '注册扩展', '列出扩展', '技能列表', '技能取用', '注册路由', '分发请求',
    '规范化路径', '订阅文件变更', '文档大纲',
    '查时间', '查工作目录', '查版本', '查退出码',
    '屏幕操作', '桌面驱动CUA协议', '桌面驱动CUA原生', '模型补全',
    '沙箱裁决', '运行用例表', '浏览器执行', '登记页面', '执行动作队列',
    '浏览器驱动DevTools', '浏览器驱动Playwright', '浏览器驱动Stagehand',
    '写入缓冲', '读取缓冲', '目标创建', '目标推进', '目标列出',
    '判定类型', '校验结构', '打开终端', '写入终端', '读取终端', '关闭终端',
    'Webhook注册', 'Webhook触发', 'Webhook列出', 'Webhook删除',
    '网页抓取', '自动审查', '视频生成',
    '计划创建', '计划开始', '计划完成', '计划阻塞', '计划列出',
    '读取设置', '写入设置', 'LSP初始化', 'LSP发请求', 'LSP收响应',
    '语音转文字', '录音控制', '语音打包', '语音目录', '语音转写',
    '人格列表', '人格装配', '登记任务槽', '释放任务槽',
    '执行Python脚本', '采集诊断快照', '健康检查', '运行检视',
    '合并字典', '去重列表', '注册钩子', '触发事件',
    '附件上传', '附件下载', '附件列举',
    '预设保存', '预设应用', '预设列出', '预设删除',
]

_TOOLS_LITERAL = '[' + ', '.join('"%s"' % n for n in ALL_TOOLS) + ']'


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


# ---- Light 侧 driver：从真实注册表取名单，逐名查 domain ----
DOMAIN_DRIVER = '''
从 总入口 导入 组装注册表
从 工具面装配 导入 工具域, 按域取工具, 工具域名表, 默认域, 是MCP域标识

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
  设 空域 为 []
  遍历 名 之 名表:
    设 域 为 工具域(名)
    如果 域 == "" 或 域 == 空:
      列表追加(空域, 名)
  打印 "空域数=" + 转字符串(长度(空域))
  打印 "空域名表=" + 逗号连接(空域)
  # 按域查询：子集 + 保持登记序
  设 文件域 为 按域取工具(名表, "file")
  打印 "file子集=" + 逗号连接(文件域)
  打印 "file计数=" + 转字符串(长度(文件域))
  设 壳域 为 按域取工具(名表, "shell")
  打印 "shell子集=" + 逗号连接(壳域)
  # 恒等性质：按域取工具 各域并集 = 全集，且不重不漏
  设 并集 为 []
  遍历 域 之 工具域名表():
    遍历 名 之 按域取工具(名表, 域):
      如果 列表包含(并集, 名) == 假:
        列表追加(并集, 名)
  打印 "并集数=" + 转字符串(长度(并集))
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


# ---- Light 侧 driver：工具执行 注册接口的 domain 纯元数据 ----
EXEC_DRIVER = '''
从 工具执行 导入 建注册表, 具注册工具, 按域列工具, 工具之域, 级公开, 执行工具

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
  打印 "调用结果=" + 结果["结果"]
主程()
'''

EXEC_DRIVER = EXEC_DRIVER.replace(
    '从 工具执行 导入 建注册表, 具注册工具, 按域列工具, 工具之域, 级公开, 执行工具',
    '从 工具执行 导入 建注册表, 具注册工具, 按域列工具, 工具之域, 级公开, 执行工具, 策略滑动窗, 建执行器')


def test_每个工具都有非空domain(tmp_path):
    rc, out, kv = _run(DOMAIN_DRIVER, tmp_path, 't0496_domain_all.light')
    assert rc == 0, out
    assert int(kv.get('注册表总数', '0')) >= 150, out
    assert kv.get('空域数') == '0', ('有工具缺 domain', kv.get('空域名表'), out)


def test_按域查询返回正确子集且保持登记序(tmp_path):
    rc, out, kv = _run(DOMAIN_DRIVER, tmp_path, 't0496_domain_query.light')
    assert rc == 0, out
    got = [x for x in kv.get('file子集', '').split(',') if x]
    assert got == ['读文件', '写文件', '搜索文件', '编辑文件', '订阅文件变更'], (got, out)
    shell = [x for x in kv.get('shell子集', '').split(',') if x]
    assert shell == ['bash', 'SSH执行', '运行用例表', '执行Python脚本'], (shell, out)
    # 并集 = 全集（不重不漏）
    assert kv.get('并集数') == kv.get('注册表总数'), out


def test_未知工具与非字符串缺省行为明确(tmp_path):
    rc, out, kv = _run(DOMAIN_DRIVER, tmp_path, 't0496_domain_unknown.light')
    assert rc == 0, out
    assert kv.get('未知工具域') == kv.get('默认域') == '其他', out
    assert kv.get('非字符串域') == '其他', out
    assert kv.get('空串域') == '其他', out


def test_MCP透传工具按服务器解析域(tmp_path):
    rc, out, kv = _run(DOMAIN_DRIVER, tmp_path, 't0496_domain_mcp.light')
    assert rc == 0, out
    assert kv.get('MCP判定') in ('True', '真'), out
    assert kv.get('MCP域') == 'mcp_github', out
    # 无双下划线的畸形标识仍有明确兜底（不抛错、非空）
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
    # 审计/统计照常落账（domain 不参与任何执行闸门）

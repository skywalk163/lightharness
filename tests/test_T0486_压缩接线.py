# -*- coding: utf-8 -*-
"""T-0486 压缩接线判据：模型摘要注入 / 失败回退 / 单次调用 / 事件不污染 / 来源标记。"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 120

_POLLUTING_ENV = (
    'HARNESS_ROOT', 'HARNESS_CWD',
    'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_COMPACTION_THRESHOLD_RATIO',
    'HARNESS_COMPACTION_KEEP_COUNT', 'HARNESS_COMPACTION_THRESHOLD',
    'HARNESS_COMPACTION_KEEP_ROUNDS', 'HARNESS_COMPACTION_MODEL_SUMMARY',
)


def _find_repo(env_name, dir_name):
    cands = []
    explicit = os.environ.get(env_name, '')
    if explicit:
        cands.append(explicit)
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        cands.append(os.path.join(here, dir_name))
        cands.append(os.path.join(here, 'duan-light-merge', dir_name))
    cands.append('/home/skywalk/dswork/' + dir_name)
    for c in cands:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _run(src: str, tmp_path, extra_env=None):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in _POLLUTING_ENV}
    for key, repo in (('LIGHTPLUGIN', 'lightplugin'), ('LIGHT_MERGE', 'light-merge')):
        found = _find_repo(key, repo)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    if extra_env:
        env.update(extra_env)
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(tmp_path), env=env,
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return p.returncode, p.stdout + p.stderr, kv


BOOT = """
从 会话 导入 新建会话
从 消息 导入 造用户消息, 造文本块
从 压缩 导入 压缩到最近, 压缩造摘要, 清压缩摘要来源信息, 取消息文本
从 压缩摘要器 导入 造摘要指令, 八段标题
从 代理 导入 造模型摘要器
从 字符串处理 导入 长度
"""

GOOD_CLIENT = """
类 假客户端:
  属性 调用次数 等于 0
  属性 最后消息数 等于 0
  属性 最后工具数 等于 -1
  属性 最后末条 等于 ""
  属性 最后选项 等于 空
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    己.调用次数 为 己.调用次数 + 1
    己.最后消息数 为 长度(消息表)
    己.最后工具数 为 长度(工具表)
    己.最后选项 为 选项表
    设 末条 为 消息表[长度(消息表) - 1]
    己.最后末条 为 末条["content"][0]["text"]
    返回 [["type": "text", "text": 造摘要指令()]]
"""

THROW_CLIENT = """
类 坏客户端:
  属性 调用次数 等于 0
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    己.调用次数 为 己.调用次数 + 1
    抛出 新建 错误("模型不可用")
"""

INVALID_CLIENT = """
类 无效客户端:
  属性 调用次数 等于 0
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    己.调用次数 为 己.调用次数 + 1
    返回 [["type": "text", "text": "这不是合法摘要"]]
"""

MK_SESSION = """
设 会话对象 为 新建会话("{name}", ".")
设 i 为 0
当 i < {count}:
  会话对象.记录事件("user/message", 造用户消息([造文本块("{text}" + 转字符串(i))]))
  设 i 为 i + 1
"""

# 摘要来源/正文 读取器（事件顶层 摘要来源 由 落摘要来源到事件 写入）
DUMP_SOURCE = """
设 来源 为 "无"
设 段数 为 -1
设 有检查点 为 假
设 检查点正文 为 ""
遍历 记录 之 会话对象.汇集全部事件():
  如果 记录.包含("来源事件序号"):
    有检查点 为 真
    设 数据 为 记录["数据"]
    遍历 块 之 数据["content"]:
      检查点正文 为 检查点正文 + 块["text"]
  如果 记录.包含("摘要来源"):
    来源 为 记录["摘要来源"]
    段数 为 记录["摘要段数"]
打印 "有检查点=" + 转字符串(有检查点)
打印 "来源=" + 来源
打印 "段数=" + 转字符串(段数)
打印 "检查点正文含八段=" + 转字符串(检查点正文.包含("## 当前工作"))
打印 "检查点正文含折叠=" + 转字符串(检查点正文.包含("折叠内容"))
"""


def test_成功路径模型摘要落事件(tmp_path):
    src = (BOOT + GOOD_CLIENT + MK_SESSION.format(name='t486ok', count=6, text='折叠内容') + """
设 客户端对象 为 新建 假客户端()
设 选项表 为 ["k": "v"]
设 摘要器 为 造模型摘要器(客户端对象, 会话对象, 选项表)
清压缩摘要来源信息()
设 前事件数 为 长度(会话对象.汇集全部事件())
压缩到最近(会话对象, 2, 摘要器)
设 后事件数 为 长度(会话对象.汇集全部事件())
""" + DUMP_SOURCE + """
打印 "调用次数=" + 转字符串(客户端对象.调用次数)
打印 "请求消息数=" + 转字符串(客户端对象.最后消息数)
打印 "工具数=" + 转字符串(客户端对象.最后工具数)
打印 "选项透传=" + 转字符串(客户端对象.最后选项.包含("k") 且 客户端对象.最后选项["k"] == "v")
打印 "事件数不变=" + 转字符串(前事件数 == 后事件数 - 1)
""")
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-2000:]
    assert kv['调用次数'] == '1', '压缩只触发一次摘要请求（不重试）'
    assert kv['工具数'] == '0', '摘要请求不许带工具 schema'
    assert kv['选项透传'] == 'True', '选项应透传给客户端'
    assert kv['请求消息数'] == '5', '4 条折叠消息 + 1 条摘要指令'
    assert kv['有检查点'] == 'True'
    assert kv['来源'] == 'model', '检查点事件应落 摘要来源=model'
    assert int(kv['段数']) == 4, '段数应为被折叠的旧消息数'
    assert kv['检查点正文含八段'] == 'True', '检查点应含八段标题正文'
    assert kv['检查点正文含折叠'] == 'False', '模型摘要不应回抄原始折叠内容'


def test_缺段与抛错回退确定性且单次调用(tmp_path):
    for bad_src, ctor, tag in ((INVALID_CLIENT, '无效客户端()', '缺段'), (THROW_CLIENT, '坏客户端()', '抛错')):
        src = (BOOT + bad_src + MK_SESSION.format(name='t486bad', count=5, text='回退内容') + """
设 客户端对象 为 新建 """ + ctor + """
设 摘要器 为 造模型摘要器(客户端对象, 会话对象, 空)
清压缩摘要来源信息()
设 直返 为 摘要器(会话对象, 3)
""" + DUMP_SOURCE + """
打印 "直返空=" + 转字符串(直返 == 空 或 长度(直返) == 0)
打印 "调用次数=" + 转字符串(客户端对象.调用次数)
""")
        rc, out, kv = _run(src, tmp_path)
        assert rc == 0, out[-2000:]
        assert kv['直返空'] == 'True', f'{tag}: 摘要器失败应返回空'
        assert kv['调用次数'] == '1', f'{tag}: 恰好一次调用，不重试'
        assert kv['有检查点'] == 'False', f'{tag}: 直接调用摘要器不应落检查点'
        assert kv['来源'] == '无', f'{tag}: 失败时不应落来源事件'


def test_压缩回退确定性落来源(tmp_path):
    src = (BOOT + THROW_CLIENT + MK_SESSION.format(name='t486fb', count=5, text='回退内容') + """
设 客户端对象 为 新建 坏客户端()
设 摘要器 为 造模型摘要器(客户端对象, 会话对象, 空)
清压缩摘要来源信息()
压缩到最近(会话对象, 2, 摘要器)
""" + DUMP_SOURCE + """
打印 "调用次数=" + 转字符串(客户端对象.调用次数)
""")
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-2000:]
    assert kv['调用次数'] == '1'
    assert kv['来源'] == 'deterministic', '失败回退应落 摘要来源=deterministic'
    assert kv['检查点正文含折叠'] == 'False' and kv['来源'] == 'deterministic'


def test_旧检查点合并(tmp_path):
    src = (BOOT + GOOD_CLIENT + """
设 会话对象 为 新建会话("t486old", ".")
设 i 为 0
当 i < 5:
  会话对象.记录事件("user/message", 造用户消息([造文本块("旧正文" + 转字符串(i))]))
  设 i 为 i + 1
压缩到最近(会话对象, 2)
设 客户端对象 为 新建 假客户端()
设 摘要器 为 造模型摘要器(客户端对象, 会话对象, 空)
清压缩摘要来源信息()
压缩到最近(会话对象, 1, 摘要器)
打印 "调用=" + 转字符串(客户端对象.调用次数)
打印 "先前=" + 转字符串(客户端对象.最后末条.包含("先前检查点"))
打印 "旧正文=" + 转字符串(客户端对象.最后末条.包含("旧正文"))
""")
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-2000:]
    assert kv['调用'] == '1'
    assert kv['先前'] == 'True', '指令应含先前检查点合并要求'
    assert kv['旧正文'] == 'True', '旧检查点正文应并入指令'


def test_代理构造默认注入与关闭(tmp_path):
    src = (BOOT + GOOD_CLIENT + """
从 代理 导入 代理循环
设 会话对象 为 新建会话("t486cfg", ".")
设 客户端对象 为 新建 假客户端()
设 cfg 为 ["上下文窗口": 32768, "阈值比例": 0.75, "保留条数": 10]
设 选项默认 为 ["压缩配置": cfg]
设 代理默认 为 新建 代理循环(会话对象, 客户端对象, 空, 选项默认)
设 有摘要器默认 为 代理默认.压缩管理器.摘要器 != 空
设 选项关 为 ["压缩配置": cfg, "模型摘要": 假]
设 代理关 为 新建 代理循环(会话对象, 客户端对象, 空, 选项关)
设 有摘要器关 为 代理关.压缩管理器.摘要器 != 空
设 自带 为 ["摘要器": 空]
设 选项自带 为 ["压缩配置": 自带]
设 代理自带 为 新建 代理循环(会话对象, 客户端对象, 空, 选项自带)
设 自带摘要器被保留 为 代理自带.压缩管理器.摘要器 == 空
打印 "默认=" + 转字符串(有摘要器默认)
打印 "关=" + 转字符串(有摘要器关)
打印 "自带=" + 转字符串(自带摘要器被保留)
""")
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-2000:]
    assert kv['默认'] == 'True', '默认应注入模型摘要器'
    assert kv['关'] == 'False', '模型摘要=假 不注入'
    assert kv['自带'] == 'True', '配置自带摘要器（即使是空）不覆盖'


def test_配置解析默认开与环境变量关(tmp_path):
    src = """
从 压缩E5 导入 压缩配置解析, 压缩配置
设 c 为 压缩配置解析()
打印 "默认=" + 转字符串(c["模型摘要"])
设 cfg 为 新建 压缩配置()
打印 "类默认=" + 转字符串(cfg.模型摘要)
"""
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-2000:]
    assert kv['默认'] == 'True'
    assert kv['类默认'] == 'True'

    rc, out, kv = _run(src, tmp_path, extra_env={'HARNESS_COMPACTION_MODEL_SUMMARY': '0'})
    assert rc == 0, out[-2000:]
    assert kv['默认'] == 'False', '环境变量=0 应关闭'

    src2 = """
从 会话 导入 新建会话
从 压缩E5 导入 压缩配置解析
从 代理 导入 代理循环
设 会话对象 为 新建会话("t486env", ".")
设 选项 为 ["压缩配置": ["上下文窗口": 32768, "阈值比例": 0.75, "保留条数": 10]]
设 代理对象 为 新建 代理循环(会话对象, 空, 空, 选项)
打印 "注入=" + 转字符串(代理对象.压缩管理器.摘要器 != 空)
"""
    rc, out, kv = _run(src2, tmp_path, extra_env={'HARNESS_COMPACTION_MODEL_SUMMARY': '0'})
    assert rc == 0, out[-2000:]
    assert kv['注入'] == 'False', '环境变量=0 时不应注入摘要器（0 次客户端调用）'

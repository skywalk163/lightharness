# -*- coding: utf-8 -*-
"""T-0395 会话级工作目录（后端）判据。

每个用例起一个独立 Light 子进程，走真实的 Web服务端 / 会话存储 / 路由处理器。
旧实现下关键用例必红：
  - 旧 `取会话` 没有请求目录入参，`POST /api/sessions` 不认 工作目录；
  - 旧 `会话库.新建会话` 只收标题，索引里没有会话 cwd；
  - 旧 `GET /api/sessions/:id` 详情没有 工作目录 键。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 120


def _lp(p) -> str:
    return str(p).replace('\\', '/')


def _run(src: str, tmp_path, cwd=None):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(cwd or tmp_path), env=env,
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return p.returncode, p.stdout + p.stderr, kv


def _same(a: str, b: str) -> bool:
    norm = lambda s: os.path.normcase(os.path.normpath(s.strip()))
    return norm(a) == norm(b)


BOOT = '''
从 web服务器 导入 Web服务端
从 会话存储 导入 会话存储
从 持久化 导入 读入会话
从 工作目录 导入 解析工作目录, 断言可用
从 工具_路径安全 导入 取根目录, 解析安全路径
从 文件系统 导入 创建目录, 写入文件, 路径连接
从 字符串处理 导入 编码
从 JSON 导入 解析JSON, 序列化JSON
从 内置核心字典 导入 字典获取
从 认证 导入 初始化认证
'''


def _new_service(root):
    return f'''
初始化认证()
设 根 为 "{_lp(root)}"
设 库 为 新建 会话存储(路径连接(根, "sessions"))
设 服务 为 新建 Web服务端()
服务.设置会话库(库)
'''


def _body(title, cwd_expr=None):
    if cwd_expr is None:
        return f'序列化JSON(["标题": "{title}"])'
    return f'序列化JSON(["标题": "{title}", "工作目录": {cwd_expr}])'


# --------------------------------------------------------------------------- #
# 1. 两条会话各自不同目录并发存在，路径安全各按各根（反证）
# --------------------------------------------------------------------------- #
def test_两条会话不同目录并发存在且路径安全各按各根(tmp_path):
    a = tmp_path / '甲项目'
    b = tmp_path / '乙项目'
    a.mkdir(); b.mkdir()
    (a / 'own.txt').write_text('A', encoding='utf-8')
    (b / 'own.txt').write_text('B', encoding='utf-8')

    src = BOOT + _new_service(tmp_path) + f'''
设 甲目录 为 "{_lp(a)}"
设 乙目录 为 "{_lp(b)}"
设 甲应 为 服务.处理新建会话(["方法":"POST","路径":"/api/sessions","头":{{}},"体":编码({_body('甲', '甲目录')})], "")
设 乙应 为 服务.处理新建会话(["方法":"POST","路径":"/api/sessions","头":{{}},"体":编码({_body('乙', '乙目录')})], "")
设 甲元 为 解析JSON(甲应["体"])
设 乙元 为 解析JSON(乙应["体"])
设 甲会 为 服务.取会话(甲元["id"])
设 乙会 为 服务.取会话(乙元["id"])
设 甲根 为 取根目录(甲会.取工作目录())
设 乙根 为 取根目录(乙会.取工作目录())
打印("状态甲=" + 转字符串(甲应["状态"]))
打印("状态乙=" + 转字符串(乙应["状态"]))
打印("甲cwd=" + 甲会.取工作目录())
打印("乙cwd=" + 乙会.取工作目录())
打印("甲读自己=" + 转字符串(解析安全路径(甲根, "own.txt")["ok"]))
打印("乙读自己=" + 转字符串(解析安全路径(乙根, "own.txt")["ok"]))
打印("甲读乙=" + 转字符串(解析安全路径(甲根, "../乙项目/own.txt")["ok"]))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['状态甲'] == '200' and kv['状态乙'] == '200', out
    assert _same(kv['甲cwd'], str(a)), f'甲会话 cwd 不对：{out}'
    assert _same(kv['乙cwd'], str(b)), f'乙会话 cwd 不对：{out}'
    assert kv['甲读自己'] == 'True' and kv['乙读自己'] == 'True', f'各自读自己目录被拒\n{out}'
    assert kv['甲读乙'] == 'False', f'甲越界读到乙的文件（各根未生效）\n{out}'


# --------------------------------------------------------------------------- #
# 2. GET /api/sessions/:id 的 cwd，与重启后 cwd 不丢
# --------------------------------------------------------------------------- #
def test_会话详情cwd与重启后cwd不丢(tmp_path):
    target = tmp_path / '项目'
    target.mkdir()

    src = BOOT + _new_service(tmp_path) + f'''
设 目录 为 "{_lp(target)}"
设 应 为 服务.处理新建会话(["方法":"POST","路径":"/api/sessions","头":{{}},"体":编码({_body('持久', '目录')})], "")
设 元 为 解析JSON(应["体"])
设 详 为 服务.处理会话详情(元["id"])
设 详体 为 解析JSON(详["体"])
打印("id=" + 元["id"])
打印("详情cwd=" + 详体["工作目录"])
# 新实例（模拟重启）：索引元数据与新 Web服务端 都要能恢复 cwd
设 库2 为 新建 会话存储(路径连接(根, "sessions"))
设 服务2 为 新建 Web服务端()
服务2.设置会话库(库2)
设 元2 为 库2.取元数据(元["id"])
设 会2 为 服务2.取会话(元["id"])
打印("索引cwd=" + 元2["工作目录"])
打印("重启cwd=" + 会2.取工作目录())
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert _same(kv['详情cwd'], str(target)), f'详情没有 cwd\n{out}'
    assert _same(kv['索引cwd'], str(target)), f'索引没持久化 cwd\n{out}'
    assert _same(kv['重启cwd'], str(target)), f'重启后 cwd 丢失\n{out}'


# --------------------------------------------------------------------------- #
# 3. 非法目录 400，且索引里没有新会话
# --------------------------------------------------------------------------- #
def test_非法目录400且不建会话(tmp_path):
    a_file = tmp_path / '是文件.txt'
    a_file.write_text('x', encoding='utf-8')

    src = BOOT + _new_service(tmp_path) + f'''
设 前数 为 长(库.列表会话())
设 缺 为 服务.处理新建会话(["方法":"POST","路径":"/api/sessions","头":{{}},"体":编码({_body('缺', '"' + _lp(tmp_path / '不存在') + '"')})], "")
设 文 为 服务.处理新建会话(["方法":"POST","路径":"/api/sessions","头":{{}},"体":编码({_body('文', '"' + _lp(a_file) + '"')})], "")
设 相 为 服务.处理新建会话(["方法":"POST","路径":"/api/sessions","头":{{}},"体":编码({_body('相', '"relative/dir"')})], "")
设 后数 为 长(库.列表会话())
打印("缺状态=" + 转字符串(缺["状态"]))
打印("文状态=" + 转字符串(文["状态"]))
打印("相状态=" + 转字符串(相["状态"]))
打印("缺体=" + 转字符串(缺["体"]))
打印("前数=" + 转字符串(前数))
打印("后数=" + 转字符串(后数))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['缺状态'] == kv['文状态'] == kv['相状态'] == '400', f'非法目录未拒绝\n{out}'
    assert kv['缺体'].strip(), f'400 必须带明确理由\n{out}'
    assert kv['前数'] == kv['后数'], f'非法请求写进了索引\n{out}'


# --------------------------------------------------------------------------- #
# 4. 不传工作目录时回退全局（旧行为不变）
# --------------------------------------------------------------------------- #
def test_不传目录回退全局(tmp_path):
    g = tmp_path / '全局'
    g.mkdir()

    src = BOOT + _new_service(tmp_path) + f'''
设 全局 为 "{_lp(g)}"
服务.生效工作目录 为 全局
设 应 为 服务.处理新建会话(["方法":"POST","路径":"/api/sessions","头":{{}},"体":编码({_body('默认')})], "")
设 元 为 解析JSON(应["体"])
设 会 为 服务.取会话(元["id"])
设 懒 为 服务.取会话("")
打印("显式cwd=" + 会.取工作目录())
打印("惰性cwd=" + 懒.取工作目录())
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert _same(kv['显式cwd'], str(g)), f'未回退全局：{out}'
    assert _same(kv['惰性cwd'], str(g)), f'惰性建会话未回退全局：{out}'


# --------------------------------------------------------------------------- #
# 5. POST /v1/chat/completions 首条消息带 工作目录 → 写入新会话头信息
# --------------------------------------------------------------------------- #
def test_对话首条消息带目录写入新会话头信息(tmp_path):
    target = tmp_path / '聊天项目'
    target.mkdir()
    bad_dir = tmp_path / '不存在聊天目录'

    src = BOOT + """
从 总入口 导入 组装注册表
从 流 导入 造块开始, 造文本增量, 造块结束, 造结束, 造停止原因

类 模拟客户端:
  属性 模型名 等于 "mock"
  段落 构造:
    设 己.模型名 为 "mock"
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    设 文本 为 "ok"
    返回 [造块开始(0, "text"), 造文本增量(0, 文本), 造块结束(0, ["type":"text","text":文本]), 造结束(造停止原因())]
""" + _new_service(tmp_path) + f"""
服务.配置(新建 模拟客户端(), 组装注册表(), 根, 30.0, "", 空)
设 目录 为 "{_lp(target)}"
设 聊天体 为 序列化JSON(["model":"mock","messages":[["role":"user","content":"你好"]],"工作目录":目录])
设 应 为 服务.处理对话(["方法":"POST","路径":"/v1/chat/completions","头":{{}},"体":编码(聊天体)], "", "")
设 坏体 为 序列化JSON(["model":"mock","messages":[["role":"user","content":"你好"]],"工作目录":"{_lp(bad_dir)}"])
设 坏应 为 服务.处理对话(["方法":"POST","路径":"/v1/chat/completions","头":{{}},"体":编码(坏体)], "", "")
设 标识 为 ""
遍历 键 之 字典键列表(服务.会话表):
  设 标识 为 键
设 会 为 服务.会话表[标识]
设 元 为 库.取元数据(标识)
打印("状态=" + 转字符串(应["状态"]))
打印("坏状态=" + 转字符串(坏应["状态"]))
打印("cwd=" + 会.取工作目录())
打印("键=" + 标识)
打印("库数=" + 转字符串(长(库.列表会话())))
设 索引值 为 "空"
如果 元 != 空:
  设 索引值 为 元["工作目录"]
打印("索引cwd=" + 索引值)
"""
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['状态'] == '200', f'对话失败\n{out}'
    assert kv['坏状态'] == '400', f'completions 非法目录未拒绝\n{out}'
    assert _same(kv['cwd'], str(target)), f'首条消息没把目录写进会话头信息\n{out}'
    assert _same(kv['索引cwd'], str(target)), f'索引没记下会话目录\n{out}'

# -*- coding: utf-8 -*-
"""T-0484 压缩摘要器判据（八段 checkpoint 指令与校验，贴 dsh compaction）。

覆盖：
  1) 造摘要指令：八段标题顺序全对、「不提及」「只输出」三条规则在、长度 ≤ 4000；
  2) 造摘要请求：3 条 → 4 条，前 3 条深比较不变（不原地改入参），末条是 user 指令；
  3) 带旧检查点：指令含「先前检查点」「合并」，旧文本原样嵌入；
  4) 校验摘要：完整八段 → ok；删「下一步」→ 缺段=["下一步"]；顺序颠倒 → ok=假；
  5) 抽取摘要文本：两段 text 拼接、只有 image 块 → ""、首尾空白被去掉；
  6) 契约常量：摘要指令字符上限() = 4000，八段标题() 返回副本（外部改动不污染常量）。

套路照抄 T-0402 的 _run（驱动脚本 + 子进程 + k=v 解析）与 _find_repo（沿祖先探测兄弟仓）。
反跑（手工验证口径）：
  ① 删 造摘要指令 里「不提及本次摘要请求」一条 → test_造摘要指令八段顺序与规则 红；
  ② 校验摘要 改成只查数量不查顺序 → test_校验摘要查缺失与乱序 红；
  ③ 造摘要请求 里去掉 深拷贝、直接往入参追加 → test_造摘要请求不原地改 红。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 120


def _find_repo(env_name, dir_name):
    """沿祖先逐级探测兄弟仓（worktree 深度不固定，口径同 运行.py / T-0399）。"""
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


def _run(src: str, tmp_path):
    """把光明驱动脚本写进 tmp_path，起真实 运行.py 子进程跑，解析 k=v。"""
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = dict(os.environ)
    for key, repo in (('LIGHTPLUGIN', 'lightplugin'), ('LIGHT_MERGE', 'light-merge')):
        found = _find_repo(key, repo)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
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


BOOT = '''
从 字符串处理 导入 长度, 查找, 分割成行
从 压缩摘要器 导入 造摘要指令, 造摘要请求, 校验摘要, 抽取摘要文本, 摘要指令字符上限, 八段标题
'''


def test_造摘要指令八段顺序与规则(tmp_path):
    src = BOOT + '''
设 指令 为 造摘要指令()
设 标题表 为 八段标题()
设 有序 为 真
设 上位置 为 -1
设 序 为 0
当 序 < 长度(标题表):
  设 位置 为 查找(指令, "## " + 标题表[序])
  如果 位置 < 0:
    设 有序 为 假
  如果 位置 >= 0:
    如果 位置 <= 上位置:
      设 有序 为 假
    设 上位置 为 位置
  设 序 为 序 + 1
打印 "标题数=" + 转字符串(长度(标题表))
打印 "有序=" + 转字符串(有序)
打印 "首段位=" + 转字符串(查找(指令, "## 主要请求与意图"))
打印 "末段位=" + 转字符串(查找(指令, "## 关键上下文"))
打印 "含不提及=" + 转字符串(指令.包含("不提及"))
打印 "含只输出=" + 转字符串(指令.包含("只输出"))
打印 "含原文事实=" + 转字符串(指令.包含("保留原文事实"))
打印 "含占位=" + 转字符串(指令.包含("(none)"))
打印 "长度=" + 转字符串(长度(指令))
打印 "上限=" + 转字符串(摘要指令字符上限())
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-3000:]
    assert kv['标题数'] == '8', f"八段标题应为 8 条，实际 {kv['标题数']}"
    assert kv['有序'] == 'True', '八段标题必须按契约顺序出现'
    assert int(kv['首段位']) < int(kv['末段位'])
    assert kv['含不提及'] == 'True', '必须含「不提及压缩」规则'
    assert kv['含只输出'] == 'True', '必须含「只输出 checkpoint 文本」规则'
    assert kv['含原文事实'] == 'True'
    assert kv['含占位'] == 'True', '空段必须用 (none) 占位'
    assert kv['上限'] == '4000'
    assert int(kv['长度']) <= 4000, f"指令超上限：{kv['长度']}"


def test_造摘要请求不原地改(tmp_path):
    src = BOOT + '''
设 原表 为 [["role": "user", "content": [["type": "text", "text": "第一条"]]], ["role": "assistant", "content": [["type": "text", "text": "第二条"]]], ["role": "user", "content": [["type": "text", "text": "第三条"]]]]
设 指令 为 造摘要指令()
设 请求表 为 造摘要请求(原表)
设 前三条不变 为 真
如果 请求表[0] != 原表[0]:
  设 前三条不变 为 假
如果 请求表[1] != 原表[1]:
  设 前三条不变 为 假
如果 请求表[2] != 原表[2]:
  设 前三条不变 为 假
打印 "请求条数=" + 转字符串(长度(请求表))
打印 "原表条数=" + 转字符串(长度(原表))
打印 "前三条不变=" + 转字符串(前三条不变)
打印 "末条角色=" + 转字符串(请求表[3]["role"])
打印 "末条块数=" + 转字符串(长度(请求表[3]["content"]))
打印 "末条种类=" + 转字符串(请求表[3]["content"][0]["type"])
打印 "末条等于指令=" + 转字符串(请求表[3]["content"][0]["text"] == 指令)
打印 "末条含八段=" + 转字符串(请求表[3]["content"][0]["text"].包含("## 主要请求与意图"))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-3000:]
    assert kv['请求条数'] == '4', f"3 条消息应得到 4 条请求，实际 {kv['请求条数']}"
    assert kv['原表条数'] == '3', '入参消息表不得被原地追加'
    assert kv['前三条不变'] == 'True', '前三条消息必须逐字保留（深比较）'
    assert kv['末条角色'] == 'user'
    assert kv['末条块数'] == '1'
    assert kv['末条种类'] == 'text'
    assert kv['末条等于指令'] == 'True', '末条正文应就是 造摘要指令()'
    assert kv['末条含八段'] == 'True'


def test_旧检查点合并且在(tmp_path):
    src = BOOT + '''
设 原表 为 [["role": "user", "content": [["type": "text", "text": "早先对话"]]]]
设 旧文 为 "旧检查点正文：改了 src/压缩.light 第 40 行"
设 新表 为 造摘要请求(原表, 旧文)
设 指令 为 新表[长度(新表) - 1]["content"][0]["text"]
打印 "条数=" + 转字符串(长度(新表))
打印 "含先前检查点=" + 转字符串(指令.包含("先前检查点"))
打印 "含合并=" + 转字符串(指令.包含("合并"))
打印 "旧文原样=" + 转字符串(指令.包含(旧文))
打印 "含同结构=" + 转字符串(指令.包含("同结构"))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-3000:]
    assert kv['条数'] == '2'
    assert kv['含先前检查点'] == 'True'
    assert kv['含合并'] == 'True'
    assert kv['旧文原样'] == 'True', '旧检查点文本必须原样嵌入指令'
    assert kv['含同结构'] == 'True'


def test_校验摘要查缺失与乱序(tmp_path):
    src = BOOT + '''
设 标题表 为 八段标题()
设 摘要文本 为 ""
遍历 标题 之 标题表:
  设 摘要文本 为 摘要文本 + "## " + 标题 + "\\n- (none)\\n"
设 检查甲 为 校验摘要(摘要文本)
打印 "完整ok=" + 转字符串(检查甲["ok"])
打印 "完整缺段=" + 转字符串(检查甲["缺段"])

设 删段文本 为 ""
遍历 标题 之 标题表:
  如果 标题 == "下一步":
    继续
  设 删段文本 为 删段文本 + "## " + 标题 + "\\n- (none)\\n"
设 检查乙 为 校验摘要(删段文本)
打印 "删后ok=" + 转字符串(检查乙["ok"])
打印 "删后缺段=" + 转字符串(检查乙["缺段"])

设 乱序文本 为 ""
遍历 标题 之 标题表:
  如果 标题 == "当前工作":
    设 乱序文本 为 乱序文本 + "## 下一步\\n- (none)\\n"
    继续
  如果 标题 == "下一步":
    设 乱序文本 为 乱序文本 + "## 当前工作\\n- (none)\\n"
    继续
  设 乱序文本 为 乱序文本 + "## " + 标题 + "\\n- (none)\\n"
设 检查丙 为 校验摘要(乱序文本)
打印 "乱序ok=" + 转字符串(检查丙["ok"])
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-3000:]
    assert kv['完整ok'] == 'True', f"完整八段应通过：{kv['完整缺段']}"
    assert kv['完整缺段'] == '[]'
    assert kv['删后ok'] == 'False'
    assert kv['删后缺段'] == "['下一步']", f"缺段应恰为 ['下一步']，实际 {kv['删后缺段']}"
    assert kv['乱序ok'] == 'False', '标题顺序颠倒必须判不合格（只查数量会漏）'


def test_抽取摘要文本拼接与去空白(tmp_path):
    src = BOOT + '''
设 两段 为 抽取摘要文本([["type": "text", "text": "  甲段  "], ["type": "image", "data": "xx"], ["type": "text", "text": "乙段"]])
设 只图 为 抽取摘要文本([["type": "image", "data": "xx"]])
设 空表 为 抽取摘要文本([])
打印 "两段=" + 转字符串(两段 == "甲段  乙段")
打印 "两段值=" + 两段
打印 "只图空=" + 转字符串(只图 == "")
打印 "空表空=" + 转字符串(空表 == "")
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-3000:]
    assert kv['两段'] == 'True', f"两段 text 应拼接且去首尾空白，实际 {kv['两段值']!r}"
    assert kv['只图空'] == 'True'
    assert kv['空表空'] == 'True'


def test_契约常量返回副本(tmp_path):
    src = BOOT + '''
设 表甲 为 八段标题()
表甲.追加("外部脏增")
设 表乙 为 八段标题()
打印 "甲长=" + 转字符串(长度(表甲))
打印 "乙长=" + 转字符串(长度(表乙))
打印 "乙首=" + 表乙[0]
打印 "乙末=" + 表乙[长度(表乙) - 1]
打印 "上限=" + 转字符串(摘要指令字符上限())
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, out[-3000:]
    assert kv['甲长'] == '9'
    assert kv['乙长'] == '8', '八段标题() 必须返回副本，外部追加不得污染契约常量'
    assert kv['乙首'] == '主要请求与意图'
    assert kv['乙末'] == '关键上下文'
    assert kv['上限'] == '4000'

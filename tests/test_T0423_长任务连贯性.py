# -*- coding: utf-8 -*-
"""T-0423 长任务连贯性：压缩必须真降上下文 + 长静默必须可见。

本卡来自一次真实故障复盘（2026-11-21，lightharness 跑长任务「任务不连贯」）。
现场证据全部来自会话日志与复现脚本，四个缺陷各自独立、互相放大：

  A) 压缩**越压越大**：旧实现每压一次就追加一个检查点，且从不折叠上一版检查点
     （折叠范围按「序号」算，而新检查点序号比所有旧事件都大，永远落在保留区之外）。
     实测同一会话连续压 8 次：292 → 408 → 524 → … → 1104 token，单调上涨。
  B) 压缩**落盘后弹回**：遮蔽位由 编码V2事件 写成英文 `redacted`，
     而 读入会话 只认中文「遮蔽」——压缩结果一重启/续写就整段复活。
  C) token 计量**看不见大头**：估算token 只数顶层 text 块，
     工具结果（一轮里最大的一块，实测 13006 token）与推理正文都计为 0，
     于是阈值永远不触发，长任务直接撞窗口。
  D) 长静默**完全不可见**：流式只转发 text-delta，reasoning-delta 被丢弃；
     工具调用/结果帧只在整轮跑完后由 生成SSE 一次性补齐。
     会话日志实测：单步推理 21922 字符 / 约 10 分钟，正文仅 1070 字符
     —— 浏览器整段时间收不到任何字节，用户看到的就是「卡死」。

判据（每条都做过反跑）：
  1. A：连续压缩后 token 单调不增，且检查点数量不随压缩次数增长；
  2. A：无收益的压缩被拒绝（压完更贵就不压），台账原样恢复；
  3. B：压缩后的会话落盘再读回，遮蔽数与 token 与内存完全一致；
  4. C：工具结果 / 推理块 / 工具参数都计入估算；
  5. D：流块翻译把 reasoning-delta 也转成帧；
  6. D：代理把工具调用/结果帧**在执行当时**推给回调（不依赖收尾的 生成SSE）。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 300


def _find_sibling(name):
    candidates = [
        os.environ.get(name, ''),
        os.path.join(ROOT, '..', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
        os.path.join(ROOT, '..', '..', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
        '/home/skywalk/dswork/' + ('lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _run(src, tmp_path):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
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
从 会话 导入 新建会话
从 消息 导入 造用户消息, 造助手消息, 造文本块, 造推理块, 造工具调用块, 造工具结果块, 造工具结果消息
从 压缩 导入 压缩到最近, 估算token, 压缩管理器, 检查点计数

段落 填对话(会话对象, 轮数, 字数):
  设 i 为 0
  当 i < 轮数:
    设 正文 为 "第" + 转字符串(i) + "轮："
    设 k 为 0
    当 k < 字数:
      设 正文 为 正文 + "填充内容"
      设 k 为 k + 1
    会话对象.记录事件("user/message", 造用户消息([造文本块(正文)]))
    会话对象.记录事件("assistant/message", ["消息": 造助手消息([造文本块("回答" + 正文)], "p", "m")])
    设 i 为 i + 1
  返回 真
'''


# --------------------------------------------------------------------------- #
# 1. A：连续压缩必须收敛（旧实现 292→408→524→…→1104 单调上涨）
# --------------------------------------------------------------------------- #
def test_连续压缩后token有界且检查点不累积(tmp_path):
    src = BOOT + """
段落 主:
  设 会话对象 为 新建会话("t0423a", ".")
  填对话(会话对象, 40, 6)
  设 初始 为 估算token(会话对象.整理消息())
  设 峰值 为 初始
  设 末段最大 为 0
  设 轮 为 0
  当 轮 < 20:
    设 表 为 压缩到最近(会话对象, 2, 空, 120)
    设 当前 为 估算token(表)
    如果 当前 > 峰值:
      设 峰值 为 当前
    如果 轮 >= 10 且 当前 > 末段最大:
      设 末段最大 为 当前
    设 轮 为 轮 + 1
  设 末态 为 估算token(会话对象.整理消息())
  打印 "初始token=" + 转字符串(初始)
  打印 "峰值token=" + 转字符串(峰值)
  打印 "末段最大token=" + 转字符串(末段最大)
  打印 "末态token=" + 转字符串(末态)
  打印 "检查点数=" + 转字符串(检查点计数(会话对象))
主()
"""
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    # 反证（旧实现）：同一场景压 8 次 token 就涨到 1104，压 20 次会一路爬，
    #   检查点数等于压缩次数。修好后必须「有界」：峰值不越过初始太多，
    #   后半段稳定在同一水平，末态明显低于初始。
    assert float(kv['峰值token']) <= 1100, (
        f'压缩后上下文峰值 {kv["峰值token"]} 失控（旧实现一路涨到 1104 以上）\n{out}')
    assert float(kv['末段最大token']) <= float(kv['峰值token']) + 0.01, out
    assert float(kv['末态token']) < float(kv['初始token']), (
        f'压缩没有真正把上下文压下去：末态 {kv["末态token"]} 初始 {kv["初始token"]}\n{out}')
    assert int(kv['检查点数']) <= 3, (
        f'检查点随压缩次数累积（{kv["检查点数"]} 个，压了 20 次）：旧检查点没被折叠\n{out}')


# --------------------------------------------------------------------------- #
# 2. A：无收益压缩被拒绝，台账原样恢复
# --------------------------------------------------------------------------- #
def test_无收益压缩拒绝且台账复原(tmp_path):
    src = BOOT + '''
段落 主:
  # 只有一条消息：折叠区为空 / 折叠下来还不够付检查点框架成本
  设 会话对象 为 新建会话("t0423b2", ".")
  会话对象.记录事件("user/message", 造用户消息([造文本块("唯一一条很短的消息")]))
  设 管理器 为 新建 压缩管理器(会话对象, ["上下文窗口": 30, "阈值比例": 0.5, "保留条数": 1])
  设 前 为 估算token(会话对象.整理消息())
  设 前条数 为 长度(会话对象.整理消息())
  设 详情 为 管理器.检查并压缩详情()
  设 后 为 估算token(会话对象.整理消息())
  打印 "压缩了=" + 转字符串(详情["压缩了"])
  打印 "前=" + 转字符串(前)
  打印 "后=" + 转字符串(后)
  打印 "条数不变=" + 转字符串(长度(会话对象.整理消息()) == 前条数)
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['压缩了'] == 'False', f'压不动就该拒绝（不能越压越大）\n{out}'
    # 反证：如果拒绝后没回滚，后 token 会大于前，或条数被检查点改掉
    assert kv['前'] == kv['后'], f'拒绝压缩后上下文必须原样（前 {kv["前"]} 后 {kv["后"]}）\n{out}'
    assert kv['条数不变'] == 'True', f'拒绝压缩后消息条数必须原样\n{out}'


# --------------------------------------------------------------------------- #
# 3. B：压缩结果落盘再读回，不得「弹回」
# --------------------------------------------------------------------------- #
def test_压缩遮蔽位可落盘可读回(tmp_path):
    src = BOOT + '''
从 总入口 导入 增量保存
从 持久化 导入 读入会话

段落 计遮蔽(会话对象):
  设 数 为 0
  遍历 记录 之 会话对象.汇集全部事件():
    如果 记录.包含("遮蔽") 且 记录["遮蔽"]:
      设 数 为 数 + 1
  返回 数

段落 主:
  设 根 为 转字符串(当前目录()) + "/sess"
  设 会话对象 为 新建会话("t0423c", 根)
  填对话(会话对象, 8, 3)
  设 忽略1 为 增量保存(根, 会话对象, 0)
  设 忽略2 为 压缩到最近(会话对象, 2, 空, 20)
  设 忽略3 为 增量保存(根, 会话对象, 16)
  设 重载 为 读入会话(根, 根, "t0423c")
  打印 "内存遮蔽=" + 转字符串(计遮蔽(会话对象))
  打印 "重载遮蔽=" + 转字符串(计遮蔽(重载))
  打印 "内存token=" + 转字符串(估算token(会话对象.整理消息()))
  打印 "重载token=" + 转字符串(估算token(重载.整理消息()))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    # 反证：旧实现 内存遮蔽 7 / 重载遮蔽 0，且重载 token 更大（压缩整段复活）
    assert int(kv['内存遮蔽']) > 0, f'这个场景本该发生压缩\n{out}'
    assert kv['内存遮蔽'] == kv['重载遮蔽'], \
        f'遮蔽位没能落盘读回：内存 {kv["内存遮蔽"]} vs 重载 {kv["重载遮蔽"]}（压缩会「弹回」）\n{out}'
    assert kv['内存token'] == kv['重载token'], \
        f'重载后上下文与内存不一致（内存 {kv["内存token"]} vs 重载 {kv["重载token"]}）\n{out}'


# --------------------------------------------------------------------------- #
# 4. C：计量必须覆盖工具结果 / 推理 / 工具参数
# --------------------------------------------------------------------------- #
def test_估算覆盖工具结果与推理(tmp_path):
    src = BOOT + '''
段落 主:
  设 纯文本 为 ["role": "user", "content": [造文本块("纯文本内容")]]
  设 工具结果 为 [造工具结果消息("c1", [造文本块("工具输出的正文内容八个字")], 假)]
  设 推理 为 ["role": "assistant", "content": [造推理块("推理正文内容八个字")]]
  设 调用 为 ["role": "assistant", "content": [造工具调用块("c2", "bash", "{\\"命令\\":\\"ls\\"}")]]
  打印 "纯文本=" + 转字符串(估算token([纯文本]))
  打印 "工具结果=" + 转字符串(估算token(工具结果))
  打印 "推理=" + 转字符串(估算token([推理]))
  打印 "调用参数=" + 转字符串(估算token([调用]))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    # 反证：旧实现 工具结果=0.0（只数顶层 text 块）
    assert float(kv['工具结果']) > 0, \
        f'工具结果必须计入 token（旧实现恒为 0，于是长任务永不触发压缩）\n{out}'
    assert float(kv['推理']) > 0, f'推理正文必须计入 token\n{out}'
    assert float(kv['调用参数']) > 0, f'工具调用参数必须计入 token\n{out}'
    # 工具结果正文比纯文本长，估算必须更大
    assert float(kv['工具结果']) > float(kv['纯文本']), out


# --------------------------------------------------------------------------- #
# 5. D：流块翻译要把 reasoning-delta 也转成帧（否则长静默黑屏）
# --------------------------------------------------------------------------- #
def test_流块翻译包含推理帧(tmp_path):
    src = '''
从 实时流 导入 流块转增量帧

段落 主:
  设 推理帧表 为 流块转增量帧(["type": "reasoning-delta", "index": 0, "text": "我在想"])
  设 文本帧表 为 流块转增量帧(["type": "text-delta", "index": 1, "text": "好的"])
  设 空帧表 为 流块转增量帧(["type": "reasoning-delta", "index": 0, "text": ""])
  打印 "推理帧数=" + 转字符串(长度(推理帧表))
  打印 "文本帧数=" + 转字符串(长度(文本帧表))
  打印 "空推理帧数=" + 转字符串(长度(空帧表))
  打印 "推理键在=" + 转字符串(序列化JSON(推理帧表) .包含("reasoning_content"))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    # 反证：旧实现 reasoning-delta 一律丢弃 → 推理帧数=0
    assert kv['推理帧数'] == '1', f'reasoning-delta 必须转成帧（旧实现直接丢弃 → 长任务黑屏）\n{out}'
    assert kv['推理键在'] == 'True', f'推理帧要能被前端按 reasoning_content 识别\n{out}'
    assert kv['文本帧数'] == '1', out
    assert kv['空推理帧数'] == '0', f'空推理不该产生空帧\n{out}'


# --------------------------------------------------------------------------- #
# 6. D：代理把工具帧在「执行当时」推给回调，不等整轮收尾
# --------------------------------------------------------------------------- #
def test_工具帧在执行当时推送(tmp_path):
    src = '''
从 代理 导入 代理循环
从 会话 导入 新建会话
从 工具 导入 工具注册表, 造工具定义

类 假客户端:
  属性 模型名 等于 "mock"
  属性 次数 等于 0
  段落 构造:
    设 己.次数 为 0
  段落 对话响应(网络消息, 选项, 工具模式表, 增量回调 = 空):
    设 己.次数 为 己.次数 + 1
    如果 己.次数 == 1:
      返回 [
        ["type": "block-start", "index": 0, "blockType": "tool-call"],
        ["type": "tool-call-delta", "index": 0, "id": "c1", "name": "echo1", "argumentsDelta": "{}"],
        ["type": "block-end", "index": 0, "block": ["type": "tool-call", "id": "c1", "name": "echo1", "arguments": "{}"]],
        ["type": "finish", "reason": ["种类": "tool-calls"]]
      ]
    返回 [
      ["type": "block-start", "index": 0, "blockType": "text"],
      ["type": "text-delta", "index": 0, "text": "完成"],
      ["type": "block-end", "index": 0, "block": ["type": "text", "text": "完成"]],
      ["type": "finish", "reason": ["种类": "stop"]]
    ]

段落 假执行(参数):
  返回 ["content": [["type": "text", "text": "回声结果"]], "isError": 假]

段落 主:
  设 会话对象 为 新建会话("t0423d", 当前目录())
  设 注册表 为 新建 工具注册表()
  注册表.注册(造工具定义("echo1", "回声", ["type": "object", "properties": {}], 假执行))
  设 帧表 为 []
  段落 收工具帧(帧):
    帧表.追加(帧)
    返回 真
  设 代理对象 为 新建 代理循环(会话对象, 新建 假客户端(), 注册表, ["工具回调": 收工具帧])
  设 结果 为 代理对象.驱动("跑一下工具")
  打印 "结果=" + 转字符串(结果["种类"])
  打印 "帧数=" + 转字符串(长度(帧表))
  设 有调用帧 为 假
  设 有结果帧 为 假
  遍历 帧 之 帧表:
    如果 帧.获取("种类", "") == "工具调用":
      设 有调用帧 为 真
    如果 帧.获取("种类", "") == "工具结果":
      设 有结果帧 为 真
  打印 "有调用帧=" + 转字符串(有调用帧)
  打印 "有结果帧=" + 转字符串(有结果帧)
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动失败 rc={rc}\n{out}'
    assert kv['结果'] == 'completed', out
    # 反证：旧实现只有 生成SSE 在收尾时构造工具帧，回调链上一条都没有
    assert kv['有调用帧'] == 'True', \
        f'工具调用帧必须在执行当时推出（否则工具跑几分钟界面全空白）\n{out}'
    assert kv['有结果帧'] == 'True', f'工具结果帧必须及时推出\n{out}'

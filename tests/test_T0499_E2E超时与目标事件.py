# -*- coding: utf-8 -*-
"""T-0499 判据：E2E 超时预算契约 + 目标 complete 落 goal/change 事件契约（T-0523）。

锁两件事，防止回归：

D1 · 真起服务的 E2E 判据超时预算
    pytest.ini 全局 --timeout=60 与「真起服务 E2E 冷启动约 59s」（test_T0456
    先例注释）严重不匹配：全局预算在服务起完前先到点，pytest-timeout（Windows
    thread 模式）dump 栈后整个测试进程终止——修前 5 条用例全部 63~64s 确定性
    Timeout。契约：真起服务的用例必须显式 @pytest.mark.timeout(300)（沿 T-0456
    先例），全局 60 继续看住其余快用例。本文件静态钉住 6 条用例的 mark 与
    全局预算并存，缺一即红。

D2 · 目标续跑核心契约：模型 目标.complete 必须落 goal/change 事件
    T0407 修前留证定位：完整 HTTP 链路里 T-0486 LLM 摘要器的压缩请求会抢走 mock
    状态机的 tool_call 额度，目标工具从未被调用（判据侧缺陷）；而「目标工具
    complete → web 闭包落 goal/change 事件 → 台账相位推进」的业务契约本身要
    用轻量 E2E 独立锁住——不起 HTTP mock LLM，driver 子进程内用 mock 客户端
    直驱 处理对话：/goal 立目标 → 第 1 轮回文本（续跑推进）→ 第 2 轮发
    目标.complete 工具调用 → 断言会话事件、会话 JSONL 与台账相位。
    driver 环境不设 HARNESS_MODEL_CONTEXT_WINDOW，默认窗口下 2 轮短对话不触发
    压缩，判据不受摘要请求干扰。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / '运行.py'
TIMEOUT_SEC = 280  # < pytest.mark.timeout(300)：TimeoutExpired 先出可读信息
# T-0523 D1 第二层：处理对话 第一行就 起队列闸门 → T-0490 的排队唤醒循环（当 真 +
# sleep 2s）以非守护线程挂住进程（stdlib/线程.py 默认 守护线程=False），driver 业务
# 跑完后进程永不退出——这正是修前 subprocess 120s/240s TimeoutExpired 的机制。
# 判据侧契约：driver 末尾统一追加结束标记行，_run 见到标记即 kill 并按业务完成
# 解析（rc=0）；超时未见标记 = 业务真没跑完，抛 TimeoutExpired。
DONE_MARK = 'T0523-DRIVER-DONE'


# --------------------------------------------------------------------------- #
# D1 · 静态回归锁：真起服务的 E2E 用例必须显式声明 timeout(300)
# --------------------------------------------------------------------------- #
# 覆盖口径：凡以 subprocess 起 Light 子进程判据的用例（driver 重导入 web服务器，
# 冷启动约 59s；T0407 的重负载在 module fixture setup）都要显式放宽——并发争用下
# 全局 60s 会先杀判据甚至崩 worker（T-0523 修前留证）。
MARKED_E2E = [
    ("tests/test_T0395_会话工作目录.py", "test_两条会话不同目录并发存在且路径安全各按各根"),
    ("tests/test_T0395_会话工作目录.py", "test_会话详情cwd与重启后cwd不丢"),
    ("tests/test_T0395_会话工作目录.py", "test_非法目录400且不建会话"),
    ("tests/test_T0395_会话工作目录.py", "test_不传目录回退全局"),
    ("tests/test_T0395_会话工作目录.py", "test_对话首条消息带目录写入新会话头信息"),
    ("tests/test_T0395_会话工作目录.py", "test_空体与非字典体仍建会话"),
    ("tests/test_T0397_会话模式权限.py", "test_两会话并发权限隔离同一工具分别放行拒绝"),
    ("tests/test_T0397_会话模式权限.py", "test_未设置回退默认标准加按类别"),
    ("tests/test_T0397_会话模式权限.py", "test_改全局默认不影响已绑定会话"),
    ("tests/test_T0397_会话模式权限.py", "test_切换会话持久化重启恢复"),
    ("tests/test_T0397_会话模式权限.py", "test_会话内切换只改本会话"),
    ("tests/test_T0397_会话模式权限.py", "test_对话每轮写回预设"),
    ("tests/test_T0397_会话模式权限.py", "test_续轮与单项更新不互相抹除"),
    ("tests/test_T0398_附件暂存契约.py", "test_服务端稳健接收附件形状"),
    ("tests/test_T0470_工具根与cd守卫.py", "test_会话cwd成为四工具根"),
    ("tests/test_T0470_工具根与cd守卫.py", "test_cd守卫_解析后路径判定"),
    ("tests/test_T0470_工具根与cd守卫.py", "test_cd守卫_间接形式也判定"),
    ("tests/test_T0470_工具根与cd守卫.py", "test_无worktree时根仍为项目根"),
    ("tests/test_T0470_工具根与cd守卫.py", "test_工作目录参数必须过白名单"),
    ("tests/test_T0470_工具根与cd守卫.py", "test_Web服务端会话cwd透传到工具"),
    ("tests/test_T0407_收口接线.py", "test_目标续跑两轮后由目标工具收口"),
    ("tests/test_T0407_收口接线.py", "test_小窗口下自动压缩写出检查点"),
    ("tests/test_T0407_收口接线.py", "test_compact命令不消耗模型轮次并回压缩帧"),
    ("tests/test_T0407_收口接线.py", "test_八种模式都可开会话"),
    ("tests/test_T0407_收口接线.py", "test_统计帧带耗时与速率"),
    ("tests/test_T0407_收口接线.py", "test_同会话并发第二条走202排队"),
    ("tests/test_T0499_E2E超时与目标事件.py", "test_目标complete落goalchange事件且台账推进"),
]


@pytest.mark.parametrize("rel,func", MARKED_E2E)
def test_真起服务E2E用例显式声明超时预算(rel, func):
    """全局 60s 会先杀冷启动 59s 的真起服务判据（T-0523 D1），必须显式 mark(300)。"""
    src = (ROOT / rel).read_text(encoding='utf-8')
    pat = r"@pytest\.mark\.timeout\(300\)\s*\ndef " + re.escape(func) + r"\("
    assert re.search(pat, src), (
        f"{rel}::{func} 缺 @pytest.mark.timeout(300)——pytest.ini 全局 --timeout=60 "
        f"会在服务冷启动（约 59s，见 test_T0456 先例）完成前先杀判据，"
        f"表现为确定性 Timeout（T-0523 D1 回归）"
    )


def test_全局超时与显式放宽并存():
    """全局 60s 必须仍在位：慢用例靠显式 mark 放宽，快用例靠全局看住，不许删全局预算。"""
    ini = (ROOT / 'pytest.ini').read_text(encoding='utf-8')
    assert '--timeout=60' in ini, (
        'pytest.ini 全局 --timeout=60 被移除——「快用例全局看住 + 慢用例显式放宽」'
        '的契约被破坏，真 hang 的用例会永远挂着（T-0523 D1）'
    )


# --------------------------------------------------------------------------- #
# D2 · 轻量 E2E：目标 complete 落 goal/change 事件 + 台账相位推进
# --------------------------------------------------------------------------- #
DRIVER = '''
从 web服务器 导入 Web服务端
从 会话存储 导入 会话存储
从 总入口 导入 组装注册表
从 文件系统 导入 路径连接
从 字符串处理 导入 编码
从 JSON 导入 序列化JSON
从 流 导入 造块开始, 造文本增量, 造工具调用增量, 造块结束, 造结束, 造停止原因, 造工具调用原因
从 认证 导入 初始化认证
从 目标工具 导入 取目标台账
从 内置核心字典 导入 字典键列表, 字典获取

类 模拟客户端:
  属性 模型名 等于 "mock"
  属性 轮数 等于 0
  段落 构造:
    设 己.模型名 为 "mock"
    设 己.轮数 为 0
  段落 对话响应(消息表, 选项表, 工具表, 增量回调 = 空):
    设 己.轮数 为 己.轮数 + 1
    如果 己.轮数 == 1:
      返回 [造块开始(0, "text"), 造文本增量(0, "第一轮推进完成"), 造块结束(0, ["type": "text", "text": "第一轮推进完成"]), 造结束(造停止原因())]
    如果 己.轮数 == 2:
      设 参 为 序列化JSON(["动作": "complete"])
      返回 [造块开始(0, "tool_call"), 造工具调用增量(0, "g1", "目标", 参), 造块结束(0, ["type": "tool-call", "id": "g1", "name": "目标", "arguments": 参]), 造结束(造工具调用原因())]
    # complete 执行后的工具结果回填请求：回文本收尾（否则会无限再发 complete 直到步数上限）
    返回 [造块开始(0, "text"), 造文本增量(0, "目标已完成"), 造块结束(0, ["type": "text", "text": "目标已完成"]), 造结束(造停止原因())]

初始化认证()
设 根 为 "{root}"
设 库 为 新建 会话存储(路径连接(根, "sessions"))
设 服务 为 新建 Web服务端()
服务.设置会话库(库)
设 客户端 为 新建 模拟客户端()
服务.配置(客户端, 组装注册表(), 根, 30.0, "", 空)
设 体 为 序列化JSON(["model": "mock", "session_id": "t0499-goal", "messages": [["role": "user", "content": "/goal T0499 轻量目标收口"]]])
设 应 为 服务.处理对话(["方法": "POST", "路径": "/v1/chat/completions", "头": {{}}, "体": 编码(体)], "", "")
打印("状态=" + 转字符串(应["状态"]))
打印("错误体=" + 转字符串(应["体"]))
打印("轮数=" + 转字符串(客户端.轮数))
设 标识 为 ""
遍历 键 之 字典键列表(服务.会话表):
  设 标识 为 键
设 会 为 服务.会话表[标识]
设 全 为 序列化JSON(会.汇集全部事件())
打印("含变更=" + 转字符串(全.包含("goal/change")))
设 台账 为 取目标台账()
如果 台账 != 空:
  设 目标视图 为 字典获取(台账, "目标", {{}})
  打印("台账phase=" + 转字符串(字典获取(目标视图, "phase", "")))
否则:
  打印("台账phase=空")
'''


def _lp(p) -> str:
    return str(p).replace('\\', '/')


def _find_sibling(name):
    """运行时依赖的兄弟仓定位（沿祖先逐级找，含 duan-light-merge 主仓内层；T-0395/T-0397 口径）。"""
    key = 'lightplugin' if name == 'LIGHTPLUGIN' else 'light-merge'
    env_name = os.environ.get(name, '')
    if env_name:
        return os.path.normpath(env_name)
    cands = []
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        cands.append(os.path.join(here, key))
        cands.append(os.path.join(here, 'duan-light-merge', key))
    cands.append(os.path.join('G:/dswork/duan-light-merge', key))
    for c in cands:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _env():
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_MODEL_CONTEXT_WINDOW')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _run_driver(src, tmp_path):
    """driver 末尾统一追加结束标记行；子进程见标记即 kill（T-0523 D1：唤醒线程挡退出）。"""
    f = tmp_path / 'driver.light'
    f.write_text(src + f'\n打印("{DONE_MARK}")\n', encoding='utf-8')
    proc = subprocess.Popen(
        [sys.executable, str(RUNNER), str(f)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding='utf-8', errors='replace',
        cwd=str(tmp_path), env=_env(),
    )
    buf = []
    reader = threading.Thread(target=lambda: buf.extend(iter(proc.stdout)), daemon=True)
    reader.start()
    deadline = time.time() + TIMEOUT_SEC
    done = False
    while time.time() < deadline:
        if DONE_MARK in ''.join(buf):
            done = True
            break
        time.sleep(0.2)
    try:
        proc.kill()
    except Exception:
        pass
    reader.join(timeout=10)
    out = ''.join(buf)
    if not done:
        raise subprocess.TimeoutExpired([sys.executable, str(RUNNER), str(f)],
                                        TIMEOUT_SEC, output=out)
    kv = {}
    for line in out.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return 0, out, kv


@pytest.mark.timeout(300)
def test_目标complete落goalchange事件且台账推进(tmp_path):
    # T-0523 D2 回归锁：真起 Light 服务进程（driver 子进程）走 /goal → 2 轮 → complete。
    # 冷启动约 59s，全局 60s 会先杀，显式 mark(300)（同 D1 契约）。
    #
    # 短根（T-0523，同 T0395::test_对话首条消息 的修法）：会话存储把项目根整条
    #   转义编码成磁盘目录名（--<转义路径>--），pytest tmp_path 的超长中文名编码后
    #   超 Windows MAX_PATH(260) → 增量保存 500「会话保存失败」（错误体实锤：
    #   写 session.jsonl 失败于转义目录下）。改用系统 Temp 短根，业务断言不变。
    根基 = Path(tempfile.mkdtemp(prefix='t0523-t0499'))
    try:
        结果 = None
        结果根 = None
        for 尝试 in (1, 2, 3):
            根 = 根基 / ('try' + str(尝试))
            根.mkdir()
            try:
                本次 = _run_driver(DRIVER.format(root=_lp(根)), 根)
            except subprocess.TimeoutExpired as e:
                本次 = (-1, (e.output or b'').decode('utf-8', 'replace') if isinstance(e.output, bytes) else (e.output or ''), {'状态': 'timeout'})
            结果 = 本次
            结果根 = 根
            if 本次[0] == 0 and 本次[2].get('状态') == '200':
                break
        assert 结果 is not None
        rc, out, kv = 结果
        assert rc == 0, f'driver 失败 rc={rc}\n{out}'

        assert kv['状态'] == '200', f'对话失败（3 次全新驱动均失败，非偶发抖动）\n{out}'
        assert kv['轮数'] == '3', (
            f'模型请求应正好 3 次（turn1 文本 1 次 + turn2 工具调用 1 次 + 工具结果回填收尾 1 次），'
            f'续跑正好 2 轮后由目标工具收口，实际 {kv["轮数"]}\n{out}'
        )
        assert kv['含变更'] == 'True', (
            f'模型 complete 必须落成 goal/change 事件（否则续跑读不到 phase）\n{out}'
        )
        assert kv['台账phase'] == 'complete', (
            f'工具执行后 新状态 必须挂回台账，续跑决策才能看到 complete\n{out}'
        )

        # 会话 JSONL 精确断言：goal/change 的 operation 与 phase（对齐 T0407 判据口径）
        hits = [q for q in (结果根 or 根基).rglob('session.jsonl')]
        assert hits, f'找不到会话 JSONL\n{out}'
        rows = []
        for q in hits:
            for line in q.read_text(encoding='utf-8', errors='replace').splitlines():
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        pass
        变更 = [e for e in rows if e.get('type') == 'goal/change']
        assert 变更, f'会话 JSONL 里没有 goal/change 事件\n{out}'
        assert 变更[-1]['data'].get('operation') == 'complete', 变更[-1]
        assert 变更[-1]['data']['goal'].get('phase') == 'complete', 变更[-1]
    finally:
        shutil.rmtree(根基, ignore_errors=True)

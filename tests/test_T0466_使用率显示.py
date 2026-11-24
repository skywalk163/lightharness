# -*- coding: utf-8 -*-
"""T-0466：上下文使用率显示准确率整改（928% 假爆满）。

现场：Web GUI 顶部统计 `in 267680 out 26980 | 累计 605096 | 使用率 928%`，
同类 DSH 显示 15% 左右。两处口径错位：
  1) 分母用了 `压缩配置()` 的缺省窗口 32768（HARNESS_MODEL_CONTEXT_WINDOW），
     而当前模型 `buddy/hy4flash-free` 的目录窗口是 1,000,000；
  2) 分子用了 `本轮输入 + 本轮输出`，而 `代理.light` 的本轮输入是**一轮内
     所有 step / 工具往返的累加**，不是「当前驻留上下文 token」。

本文件判四件事（黑盒 .light 片段 + 前端文本断言，不碰实现细节）：
  A. 267680/26980 + 真窗口 1,000,000 → 使用率 ≤ 100 且等于按新口径（prompt_tokens）算的值；
  B. 窗口缺省场景取真实模型窗口：内置目录命中 → 1,000,000；jet-hub 缓存命中 → 1,000,000；
  C. 占用超过窗口时封顶 100（不再出现 928% 这种数字）；
  D. 没有模型侧上报时回退「本轮累计」并在帧里标注口径（口径可核对，不静默）。
  E. 前端 app.js 含封顶逻辑（文本断言，避免回归到 928%）。
"""
import os
import subprocess
import sys
import tempfile

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')

# 编译 web服务器 及其依赖树要几十秒（冷缓存更久），单个用例硬超时给足
pytestmark = pytest.mark.timeout(900)

_片段 = r'''
从 web服务器 导入 Web服务端

# 假会话：只实现统计口径要用到的 查询事件（返回 assistant/message 记录表）
类 假会话:
  属性 记录表 等于 []
  段落 构造(表):
    设 己.记录表 为 表
  段落 查询事件(种类, 起始, 末):
    返回 己.记录表

# 按「每步上报的 prompt_tokens」造会话事件表（最后一个值即当前驻留上下文）
段落 造会话(输入表):
  设 表 为 []
  设 序 为 1
  遍历 值 之 输入表:
    设 行 为 ["序号": 序, "数据": ["用量": ["输入": 值, "输出": 100]]]
    表.追加(行)
    设 序 为 序 + 1
  返回 新建 假会话(表)

段落 主程序:
  # ---- A：928% 现场的等价输入（本轮输入 267680 / 输出 26980 / 真窗口 1,000,000）----
  设 服务 为 新建 Web服务端()
  服务.最近统计模型 为 "deepseek-flash"
  服务.计量器.记录响应(["输入token": 267680, "输出token": 26980])
  设 忽略1 为 服务.重算上下文占用(造会话([267680]))
  设 统计 为 服务.生成统计事件()
  打印("A_PCT=" + 转字符串(统计["上下文使用率"]))
  打印("A_WIN=" + 转字符串(统计["上下文窗口"]))
  打印("A_SRC=" + 转字符串(统计["窗口来源"]))
  打印("A_KJ=" + 转字符串(统计["占用口径"]))
  打印("A_OCC=" + 转字符串(统计["上下文占用"]))
  打印("A_IN=" + 转字符串(统计["本轮输入"]))
  打印("A_OUT=" + 转字符串(统计["本轮输出"]))
  打印("A_ENVWIN=" + 转字符串(服务.上下文窗口))

  # ---- B1：jet-hub 已缓存目录命中（buddy/hy4flash-free = 1,000,000）----
  设 服务2 为 新建 Web服务端()
  服务2.最近统计模型 为 "buddy/hy4flash-free"
  设 缓存 为 [["id": "buddy/hy4flash-free", "名称": "Hy4 Flash Free", "上下文窗口": 1000000]]
  服务2.设置枢纽缓存(缓存)
  服务2.计量器.记录响应(["输入token": 267680, "输出token": 26980])
  设 忽略2 为 服务2.重算上下文占用(造会话([267680]))
  设 统计2 为 服务2.生成统计事件()
  打印("B_WIN=" + 转字符串(统计2["上下文窗口"]))
  打印("B_SRC=" + 转字符串(统计2["窗口来源"]))
  打印("B_PCT=" + 转字符串(统计2["上下文使用率"]))

  # ---- B2：目录里也没有 → 回退环境默认，并在帧里标注来源（不静默）----
  设 服务3 为 新建 Web服务端()
  服务3.最近统计模型 为 "no-such-vendor/no-such-model"
  服务3.计量器.记录响应(["输入token": 100, "输出token": 10])
  设 忽略3 为 服务3.重算上下文占用(造会话([100]))
  设 统计3 为 服务3.生成统计事件()
  打印("C_WIN=" + 转字符串(统计3["上下文窗口"]))
  打印("C_SRC=" + 转字符串(统计3["窗口来源"]))

  # ---- C：占用超过窗口 → 封顶 100 ----
  设 服务4 为 新建 Web服务端()
  服务4.最近统计模型 为 "deepseek-flash"
  服务4.计量器.记录响应(["输入token": 3000000, "输出token": 900000])
  设 忽略4 为 服务4.重算上下文占用(造会话([3000000]))
  设 统计4 为 服务4.生成统计事件()
  打印("D_PCT=" + 转字符串(统计4["上下文使用率"]))

  # ---- D：没有模型侧上报 → 回退「本轮累计」并标注口径 ----
  设 服务5 为 新建 Web服务端()
  服务5.最近统计模型 为 "deepseek-flash"
  服务5.计量器.记录响应(["输入token": 267680, "输出token": 26980])
  设 忽略5 为 服务5.重算上下文占用(造会话([]))
  设 统计5 为 服务5.生成统计事件()
  打印("E_KJ=" + 转字符串(统计5["占用口径"]))
  打印("E_OCC=" + 转字符串(统计5["上下文占用"]))
  打印("E_PCT=" + 转字符串(统计5["上下文使用率"]))

  打印("--- T0466 OK ---")
'''


def _run_片段():
    """在隔离临时目录跑一次 .light 片段，返回 KEY -> 值 的字典。"""
    tmp = tempfile.mkdtemp(prefix='t0466-')
    src = os.path.join(tmp, 'probe.light')
    with open(src, 'w', encoding='utf-8') as f:
        f.write(_片段)
    env = dict(os.environ)
    # 隔离宿主环境：压缩配置的窗口默认值必须回到 32768，否则「环境默认」这条判据不可复现
    for _k in ('HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_MODEL', 'HARNESS_ENDPOINT',
               'HARNESS_API_KEY', 'HARNESS_ROOT', 'HARNESS_CWD'):
        env.pop(_k, None)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    p = subprocess.run([sys.executable, RUNNER, src], cwd=tmp, env=env,
                       capture_output=True, text=True, encoding='utf-8', errors='replace')
    assert p.returncode == 0, '片段执行失败（退出码 %s）\nSTDOUT:\n%s\nSTDERR:\n%s' % (
        p.returncode, p.stdout[-4000:], p.stderr[-4000:])
    out = {}
    for line in (p.stdout or '').splitlines():
        line = line.strip()
        if '=' in line and not line.startswith('-'):
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    assert '--- T0466 OK ---' in (p.stdout or ''), '片段没有跑到结尾：\n%s' % (p.stdout[-3000:],)
    return out


@pytest.fixture(scope='module')
def 结果():
    return _run_片段()


def _f(d, key):
    """取浮点值；缺失直接失败（比静默 0 好排查）。"""
    assert key in d, '片段输出缺字段 %s：%s' % (key, sorted(d))
    return float(d[key])


# --------------------------------------------------------------------------- #
# A. 928% 现场：使用率必须 ≤ 100，且按「当前占用 / 真实窗口」算
# --------------------------------------------------------------------------- #
def test_A_使用率不超100且按当前占用算(结果):
    pct = _f(结果, 'A_PCT')
    occ = _f(结果, 'A_OCC')
    win = _f(结果, 'A_WIN')
    assert pct <= 100.0, '使用率仍可能爆表：%s' % pct
    # 新口径：占用来最后一次请求上报的 prompt_tokens（267680），不是本轮累计（294660）
    assert 结果['A_KJ'] == 'prompt_tokens', '占用口径没切到 prompt_tokens：%s' % 结果['A_KJ']
    assert occ == 267680, '占用取错：%s' % occ
    assert win == 1000000, '分母没用真实模型窗口：%s' % win
    # 267680 / 1000000 = 26.768% → 一位小数 26.8
    assert abs(pct - round(occ / win * 100.0, 1)) < 1e-6, '使用率与口径不符：%s' % pct
    assert abs(pct - 26.8) < 0.11, '使用率数值异常：%s' % pct
    # 旧口径（本轮输入+输出 294660）算出来是 29.5% —— 新值必须比它小（分子不再累加）
    assert pct < round((267680 + 26980) / 1000000.0 * 100.0, 1), '分子仍是本轮累加'
    # 分母不是压缩阈值默认值：服务端 上下文窗口（压缩配置口径）仍是 32768
    assert _f(结果, 'A_ENVWIN') == 32768.0, '压缩窗口口径被误改（红线）：%s' % 结果['A_ENVWIN']
    assert 结果['A_SRC'] == '模型目录', '窗口来源没标注：%s' % 结果['A_SRC']


# --------------------------------------------------------------------------- #
# B. 窗口缺省场景：取真实模型窗口（内置目录 / jet-hub 缓存），不是 32768
# --------------------------------------------------------------------------- #
def test_B_窗口跟随真实模型(结果):
    assert _f(结果, 'B_WIN') == 1000000, 'jet-hub 窗口没生效：%s' % 结果['B_WIN']
    assert 结果['B_SRC'] == 'jet-hub', '窗口来源没标注：%s' % 结果['B_SRC']
    assert abs(_f(结果, 'B_PCT') - 26.8) < 0.11, '使用率异常：%s' % 结果['B_PCT']


def test_B2_取不到时回退并标注来源(结果):
    # 目录全不命中 → 回退到压缩配置同源的窗口，且来源写明（可核对，不静默当真实窗口）
    assert _f(结果, 'C_WIN') == 32768.0, '回退窗口异常：%s' % 结果['C_WIN']
    assert 结果['C_SRC'] == '环境默认', '回退来源没标注：%s' % 结果['C_SRC']


# --------------------------------------------------------------------------- #
# C. 溢出封顶：占用 3,000,000 / 窗口 1,000,000 → 100.0（不是 300）
# --------------------------------------------------------------------------- #
def test_C_溢出封顶100(结果):
    pct = _f(结果, 'D_PCT')
    assert pct == 100.0, '溢出不封顶：%s' % pct


# --------------------------------------------------------------------------- #
# D. 没有 prompt_tokens 上报：回退本轮累计，并在帧里写明口径
# --------------------------------------------------------------------------- #
def test_D_无上报时回退本轮累计并标注(结果):
    assert 结果['E_KJ'] == '本轮累计', '回退口径没标注：%s' % 结果['E_KJ']
    assert _f(结果, 'E_OCC') == 294660.0, '回退占用异常：%s' % 结果['E_OCC']
    assert abs(_f(结果, 'E_PCT') - 29.5) < 0.11, '回退使用率异常：%s' % 结果['E_PCT']


# --------------------------------------------------------------------------- #
# E. 前端封顶（文本断言）
# --------------------------------------------------------------------------- #
def _app_js():
    with open(os.path.join(ROOT, 'webui', 'app.js'), encoding='utf-8') as f:
        return f.read()


def test_E_前端使用率封顶():
    js = _app_js()
    assert 'function clampUsagePct(' in js, '前端没有封顶函数'
    assert 'function formatUsagePct(' in js, '前端没有统一的百分比文案'
    assert 'USAGE_MAX = 100' in js, '封顶值不是 100'
    assert 'n > USAGE_MAX' in js, '溢出判定缺失'
    assert '"%" + (isUsageOverflow(pct) ? "+" : "")' in js, '溢出没有显示 100%+'
    # 顶栏统计与输入区用量都走封顶文案（928% 不再可能被直接打印出来）
    assert 'formatUsagePct(pct)' in js, '顶栏统计没走封顶文案'
    assert 'clampUsagePct(pct)' in js, '使用率没走封顶'
    # 判色用封顶后的值
    assert 'pctSafe > 95' in js and 'pctSafe > 80' in js, '颜色阈值没跟封顶口径同步'
    # 不允许出现把原始百分比直接拼进文案的旧写法
    assert '"%使用率 " + Math.round(pct)' not in js and '" | 使用率 " + Math.round(pct)' not in js

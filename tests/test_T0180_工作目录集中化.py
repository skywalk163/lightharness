# -*- coding: utf-8 -*-
"""T-0180 工作目录集中化：四条判据，其中两条是**反证用例**。

要解决的三套并行 cwd
---------------------
改之前 cwd 有三个互不引用的来源：

1. 进程级全局：`工具_路径安全.取根目录()` = `环境变量("HARNESS_ROOT", 当前目录())`；
2. 启动目录：`cli外壳` / `web服务器` / `mcp接线` / `总入口` 各自调 `当前目录()`；
3. 会话头信息：`会话.构造` 把 `工作目录` 写进 `"头信息"`，但全仓没有模块读它做路径判定（死数据）。

后果是 `..` 越界按**全局根**判定：会话根外、全局根内的目录会被放过（本文件用例 1 就是这条）。

为什么用例 1、2 是反证
----------------------
它们断言的是「拒绝」与「各用各的根」。如果实现没生效（`取根目录` 仍无视会话 cwd），
那么 `根` 会退回 `当前目录()`（用例里 = a、b 的**父目录**），`../b/x.txt` 恰好落在父目录内
→ `ok` 变 真 → 用例红。也就是说：**旧实现下这两条必红**，不是「怎么写都绿」的摆设。

用例 1 里还额外断言了「会话根内的文件必须放行」，防止「一律拒绝」这种假通过。

关于 HARNESS_ROOT
-----------------
卡面「目标 3」把 `HARNESS_ROOT` 定为**强制覆盖（优先级最高）**，而「验收 1」又描述
「越出会话根、但在全局 HARNESS_ROOT 之内 → 必须拒绝」。两者冲突：若 HARNESS_ROOT 真能覆盖，
它就不可能被会话根否决。本文件按「目标 3」为准，把用例 1 的「全局根」落在
`当前目录()` 兜底这一级（不设 HARNESS_ROOT）——判据照样有牙，且与实现语义自洽。
`HARNESS_ROOT` 的强制覆盖行为另有断言（用例 5），不留空档。
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')

# 首次跑要起编译器，给足余量；挂死必须被抓出来
TIMEOUT_SEC = 120


def _light_path(p) -> str:
    """把宿主路径写成 .light 字符串字面量：用正斜杠，避免反斜杠被当转义。"""
    return str(p).replace('\\', '/')


def _same(a: str, b: str) -> bool:
    """跨平台路径比较：分隔符与大小写差异不算不同。"""
    norm = lambda s: os.path.normcase(os.path.normpath(s.strip()))
    return norm(a) == norm(b)


def _run(src: str, tmp_path, cwd=None):
    """在独立子进程里跑一段光明驱动脚本，返回 (rc, stdout, {键: 值})。

    驱动脚本统一用 `打印("键=" + 值)` 输出，这里把行解析成字典，断言就不依赖行序。
    """
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')

    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    # 这两个变量一旦从宿主漏进来，用例 1/2 的「全局根」就不确定了，判据会被打空
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
    return p.returncode, p.stdout, kv


def _ok(kv: dict, key: str) -> bool:
    """把光明打印出来的 真/假 转成 bool（转字符串(真) → "True"）。"""
    raw = kv.get(key, '')
    assert raw in ('True', 'False'), f'{key} 不是布尔打印：{raw!r}\n{kv}'
    return raw == 'True'


# --------------------------------------------------------------------------- #
# 用例 1（反证）：会话根优先于全局根
# --------------------------------------------------------------------------- #

def test_会话根优先于全局根_越界必须拒绝(tmp_path):
    """会话 cwd = a，`../b/x.txt` 落在「全局根」（= 当前目录 = a 的父）内，也必须拒绝。

    旧实现（根只有 HARNESS_ROOT/当前目录）会放行这条 —— 所以这条红就说明实现没生效。
    """
    a = tmp_path / 'a'
    b = tmp_path / 'b'
    a.mkdir()
    b.mkdir()
    (a / 'self.txt').write_text('a 自己的文件', encoding='utf-8')
    (b / 'x.txt').write_text('b 的文件', encoding='utf-8')

    src = f'''
从 会话 导入 新建会话
从 工具_路径安全 导入 取根目录, 解析安全路径

设 甲 为 新建会话("s_a", "{_light_path(a)}")
设 根 为 取根目录(甲.取工作目录())
打印("根=" + 根)
打印("越界=" + 转字符串(解析安全路径(根, "../b/x.txt")["ok"]))
打印("会话内=" + 转字符串(解析安全路径(根, "self.txt")["ok"]))
'''
    rc, out, kv = _run(src, tmp_path, cwd=tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'

    assert _same(kv['根'], str(a)), f'根没取会话 cwd：{kv["根"]}'
    assert _ok(kv, '越界') is False, (
        '越出会话根的路径被放行了 —— 路径判定仍在按全局根走（实现未生效）\n' + out
    )
    # 防「一律拒绝」的假通过：会话根内的文件必须放行
    assert _ok(kv, '会话内') is True, f'会话根内文件被误拒\n{out}'


# --------------------------------------------------------------------------- #
# 用例 2（反证）：同进程双会话各用各的根
# --------------------------------------------------------------------------- #

def test_同进程双会话各用各的根(tmp_path):
    """同一进程里会话 A(cwd=a) 与 B(cwd=b)：各自读自己目录成功，A 读 B 的必须拒绝。

    旧实现只有一个全局根，两条「读自己」不可能同时成立（其中一条必被拒），
    所以这条同样是反证。
    """
    a = tmp_path / 'a'
    b = tmp_path / 'b'
    a.mkdir()
    b.mkdir()
    (a / 'own.txt').write_text('A', encoding='utf-8')
    (b / 'own.txt').write_text('B', encoding='utf-8')

    src = f'''
从 会话 导入 新建会话
从 工具_路径安全 导入 取根目录, 解析安全路径

设 甲 为 新建会话("s_a", "{_light_path(a)}")
设 乙 为 新建会话("s_b", "{_light_path(b)}")
设 根甲 为 取根目录(甲.取工作目录())
设 根乙 为 取根目录(乙.取工作目录())
打印("根甲=" + 根甲)
打印("根乙=" + 根乙)
打印("甲读自己=" + 转字符串(解析安全路径(根甲, "own.txt")["ok"]))
打印("乙读自己=" + 转字符串(解析安全路径(根乙, "own.txt")["ok"]))
打印("甲读乙=" + 转字符串(解析安全路径(根甲, "../b/own.txt")["ok"]))
'''
    rc, out, kv = _run(src, tmp_path, cwd=tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'

    assert _same(kv['根甲'], str(a)), f'会话 A 的根不对：{kv["根甲"]}'
    assert _same(kv['根乙'], str(b)), f'会话 B 的根不对：{kv["根乙"]}'
    assert _ok(kv, '甲读自己') is True, f'会话 A 读自己目录被拒\n{out}'
    assert _ok(kv, '乙读自己') is True, f'会话 B 读自己目录被拒\n{out}'
    assert _ok(kv, '甲读乙') is False, f'会话 A 读到了 B 的文件（越界未拦）\n{out}'


# --------------------------------------------------------------------------- #
# 用例 3：派生字段分离
# --------------------------------------------------------------------------- #

def test_派生子目录_cwd_与_originCwd_分离(tmp_path):
    """`派生子目录(父, 子)` 必须同时给出「子生效目录」和「父源目录」，子候选为空时两者回退相等。"""
    parent = tmp_path / '父'
    parent.mkdir()

    src = f'''
从 工作目录 导入 派生子目录

设 一 为 派生子目录("{_light_path(parent)}", "子")
打印("cwd=" + 一["cwd"])
打印("origin=" + 一["originCwd"])
设 二 为 派生子目录("{_light_path(parent)}", "")
打印("cwd2=" + 二["cwd"])
打印("origin2=" + 二["originCwd"])
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'

    assert _same(kv['cwd'], str(parent / '子')), f'子生效目录不对：{kv["cwd"]}'
    assert _same(kv['origin'], str(parent)), f'父源目录不对：{kv["origin"]}'
    assert _same(kv['cwd2'], str(parent)), f'空子候选应回退父目录：{kv["cwd2"]}'
    assert _same(kv['origin2'], str(parent)), f'空子候选应回退父目录：{kv["origin2"]}'


# --------------------------------------------------------------------------- #
# 用例 4：运行时断言（目录被删后给理由，不抛裸异常）
# --------------------------------------------------------------------------- #

def test_断言可用_目录被删后返回假且给理由(tmp_path):
    """会话目录建好后被删，`断言可用` 必须返回 ok=假 + 理由，且进程正常退出（不抛裸异常）。"""
    target = tmp_path / '活目录'

    src = f'''
从 工作目录 导入 断言可用
从 文件系统 导入 创建目录, 删除目录

设 目标 为 "{_light_path(target)}"
创建目录(目标)
设 建后 为 断言可用(目标)
打印("建后=" + 转字符串(建后["ok"]))
删除目录(目标)
设 删后 为 断言可用(目标)
打印("删后=" + 转字符串(删后["ok"]))
打印("理由=" + 删后.获取("理由", ""))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'断言可用 抛了裸异常（应降级为 ok=假）rc={rc}\n{out}'

    assert _ok(kv, '建后') is True, f'存在的目录被判不可用\n{out}'
    assert _ok(kv, '删后') is False, f'目录已删却仍判可用\n{out}'
    assert kv['理由'].strip(), f'ok=假 时必须给理由\n{out}'
    assert str(target.name) in kv['理由'] or '工作目录' in kv['理由'], (
        f'理由里应能看出是哪个目录的问题：{kv["理由"]}'
    )


# --------------------------------------------------------------------------- #
# 用例 5：HARNESS_ROOT 仍是强制覆盖（卡面红线「不废除 HARNESS_ROOT」）
# --------------------------------------------------------------------------- #

def test_HARNESS_ROOT_仍是强制覆盖(tmp_path):
    """设了 HARNESS_ROOT 时，即使传了会话 cwd 也以环境变量为准 —— 红线不许被这次改动破坏。"""
    a = tmp_path / 'a'
    override = tmp_path / '覆盖根'
    a.mkdir()
    override.mkdir()

    src = f'''
从 工具_路径安全 导入 取根目录

打印("零参=" + 取根目录())
打印("带会话=" + 取根目录("{_light_path(a)}"))
'''
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k != 'HARNESS_CWD'}
    env['HARNESS_ROOT'] = str(override)
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(tmp_path), env=env,
    )
    assert p.returncode == 0, f'驱动脚本失败 rc={p.returncode}\n{p.stdout}\n{p.stderr}'

    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    assert _same(kv['零参'], str(override)), f'零参调用没走 HARNESS_ROOT：{kv}'
    assert _same(kv['带会话'], str(override)), (
        f'HARNESS_ROOT 应强制覆盖会话 cwd（红线），实际 {kv["带会话"]}'
    )

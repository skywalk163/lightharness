# -*- coding: utf-8 -*-
# T-0526 回归判据：T-0490 起的「排队兜底唤醒线程」必须随 停止() 退出。
#
# 背景：排队唤醒循环 原先是 `当 真: time.sleep(2)` 的无出口死循环，非守护线程，
#   于是走过流式/排队路径的用例全部「断言过、进程退不出」，门禁只看到 timeout 红
#   （0.88 实测 90–120s 不返回，Windows 120s 不返回；faulthandler 栈：主线程停在
#   threading._shutdown，等 排队唤醒循环）。
#
# 本判据不看内部实现，只用外部可观察事实：
#   1) 5 条受影响的起服务用例里挑两个代表（流式推流E2E / R41 真实网络IO），
#      在独立临时 cwd 里跑：rc==0 且进程自己退出（墙钟不超 WALL_LIMIT）；
#
#   2) 「起服务 → 停止() → 再起一次」往返：确认不是「只能停一次」的假修，
#      并且 停止() 之后线程引用确实被 join 收空。
#
# 阈值说明（为什么不是 20s/25s）：本仓 pytest.ini 默认 addopts 带 -n 4，三个用例
#   并发各编译一遍光明，25s 硬超时会在负载高的机器上假红（0.88 load≈9.8 实测）；
#   故三条场景改成「同一个测试里顺序跑」，单跑实测：0.88 18.4–22.0s、Windows
#   25.9–28.5s（大头是光明编译）。上限取 35s / 硬超时 40s：既覆盖双平台正常退出，
#   又与原挂死态（>=90s 不返回）有 2.5 倍以上间距，不会把挂死放过去。
#
# 红线：只新增本文件，不改 examples/*.light（那是判据），不登记 flaky、不靠 skip。
import os
import subprocess
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNNER = os.path.join(ROOT, '运行.py')
EXAMPLES = os.path.join(ROOT, 'examples')

WALL_LIMIT = 35  # 秒：正常退出实测 18.4–28.5s（含光明编译）；挂死实测 >=90s 不返回
SUB_TIMEOUT = 40  # 秒：subprocess 硬超时，必须大于 WALL_LIMIT

pytestmark = pytest.mark.timeout(300)


def _env():
    env = dict(os.environ)
    env['HARNESS_PY'] = sys.executable
    env['HARNESS_WEB_NO_OPEN'] = '1'  # 门禁不弹浏览器（examples/运行Web服务器.light 约定）
    return env


def _run_entry(entry, cwd, timeout=SUB_TIMEOUT):
    """在独立临时 cwd 里跑一个 .light 入口 → (rc, 墙钟秒, 输出)。"""
    t0 = time.monotonic()
    p = subprocess.run(
        [sys.executable, RUNNER, entry],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=cwd, timeout=timeout, env=_env(),
    )
    return p.returncode, time.monotonic() - t0, (p.stdout or '') + (p.stderr or '')


# 「起服务 → 停止() → 再起一次」往返：同一实例连续两轮，第二轮必须能再起线程，
# 且每轮 停止() 后线程引用都被收空（只靠一次性 join 的假修会在这里露馅）。
_ROUND_TRIP = '''
从 web服务器 导入 Web服务端

段落 起停一次(服务, 根, 界面):
  设 无客户端 为 空
  设 空注册表 为 []
  服务.配置(无客户端, 空注册表, 根, 5.0, 界面)
  设 闸门 为 服务.取队列闸门()
  如果 服务.唤醒线程 == 空:
    抛出 新建 错误("取队列闸门后兜底唤醒线程没起来")
  服务.停止()
  如果 服务.唤醒线程 != 空:
    抛出 新建 错误("停止后兜底唤醒线程仍存活（join 没生效）")

段落 主程序:
  设 界面 为 ""
  设 根 为 当前目录()
  设 服务 为 新建 Web服务端()
  起停一次(服务, 根, 界面)
  打印("--- 第一轮 起服务/停止 完成 ---")
  起停一次(服务, 根, 界面)
  打印("--- 第二轮 起服务/停止 完成 ---")
  打印("--- T-0526 起停往返 通过 ---")
'''


def _must_exit(label, entry, cwd):
    """跑一条入口，返回 (rc, wall, out)；只对「超时」补一次重试。

    为什么只重试超时：机器负载高时光明编译本身能到 40s+（实测），补一次可区分
    「慢」与「挂死」；真挂死（T-0490 原态）两次都会超时，照样判红，不算放水。
    """
    last = None
    for attempt in (1, 2):
        try:
            return _run_entry(entry, cwd), attempt
        except subprocess.TimeoutExpired as exc:
            last = exc
    raise last


def test_起服务用例跑完必须自己退出(tmp_path):
    """三条场景顺序跑（避免 -n 4 下多条光明编译抢 CPU 造成假红）：

    ① test_流式推流E2E.light ② test_R41_真实网络IO.light ③ 同实例起停往返。
    任一条挂住 → subprocess 超时；断言过了但退不出（T-0490 的挂死态）也在这里现形。
    """
    failures = []
    report = []

    for name in ('test_流式推流E2E.light', 'test_R41_真实网络IO.light'):
        entry = os.path.join(EXAMPLES, name)
        assert os.path.isfile(entry), f'缺用例文件: {entry}'
        try:
            (rc, wall, out), attempt = _must_exit(name, entry, str(tmp_path))
        except subprocess.TimeoutExpired:
            failures.append(f'{name}: 两轮都 {SUB_TIMEOUT}s 内没退出（进程挂死）')
            report.append(f'{name}: TIMEOUT×2')
            continue
        ok = rc == 0 and wall < WALL_LIMIT
        report.append(f'{name}: rc={rc} wall={wall:.1f}s (第{attempt}轮)')
        if not ok:
            failures.append(
                f'{name}: rc={rc} wall={wall:.1f}s（要求 rc==0 且 < {WALL_LIMIT}s）\n{out[-2000:]}'
            )

    # ③ 起停往返：把 .light 入口写进临时目录，不往仓库里丢文件
    entry = tmp_path / '_t0526_roundtrip.light'
    entry.write_text(_ROUND_TRIP, encoding='utf-8')
    try:
        (rc, wall, out), attempt = _must_exit('起停往返', str(entry), str(tmp_path))
        ok = rc == 0 and wall < WALL_LIMIT and 'T-0526 起停往返 通过' in out
        report.append(f'起停往返: rc={rc} wall={wall:.1f}s (第{attempt}轮)')
        if not ok:
            failures.append(
                f'起停往返: rc={rc} wall={wall:.1f}s（要求 rc==0、< {WALL_LIMIT}s、且能看到通过标记）\n'
                f'{out[-2000:]}'
            )
    except subprocess.TimeoutExpired:
        failures.append(f'起停往返: 两轮都 {SUB_TIMEOUT}s 内没退出（第二轮又起了一条退不掉的线程？）')
        report.append('起停往返: TIMEOUT×2')

    assert not failures, '起服务用例退不出去（T-0490 兜底唤醒线程没随 停止() 退出）：\n' + \
                        '\n\n'.join(failures) + '\n\n实测：' + ' | '.join(report)

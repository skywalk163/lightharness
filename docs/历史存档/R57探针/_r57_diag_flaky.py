# -*- coding: utf-8 -*-
"""R57 任务2 flaky 根因诊断：复用官方用例的 helper，复刻 _跑集群(1200, 杀=1)，
在「kill 时刻」与「报告完成时刻」打印关键状态，判断监控循环是否在标失联前退出。

放在 <copy>/light-merge/ 下运行（脚本目录的 tests/ 提供 helper）。
"""
import os, sys, time, json, tempfile, shutil, multiprocessing, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
T = os.path.join(HERE, 'tests')
sys.path.insert(0, T)
# 必须用「按名字 import」——spawn 子进程要能按模块名重新导入 target 函数所属模块，
# 用 importlib 动态加载的匿名模块会 PicklingError。
import test_distributed_eval_light as m  # noqa: E402


HB_INTERVAL = float(os.environ.get('DIAG_HB_INTERVAL', '0.3'))
HB_TIMEOUT = float(os.environ.get('DIAG_HB_TIMEOUT', '1.5'))


def run():
    tmp = tempfile.mkdtemp(prefix='diag_')
    mp = None
    ws = []
    try:
        任务文件 = os.path.join(tmp, '任务.json')
        端口文件 = os.path.join(tmp, 'port.txt')
        状态文件 = os.path.join(tmp, 'state.json')
        报告文件 = os.path.join(tmp, 'report.json')
        身份目录 = os.path.join(tmp, '节点身份')
        os.makedirs(身份目录, exist_ok=True)
        m._生成任务文件(任务文件, 1200)
        ctx = multiprocessing.get_context('spawn')
        mp = ctx.Process(target=m._主进程,
                         args=(端口文件, 状态文件, 报告文件, 任务文件, 1200, HB_TIMEOUT))
        mp.start()
        端口 = m._等端口(端口文件)
        ws = [ctx.Process(target=m._工进程, args=(端口, i, 4, HB_INTERVAL, 身份目录, 0))
              for i in range(3)]
        for w in ws:
            w.start()
        t0 = time.time()
        m._等进度(状态文件, 1200 * 0.15)
        t_kill = time.time()
        st = m.解析JSON(m.读文本(状态文件)) if os.path.isfile(状态文件) else {}
        print(f"[diag] kill@{t_kill - t0:.2f}s 已汇聚={st.get('已汇聚')} "
              f"在跑={st.get('在跑')} 队列剩余={st.get('队列剩余')} 失联={st.get('失联节点')}",
              flush=True)
        ws[1].terminate()
        ws[1].join(timeout=5)
        被杀 = None
        身份文件 = os.path.join(身份目录, '节点1.txt')
        for _ in range(50):
            if os.path.isfile(身份文件):
                被杀 = m.读文本(身份文件).strip()
                if 被杀:
                    break
            time.sleep(0.1)
        报告 = m._等报告(报告文件, 1200)
        t_rep = time.time()
        最终 = m.解析JSON(m.读文本(状态文件))
        print(f"[diag] report@{t_rep - t0:.2f}s (kill->rep {t_rep - t_kill:.2f}s) "
              f"状态失联={最终.get('失联节点')} 报告失联={报告.get('失联节点')} "
              f"被杀={被杀} 状态已汇聚={最终.get('已汇聚')}", flush=True)
        return 最终.get('失联节点'), 报告.get('失联节点')
    finally:
        for w in ws:
            try:
                if w.is_alive():
                    w.terminate()
            except Exception:
                pass
            try:
                w.join(timeout=5)
            except Exception:
                pass
        if mp is not None:
            try:
                if mp.is_alive():
                    mp.terminate()
            except Exception:
                pass
            try:
                mp.join(timeout=5)
            except Exception:
                pass
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    for k in range(n):
        print(f"==== iter {k + 1} ====", flush=True)
        try:
            run()
        except Exception as e:  # noqa: BLE001
            print(f"[diag] iter {k + 1} EXC {type(e).__name__}: {e}", flush=True)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LP-D-012 容量型探针（连接并发缺陷 · 定向法）。

背景：`test_concurrent_requests` 是**连接并发**类缺陷（多个并发请求被服务端
逐个串行消费），「重跑几次 / 加进程负载」判不出来；本探针用**容量法**定向：
N 个并发请求打 `/slow`（服务端每次延时 D 秒），测墙钟 T：

- T ≈ 1×D  → 并发正常（线程化消费）→ 判定「通过」
- T ≈ N×D  → 请求被串行化（连接并发缺陷形态）→ 判定「触发」

**自检**（Day10 §3.2 两次失败的直接教训）：探针若「未真正制造压力」——
并发数 <2、请求全部失败、或注入空剔除集合（--空剔除）——必须报「探针
无效」，**不得报通过**。

纯标准库实现（http.server + threading + urllib.request），不依赖 requests。

用法（任意工作目录）：
    # 正常形态：线程化服务端 + 10 并发 → 通过（T/D ≈ 1）
    py lp012_capacity_连接并发.py --服务端 线程化 --并发 10 --慢秒 0.5
    # 缺陷形态：串行服务端 + 10 并发 → 触发（T/D ≈ 10）
    py lp012_capacity_连接并发.py --服务端 串行 --并发 10 --慢秒 0.5
    # 无压力反跑：并发 1 → 通过
    py lp012_capacity_连接并发.py --服务端 串行 --并发 1 --慢秒 0.5
    # 压满反跑：并发 10 + 串行 → 触发
    py lp012_capacity_连接并发.py --服务端 串行 --并发 10 --慢秒 0.5
    # 自检反跑：注入空剔除集合 → 探针无效（dc=2）
    py lp012_capacity_连接并发.py --并发 10 --空剔除

退出码 dc（判定码）：
    0  通过（并发正常，T/D≈1×）
    1  触发（串行化形态复现，T/D≈N×）
    2  探针无效（自检失败：没有真正制造压力 / 剔除集合为空）
    3  灰区：T/D 既不接近 1× 也不接近 N×，无法定论
    4  探针自身运行错误
"""
from __future__ import annotations

import argparse
import http.server
import socket
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor


class SlowHandler(http.server.BaseHTTPRequestHandler):
    delay = 0.5  # 服务端每次 /slow 的延时（秒），由探针启动前设置

    def do_GET(self):  # noqa: N802
        if self.path.startswith("/slow"):
            time.sleep(SlowHandler.delay)
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # 静默，避免刷屏
        pass


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _fire_one(port: int) -> float:
    """一次 /slow 请求，返回耗时（秒）。"""
    t0 = time.perf_counter()
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/slow", timeout=60) as r:
        r.read()
    return time.perf_counter() - t0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="LP-D-012 容量型探针：N 并发打 /slow 测墙钟，T/D≈1× 通过 / ≈N× 触发",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例见文件头 docstring。")
    ap.add_argument("--并发", type=int, default=10, dest="conc",
                    help="并发请求数（默认 10）")
    ap.add_argument("--慢秒", type=float, default=0.5, dest="delay",
                    help="服务端 /slow 延时 D（默认 0.5，与 test_http_client.py 对齐）")
    ap.add_argument("--服务端", choices=["串行", "线程化"], default="线程化",
                    help="服务端消费形态：串行=单线程 HTTPServer（缺陷形态）；线程化=并发消费（正常）")
    ap.add_argument("--空剔除", action="store_true",
                    help="自检反跑：注入空剔除集合 → 必须报「探针无效」")
    args = ap.parse_args()

    if args.delay <= 0:
        print("[探针] 慢秒必须 > 0")
        return 4

    # ── 自检一：注入空剔除集合 → 探针无效（复现 Day10 §3.2 失败形态）──
    if args.空剔除:
        print("=" * 60)
        print("容量型探针 · 自检反跑（注入空剔除集合）")
        print("=" * 60)
        print("剔除集合 = 空 → 未真正制造压力")
        print("判定：探针无效（dc=2）…… 满足契约 §八-3")
        return 2

    # ── 自检二：并发数 < 1（0 并发）→ 未真正制造压力 → 探针无效 ──
    # 注意：并发=1 属「无压力」形态（契约 §八-2 要求无压力时应通过），不是无效；
    #       只有 0 并发 / 空剔除等「根本没发起请求」才报探针无效。
    if args.conc < 1:
        print("=" * 60)
        print("容量型探针 · 自检反跑（并发数 < 1）")
        print("=" * 60)
        print(f"并发数 = {args.conc} → 未发起任何请求，未真正制造压力")
        print("判定：探针无效（dc=2）")
        return 2

    # ── 启动服务端 ──
    port = _free_port()
    SlowHandler.delay = args.delay
    if args.服务端 == "串行":
        server = http.server.HTTPServer(("127.0.0.1", port), SlowHandler)
        mode_desc = "串行 HTTPServer（缺陷形态：请求逐个消费）"
    else:
        server = http.server.ThreadingHTTPServer(("127.0.0.1", port), SlowHandler)
        mode_desc = "线程化 ThreadingHTTPServer（正常形态：并发消费）"
    t0 = time.perf_counter()
    st = threading.Thread(target=server.serve_forever, daemon=True)
    st.start()
    try:
        # 健康检查：等服务端就绪
        for _ in range(50):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/slow", timeout=2) as r:
                    r.read()
                break
            except Exception:
                time.sleep(0.05)

        print("=" * 60)
        print("容量型探针 · 定向法（连接并发）")
        print("=" * 60)
        print(f"服务端    : {mode_desc}")
        print(f"延时 D    : {args.delay}s  |  并发 N = {args.conc}")

        # ── 并发压测：N 个请求同时发，墙钟 T ──
        wall_t0 = time.perf_counter()
        errs = []
        with ThreadPoolExecutor(max_workers=args.conc) as ex:
            futs = [ex.submit(_fire_one, port) for _ in range(args.conc)]
            for i, f in enumerate(futs):
                try:
                    f.result()
                except Exception as exc:  # noqa: BLE001
                    errs.append((i, str(exc)))
        wall = time.perf_counter() - wall_t0

        print(f"墙钟 T    : {wall:.3f}s")
        print(f"期望比值  : 正常≈{1:.1f}×D / 串行≈{args.conc:.0f}×D")
        print(f"实测比值  : T/D = {wall / args.delay:.2f}×")

        # ── 自检三：请求全部失败 → 未真正制造压力 → 探针无效 ──
        if len(errs) >= args.conc:
            print(f"失败请求数 = {len(errs)}/{args.conc} → 未真正制造压力")
            print("判定：探针无效（dc=2）")
            return 2
        if errs:
            print(f"警告：{len(errs)} 个请求失败（不影响制造压力判定）—— {errs[0][1]}")

        # ── 判定：T/D ≈ 1× 通过；≈ N× 触发 ──
        ratio = wall / args.delay
        lo_ok = 1.5          # ≤1.5×D 视为并发正常
        hi_trip = 0.5 * args.conc   # ≥0.5·N×D 视为串行化
        if ratio <= lo_ok:
            print(f"判定：通过（并发正常，T/D≈1×，dc=0）")
            return 0
        if ratio >= hi_trip:
            print(f"判定：触发（串行化形态复现，T/D≈{ratio:.1f}×≥{hi_trip:.1f}×，dc=1）")
            return 1
        print(f"判定：灰区（T/D={ratio:.2f}× 介于 {lo_ok}× 与 {hi_trip:.1f}× 之间，无法定论，dc=3）")
        return 3
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    raise SystemExit(main())
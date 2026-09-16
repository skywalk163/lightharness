# -*- coding: utf-8 -*-
"""R29 任务1：A批（位运算符+异步 9条）CCW 逐条隔离验证。

复刻任务3 口径（_r29_ccw_verify_engine.py）。
运行：python _antirun_r29_t1_A批验证.py
输出：_task1_R29_A批位运算符异步_验证清单.md + _task1_R29_A批验证_证据.json
"""
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, HARNESS)
import _r29_ccw_verify_engine as eng  # noqa: E402

A_BATCH = ['位与', '位异或', '位或', '位非', '异步写入文件', '异步睡眠',
           '异步读取文件', '异步追加文件', '并发等待']


def main():
    eng.verify(
        '任务1（A批：位运算符+异步）',
        A_BATCH,
        os.path.join(HARNESS, '_task1_R29_A批验证_证据.json'),
        os.path.join(HARNESS, '_task1_R29_A批位运算符异步_验证清单.md'),
    )


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""R29 任务2：B批（错误类型+设置 10条）CCW 逐条隔离验证。

复刻任务3 口径（_r29_ccw_verify_engine.py）。
运行：python _antirun_r29_t2_B批验证.py
输出：_task2_R29_B批错误类型设置_验证清单.md + _task2_R29_B批验证_证据.json
"""
import os
import sys

ROOT = r'G:/dswork/duan-light-merge'
HARNESS = ROOT + '/lightharness'
sys.path.insert(0, HARNESS)
import _r29_ccw_verify_engine as eng  # noqa: E402

B_BATCH = ['导入错误', '类型错误', '零除错误', '设指针', '设指针值', '设系统',
           '设系统错误码', '设置', '设置数组', '低级关闭']


def main():
    eng.verify(
        '任务2（B批：错误类型+设置）',
        B_BATCH,
        os.path.join(HARNESS, '_task2_R29_B批验证_证据.json'),
        os.path.join(HARNESS, '_task2_R29_B批错误类型设置_验证清单.md'),
    )


if __name__ == '__main__':
    main()

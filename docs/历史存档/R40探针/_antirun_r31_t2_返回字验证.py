# -*- coding: utf-8 -*-
"""R31 任务2 反跑脚本：_EMBED 字「返回」逐条隔离验证（三重判据）。"""
import _r31_embed_engine as eng

if __name__ == '__main__':
    eng.verify('返回', '_antirun_r31_t2_返回字验证.json',
               '_task2_R31_EMBED返回字验证.md')

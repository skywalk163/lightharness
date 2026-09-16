# -*- coding: utf-8 -*-
"""R31 任务1 反跑脚本：_EMBED 字「为」逐条隔离验证（三重判据）。"""
import _r31_embed_engine as eng

if __name__ == '__main__':
    eng.verify('为', '_antirun_r31_t1_为字验证.json',
               '_task1_R31_EMBED为字验证.md')

# -*- coding: utf-8 -*-
"""R33 任务4 反跑脚本：_P0A_NEVER_SPLIT "到" 字逐条隔离验证（G1 语料判据）。

注意："到" 同时位于 DUAL（_P0A_HEAD_MERGE_DUAL，8 字之一）。移除 _P0A_NEVER_SPLIT
后 DUAL 仍生效，撤除仅使其额外进入 F/HM，范围形态不受影响。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _r33_lib import g1_for_char

if __name__ == '__main__':
    res = g1_for_char('到', 't4')
    print('任务4 _P0A_NEVER_SPLIT "到" 字 G1: %s' % ('通过' if res['ok'] else '失败'))
    print('  变化文件=%d 新增错误=%d 进入F=%s 进入HM=%s 语料=%d'
          % (len(res['changed']), len(res['new_err']), res['enters_F'],
             res['enters_HM'], res['corpus']))
    if res['changed']:
        for r in res['changed'][:10]:
            print('   ', r)
    json.dump(res, open(os.path.join(os.path.dirname(__file__),
              '_antirun_r33_t4_到字验证.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

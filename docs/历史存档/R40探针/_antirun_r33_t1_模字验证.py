# -*- coding: utf-8 -*-
"""R33 任务1 反跑脚本：_P0A_NEVER_SPLIT "模" 字逐条隔离验证（G1 语料判据）。

以改动前快照 _r33_lexer_head.py 为基线，构建「仅移除 模」的变体 lexer，对全语料
tokenize 比对。变化文件数=0 且新增错误=0 ⇒ G1 通过（可删）。
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from _r33_lib import g1_for_char

if __name__ == '__main__':
    res = g1_for_char('模', 't1')
    print('任务1 _P0A_NEVER_SPLIT "模" 字 G1: %s' % ('通过' if res['ok'] else '失败'))
    print('  变化文件=%d 新增错误=%d 进入F=%s 进入HM=%s 语料=%d'
          % (len(res['changed']), len(res['new_err']), res['enters_F'],
             res['enters_HM'], res['corpus']))
    if res['changed']:
        for r in res['changed'][:10]:
            print('   ', r)
    json.dump(res, open(os.path.join(os.path.dirname(__file__),
              '_antirun_r33_t1_模字验证.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

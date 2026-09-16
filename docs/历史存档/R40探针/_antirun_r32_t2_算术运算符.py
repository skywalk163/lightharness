# -*- coding: utf-8 -*-
"""R32 任务2（P0）：OPERATOR_VERBS 算术运算符10条 反跑脚本。

三重判据逐条验证，输出：
  - _r32_ev_<条目>.json        逐条证据
  - _r32_task_ov_<条目>.md     逐条清单
  - _task2_R32_OPERATOR算术运算符精简.md  合并交付文档

用法：/g/dswork/duan-light-merge/light-merge/.venv/Scripts/python.exe _antirun_r32_t2_算术运算符.py
依赖：_r32_ov_engine.py（同目录）
"""
import _r32_ov_engine as eng

if __name__ == '__main__':
    cache = eng.build_cache()
    for it in eng.ARR:
        eng.verify(it, '_r32_ev_%s.json' % it, '_r32_task_ov_%s.md' % it, cache)
    eng.write_consolidated('算术运算符(任务2)', eng.ARR,
                           '_task2_R32_OPERATOR算术运算符精简.md')

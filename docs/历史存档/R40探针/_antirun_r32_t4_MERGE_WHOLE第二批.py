# -*- coding: utf-8 -*-
"""R32 任务4 反跑脚本：_P0A_MERGE_WHOLE 后 5 条逐条隔离验证（G1）。

条目：外部命令/排序依据/输出块表/返回码/记录类型。
引擎与口径见 _antirun_r32_t34_MERGE_WHOLE逐条验证.py（两任务共用）。
用法：python _antirun_r32_t4_MERGE_WHOLE第二批.py
"""
import runpy
import sys
sys.argv = [__file__, 't4']
runpy.run_path(
    __file__.replace('_antirun_r32_t4_MERGE_WHOLE第二批',
                     '_antirun_r32_t34_MERGE_WHOLE逐条验证'),
    run_name='__main__')

# -*- coding: utf-8 -*-
"""R32 任务3 反跑脚本：_P0A_MERGE_WHOLE 前 5 条逐条隔离验证（G1）。

条目：导出事件表/整理模型消息/退出码/接收参数/非空块。
引擎与口径见 _antirun_r32_t34_MERGE_WHOLE逐条验证.py（两任务共用）。
用法：python _antirun_r32_t3_MERGE_WHOLE第一批.py
"""
import runpy
import sys
sys.argv = [__file__, 't3']
runpy.run_path(__file__.replace('_antirun_r32_t3_MERGE_WHOLE第一批', '_antirun_r32_t34_MERGE_WHOLE逐条验证'), run_name='__main__')

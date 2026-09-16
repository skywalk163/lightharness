# -*- coding: utf-8 -*-
# 任务4 反跑判据验证（_antirun_replay.py）
# 逐项：把实现改错 → 测试必须红（rc != 0）→ 字节级恢复 src → 必须绿（rc == 0）
# A：脚本推导顺序改错（compaction 块先 finish 后 usage）→ 断言红；恢复 → 绿
# B：fromRequest 插值去掉（占位符用模式原文，不取最后匹配）→ 断言红；恢复 → 绿
# C：父子首呼绑定改错（{{session:N}} 一律取最后一个实体会话）→ 断言红；恢复 → 绿
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src', '大模型回放.light')
TEST = 'examples/test_大模型回放.light'

def run_test():
    p = subprocess.run([sys.executable, '运行.py', TEST],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode

def read_src():
    with io.open(SRC, encoding='utf-8-sig', newline='') as f:
        return f.read().replace('\r\n', '\n')

def write_src(text):
    with io.open(SRC, 'w', encoding='utf-8', newline='') as f:
        f.write(text.replace('\n', '\r\n'))

cases = [
    # A：脚本推导顺序改错 —— usage 与 finish 对调
    ('          如果 数据.获取("usage", 空) != 空:\n            列表追加(块, ["type": "usage", "usage": 数据["usage"]])\n          列表追加(块, ["type": "finish", "reason": ["kind": "stop"]])',
     '          列表追加(块, ["type": "finish", "reason": ["kind": "stop"]])\n          如果 数据.获取("usage", 空) != 空:\n            列表追加(块, ["type": "usage", "usage": 数据["usage"]])',
     'A 脚本推导顺序改错（compaction 先 finish 后 usage）'),
    # B：fromRequest 插值去掉 —— 不替换，保留模式原文
    ('    设 结果 为 结果 + 截取(文本, 游标, 开) + 取最后匹配(模式, 语料)',
     '    设 结果 为 结果 + 截取(文本, 游标, 开) + 模式',
     'B fromRequest 插值去掉（占位符不替换）'),
    # C：父子首呼绑定改错 —— 一律取最后一个实体会话
    ('      设 实 为 实体会话表[编号 - 1]',
     '      设 实 为 实体会话表[长度(实体会话表) - 1]',
     'C 父子首呼绑定改错（总是取最后一个会话）'),
]

ok = True
for old, new, desc in cases:
    orig = read_src()
    if old not in orig:
        print('MISS:', desc)
        ok = False
        continue
    write_src(orig.replace(old, new, 1))
    rc_bad = run_test()
    write_src(orig)
    rc_ok = run_test()
    if rc_bad == 0:
        print('反跑不红 FAIL:', desc)
        ok = False
    else:
        print('反跑即红 PASS:', desc, '(rc=%d)' % rc_bad)
    if rc_ok != 0:
        print('恢复不绿 FAIL:', desc, '(rc=%d)' % rc_ok)
        ok = False
    else:
        print('恢复即绿 PASS:', desc)

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)

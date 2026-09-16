# -*- coding: utf-8 -*-
# 任务2 反跑判据验证：把 src 关键逻辑改反 → 必须 rc != 0（红）→ 字节级恢复 → 必须绿。
# 判据 A：turn/start 锚点改成 user/message → test_会话轮次大纲 turn/start 断言红。
# 判据 B：提示预览上限 50 改 99 → test_会话轮次大纲 截断长度断言红。
# 判据 C：中止未分发结果 text 改错 → test_检查点策略 中止结果断言红。
# 字节级备份/恢复 src：以二进制读写，恢复时写回原字节（含 BOM/换行不变）。
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))


def run_test(path):
    env = dict(os.environ)
    env['LIGHT_MERGE'] = r'G:\dswork\duan-light-merge\light-merge'
    p = subprocess.run([sys.executable, '运行.py', path],
                       cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return p.returncode


cases = [
    # (src 文件, 原串, 反串, 目标测试, 说明)
    (os.path.join(ROOT, 'src', '会话轮次大纲.light'),
     '如果 类型 == "turn/start":',
     '如果 类型 == "user/message":  # 反跑：锚点改错 → 红',
     'examples/test_会话轮次大纲.light',
     'turn/start 锚点改成 user/message → turn/start 开新条目断言红'),
    (os.path.join(ROOT, 'src', '会话轮次大纲.light'),
     '段落 提示预览上限 接收:\n  返回 50',
     '段落 提示预览上限 接收:\n  返回 99  # 反跑：预览限长改错 → 红',
     'examples/test_会话轮次大纲.light',
     '提示预览上限 50 改 99 → 截断长度断言红'),
    (os.path.join(ROOT, 'src', '检查点策略.light'),
     '"text": "Error: tool call aborted before dispatch"',
     '"text": "Error: aborted"  # 反跑：中止结果文案改错 → 红',
     'examples/test_检查点策略.light',
     '中止未分发结果 text 改错 → 中止结果断言红'),
]

ok = True
for full, old, new, test_path, desc in cases:
    with io.open(full, 'rb') as f:
        data = f.read()
    old_b = old.encode('utf-8')
    new_b = new.encode('utf-8')
    if old_b not in data:
        print('MISS:', desc)
        ok = False
        continue
    data2 = data.replace(old_b, new_b, 1)
    with io.open(full, 'wb') as f:
        f.write(data2)
    rc = run_test(test_path)
    with io.open(full, 'wb') as f:
        f.write(data)  # 字节级恢复
    rc2 = run_test(test_path)
    if rc == 0:
        print('反跑不红 FAIL:', desc, '(rc=0 应红)')
        ok = False
    else:
        print('反跑即红 PASS:', desc, '(rc=%d)' % rc)
    if rc2 != 0:
        print('恢复未绿 FAIL:', desc, '(rc=%d)' % rc2)
        ok = False
    else:
        print('恢复即绿 PASS:', desc)

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)

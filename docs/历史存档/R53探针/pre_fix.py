# -*- coding: utf-8 -*-
"""把 delivered R52 ssh协议 用例机械还原为「pre-fix 包裹段落」形态：
每个被传引用的校验器生成一个包裹段落，段体内**按名**调用该被导入校验器。

这是 R52 报告 §4.3 描述的 pre-fix 形态（"测试不再定义调用被导入校验器的包裹段落"）。
"""
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')
LH = r'G:\dswork\duan-light-merge\lightharness'

base = open(os.path.join(LH, 'examples', 'test_R52_ssh协议.light'), encoding='utf-8').read()

WRAPPER_TPL = '''段落 抛{名} 接收 值, 期望含, 标签:
  设 捕获名 为 空
  设 捕获消息 为 空
  尝试:
    设 丢弃 为 {名}(值)
    断言相等(假, 真, 标签 + "_应抛未抛")
  捕获 抛了:
    设 错误体 为 抛了.args[0]
    设 捕获名 为 错误体["名"]
    设 捕获消息 为 错误体["消息"]
  断言相等(捕获名, "RemoteOperationError", 标签 + "_名")
  断言真(期望含 在 捕获消息, 标签 + "_消息含:" + 捕获消息)
'''

# 1) 收集所有 校验抛远程(<校验器>, ...) 的校验器名
validators = []
for m in re.finditer(r'校验抛远程\(\s*([^\s,()]+)\s*,', base):
    v = m.group(1)
    if v not in validators:
        validators.append(v)
print('被引用的校验器:', validators)

# 2) 生成包裹段落
wrappers = '\n'.join(WRAPPER_TPL.format(名=v) for v in validators)

# 3) 替换调用点：校验抛远程(v, rest) → 抛v(rest)
new = re.sub(r'校验抛远程\(\s*([^\s,()]+)\s*,', lambda m: f'抛{m.group(1)}(', base)

# 4) 包裹段落 + 去掉参数版 校验抛远程 段落定义
new = re.sub(r'段落 校验抛远程 接收 校验器, 值, 期望含, 标签:\n(?:  .*\n|\n)*?(?=段落 主:)',
             wrappers + '\n', new)

out = os.path.join(LH, 'examples', '_l172pre_ssh协议.light')
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, 'w', encoding='utf-8', newline='\n') as f:
    f.write(new)

d = subprocess.run([PY, os.path.join(HERE, 'dump.py'), out], cwd=LH,
                   capture_output=True, text=True, encoding='utf-8')
for ln in (d.stdout or '').split('\n'):
    s = ln.strip()
    if s.startswith(('entry =', 'arity =', 'module_invokes_entry', '_entry_call',
                     '末尾是否含入口调用块')) or s.startswith('['):
        print('  ' + s)
print(d.stderr[:200])

r = subprocess.run([PY, os.path.join(LH, '运行.py'), out], cwd=LH,
                   capture_output=True, text=True, encoding='utf-8', timeout=300)
print('  rc =', r.returncode)
print('  stdout 行数 =', len([x for x in (r.stdout or '').split('\n') if x.strip()]))
print('  stdout 前3行 =', (r.stdout or '').split('\n')[:3])
print('  stderr 前3行 =', (r.stderr or '').split('\n')[:3])

# -*- coding: utf-8 -*-
# 任务6 反跑判据验证（webhook-github 域）：把判定改反 → 必须 rc != 0（红）→ 恢复 → 绿（逐字节一致）
# A：验证签名 恒定时间比较改短路恒真（签名形同虚设）→ 错误秘密 / 错误签名 断言红；恢复 → 绿
# B：必需头 单值判定 `!= 1` 改 `< 1`（放行多值）→ 同名头双值 400 用例红；恢复 → 绿
# C：是JSON内容类型 参数区含分号分支改真（放行多余参数）→ 多余参数为假 断言红；恢复 → 绿
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src', '网络钩子GitHub.light')
TEST = 'examples/test_网络钩子GitHub.light'

def run_test():
    # 与 运行.py 默认一致；显式带上 LIGHT_MERGE 便于异地环境
    env = dict(os.environ)
    env.setdefault('LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
    p = subprocess.run([sys.executable, '运行.py', TEST],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace', env=env)
    return p.returncode

with io.open(SRC, encoding='utf-8-sig', newline='') as f:
    orig = f.read().replace('\r\n', '\n')

def write_src(text):
    with io.open(SRC, 'w', encoding='utf-8', newline='') as f:
        f.write(text.replace('\n', '\r\n'))

cases = [
    # A: 恒定时间比较改短路恒真 → 验证签名 恒通过，错误密码/错误签名用例红
    (' 设 结果 为 恒定时间相等(期望, 十六进制)',
     ' 设 结果 为 真',
     'A 签名恒定时间比较改短路恒真'),
    # B: 单值判定改放行多值 → 同名头双值未抛，必抛 400 用例红
    ('如果 (列表长度(值表) != 1):',
     '如果 (列表长度(值表) < 1):',
     'B 必需头单值判定改允许多值'),
    # C: 参数区含分号分支改真 → 多余参数被放行，应为假用例红
    ('''  如果 (字符串包含(参数, ";")):
    返回 假''',
     '''  如果 (字符串包含(参数, ";")):
    返回 真''',
     'C 内容类型多余参数放行改反'),
]

ok = True
for old, new, desc in cases:
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

# 逐字节一致：写回内容必须与原始备份完全一致
with io.open(SRC, encoding='utf-8-sig', newline='') as f:
    final = f.read().replace('\r\n', '\n')
if final == orig:
    print('逐字节还原 PASS: 文件与备份一致')
else:
    print('逐字节还原 FAIL: 文件与备份存在差异')
    ok = False

print('ALL OK' if ok else 'HAS FAIL')
sys.exit(0 if ok else 1)
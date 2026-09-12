# -*- coding: utf-8 -*-
# 反跑判据验证（拷贝原语 L-082 / L-083）
# 思路：把 lightharness 自包含 stdlib 里的 副本/浅拷贝/深拷贝/冻结 四个一等原语
#       重命名（使其脱靶 → _light_builtin.副本 等 AttributeError），
#       依赖它们的测试应当转红；恢复后应当转绿。
# 在内存中备份原文件，跑完立即还原，绝不残留。
import io, os, sys, subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
BUILTINS = os.path.join(ROOT, 'stdlib', 'builtins.py')

# 依赖这四个原语的验收测试：L-082 会话格式快照、L-083 消息构造脱钩 + 新回归测试
TESTS = [
    'examples/test_修复_拷贝.light',         # L-082+083 综合：副本/浅拷贝/深拷贝/冻结
    'examples/test_修复_会话.light',         # 验收#5：事件带来源 经 副本 快照
    'examples/test_行为对照_会话持久化.light',  # 验收#5：事件带来源 经 副本 快照
    'examples/test_消息.light',              # 验收#4：消息构造 深拷贝 脱钩
]

# (原 def 行, 反跑 def 行)
PATCHES = [
    ('def 副本(原):',     'def _removed_副本(原):'),
    ('def 浅拷贝(原):',   'def _removed_浅拷贝(原):'),
    ('def 深拷贝(原):',   'def _removed_深拷贝(原):'),
    ('def 冻结(原):',     'def _removed_冻结(原):'),
]


def run_test(path):
    env = dict(os.environ)
    env['LIGHT_MERGE'] = r'G:\dswork\duan-light-merge\light-merge'
    p = subprocess.run([sys.executable, '运行.py', path],
                       cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.returncode


def read_text(p):
    with io.open(p, encoding='utf-8-sig', newline='') as f:
        return f.read()


def write_text(p, s):
    with io.open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def apply_patch(src):
    for old, new in PATCHES:
        if old not in src:
            return None, old
        src = src.replace(old, new, 1)
    return src, None


def main():
    original = read_text(BUILTINS)

    # ---- 反跑：移除原语 → 期望全红 ----
    patched, miss = apply_patch(original)
    if patched is None:
        print('MISS 未找到原定义行:', miss)
        return 1
    write_text(BUILTINS, patched)

    ok = True
    print('=== 反跑（原语移除，期望 rc!=0 即红）===')
    for t in TESTS:
        rc = run_test(t)
        if rc == 0:
            print('  反跑不红 FAIL:', t, '(rc=0 应红)')
            ok = False
        else:
            print('  反跑即红 PASS:', t, '(rc=%d)' % rc)

    # ---- 还原：恢复原语 → 期望全绿 ----
    write_text(BUILTINS, original)  # 必须还原后再跑
    print('=== 还原（原语恢复，期望 rc=0 即绿）===')
    for t in TESTS:
        rc = run_test(t)
        if rc != 0:
            print('  还原仍红 FAIL:', t, '(rc=%d 应绿)' % rc)
            ok = False
        else:
            print('  还原即绿 PASS:', t, '(rc=0)')

    # 二次确认：文件已完全还原
    if read_text(BUILTINS) != original:
        print('致命：builtins.py 未完全还原！')
        ok = False

    print('ALL OK' if ok else 'HAS FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

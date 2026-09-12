# -*- coding: utf-8 -*-
"""第11轮任务3 反跑判据：util 8 包复刻。
对 src 下三个文件做字节级备份 → 变异 → 跑 examples/test_工具_小工具.light → 断言红；
恢复字节 → 再跑 → 断言绿。三项：
  A 双端队列弹出顺序改错（队尾写入覆盖队首）
  B 深相等改浅比较（容器只比长度/键，不再递归比较值）
  C 工作区路径 UNC 判定改错（丢掉 \\server 前缀识别）
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src')
TEST = os.path.join(ROOT, 'examples', 'test_工具_小工具.light')
RUNNER = os.path.join(ROOT, '运行.py')

LIGHT_MERGE = r'G:\dswork\duan-light-merge\light-merge'


def run_test():
    env = dict(os.environ)
    env['LIGHT_MERGE'] = LIGHT_MERGE
    p = subprocess.run(
        [sys.executable, RUNNER, TEST],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        cwd=ROOT, env=env, timeout=300,
    )
    return p.returncode, ((p.stdout or '') + (p.stderr or ''))


# (用例名, src文件名, [(旧子串, 新子串), ...])
CASES = [
    (
        'A-双端队列弹出顺序',
        '双端队列.light',
        [(
            '    设 尾 为 (己.头 + 己.计数) % 长(己.缓冲)',
            '    设 尾 为 己.头',
        )],
    ),
    (
        'B-深相等改浅比较',
        '值工具.light',
        [
            ('      如果 深相等JSON(甲[i], 乙[i]) == 假:', '      如果 假:'),
            ('      如果 深相等JSON(甲[键], 乙[键]) == 假:', '      如果 假:'),
        ],
    ),
    (
        'C-工作区路径UNC判定',
        '工作区路径.light',
        [('  如果 值.开头("\\\\\\\\"):', '  如果 假:')],
    ),
]


def main():
    failures = []
    for name, fname, pairs in CASES:
        path = os.path.join(SRC, fname)
        with open(path, 'rb') as f:
            backup = f.read()
        try:
            text = backup.decode('utf-8')
            for old, new in pairs:
                cnt = text.count(old)
                if cnt != 1:
                    failures.append(f'{name}: 旧子串出现 {cnt} 次（期望 1），未变异')
                    break
                text = text.replace(old, new)
            else:
                with open(path, 'wb') as f:
                    f.write(text.encode('utf-8'))
                rc_red, out_red = run_test()
                if rc_red == 0:
                    failures.append(f'{name}: 变异后仍绿（rc=0），判据未咬住\n{out_red[-400:]}')
                else:
                    print(f'[红] {name}: 变异后 rc={rc_red}（符合预期）')
            # 恢复
            with open(path, 'wb') as f:
                f.write(backup)
            rc_green, out_green = run_test()
            if rc_green != 0:
                failures.append(f'{name}: 恢复后仍红 rc={rc_green}\n{out_green[-400:]}')
            else:
                print(f'[绿] {name}: 恢复后 rc=0（恢复成功）')
        finally:
            # 兜底：确保恢复
            with open(path, 'wb') as f:
                f.write(backup)

    print('=' * 50)
    if failures:
        print('反跑失败：')
        for fl in failures:
            print(' -', fl)
        sys.exit(1)
    print('全部 3 项反跑判据通过（变异红 → 恢复绿）')


if __name__ == '__main__':
    main()

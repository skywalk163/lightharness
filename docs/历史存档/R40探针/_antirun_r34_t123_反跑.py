# _antirun_r34_t123_反跑.py —— 第34轮 任务1-3 反跑判据
#
# 判据：
#   A) 值反：把一条 `断言相等(实际, 期望, 标签)` 的期望值改反 → 用例必须 rc=1（红）
#   B) 抛反：把「应抛」用例改成不抛 → 用例必须 rc=1（报 应抛错未抛）
#   C) 还原：改回后必须 rc=0（绿）
#
# 纪律：变异只写在仓库根目录临时文件 `_red_tmp.light`（不放 examples/，
#       否则会被 test_回归.py glob 收进去）；跑完即删。
#       反跑与测试串行，不并发。

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = os.path.join(ROOT, '..', 'light-merge', '.venv', 'Scripts', 'python.exe')
TMP = os.path.join(ROOT, '_red_tmp.light')

CASES = [
    # (任务, 源测试文件, 变异名, 原串, 新串, 判据类型)
    ('任务1', 'examples/test_代理循环.light', '值反-终态无后继',
     '断言相等(长(循轮次后继(轮次完成)), 0, "completed 无后继")',
     '断言相等(长(循轮次后继(轮次完成)), 1, "completed 无后继")', 'A'),
    ('任务1', 'examples/test_代理循环.light', '抛反-未知步骤类型放行',
     '    建步骤(0, "未知类型")',
     '    建步骤(0, "llm")', 'B'),
    ('任务2', 'examples/test_工具执行.light', '值反-可见性矩阵',
     '断言相等(长(具可见级别(级公开)), 3, "public 对三级可见")',
     '断言相等(长(具可见级别(级公开)), 2, "public 对三级可见")', 'A'),
    ('任务2', 'examples/test_工具执行.light', '抛反-工具重名放行',
     '    具注册工具(注册, "读文件", 级公开, 回显处理)',
     '    具注册工具(注册, "读文件2", 级公开, 回显处理)', 'B'),
    ('任务3', 'examples/test_子代理深化.light', '值反-目录路径',
     '断言相等(目录路径(甲丙), "根/甲/丙", "丙路径（层级拼接）")',
     '断言相等(目录路径(甲丙), "根/丙", "丙路径（层级拼接）")', 'A'),
    ('任务3', 'examples/test_子代理深化.light', '抛反-深度超限放行',
     '    派生子代(三层, "四层", 3)',
     '    派生子代(三层, "四层", 9)', 'B'),
]


def run(path, is_tmp):
    target = '_red_tmp.light' if is_tmp else path
    p = subprocess.run([PY, '运行.py', target], cwd=ROOT,
                       capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def main():
    fail = 0
    for task, src, name, old, new, kind in CASES:
        full = os.path.join(ROOT, src)
        with open(full, encoding='utf-8') as f:
            text = f.read()
        if old not in text:
            print('[%s] %s 跳过：锚点未命中' % (task, name))
            fail += 1
            continue
        with open(TMP, 'w', encoding='utf-8') as f:
            f.write(text.replace(old, new, 1))
        rc, out = run(TMP, True)
        ok = (rc != 0)
        print('[%s] %s（判据%s）：变异后 rc=%s → %s'
              % (task, name, kind, rc, '红 OK' if ok else '仍绿 FAIL'))
        if kind == 'B' and ok and '应抛错未抛' not in out:
            print('      ⚠ 红了但不是「应抛错未抛」，实际输出首行：%s'
                  % (out.strip().splitlines()[0] if out.strip() else '(空)'))
        if not ok:
            fail += 1
    if os.path.exists(TMP):
        os.remove(TMP)

    # 还原后复跑：三个用例必须全绿
    print('=== 还原态复跑（必须全绿）===')
    for task, src, name, old, new, kind in CASES:
        pass
    for src in ['examples/test_代理循环.light',
                'examples/test_工具执行.light',
                'examples/test_子代理深化.light']:
        rc, out = run(src, False)
        print('%s rc=%s %s' % (src, rc, 'GREEN OK' if rc == 0 else 'RED FAIL'))
        if rc != 0:
            fail += 1
            print(out[-800:])

    print('=== 结论：%s ===' % ('ALL OK' if fail == 0 else 'FAIL(%d)' % fail))
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())

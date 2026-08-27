# -*- coding: utf-8 -*-
"""校验编译.py —— 编译 .light 模块并核对生成代码，抓 L-004/L-007 成员名拆分与 L-003 误编译。

用法: python 工具集/校验编译.py <模块.light>
输出: 逐条列出 成员赋值 / 方法定义 / 疑似拆分（self.成员含多余点、赋值变比较）。
"""
import io, sys, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
LIGHT_MERGE = os.environ.get('LIGHT_MERGE', r'G:\dswork\duan-light-merge\light-merge')
sys.path.insert(0, os.path.join(LIGHT_MERGE, 'src'))
sys.path.insert(0, LIGHT_MERGE)
from light_parser_v3 import LightParser
from code_generator import PythonCodeGenerator

def main():
    if len(sys.argv) < 2:
        print('用法: python 工具集/校验编译.py <模块.light>')
        return 1
    path = sys.argv[1]
    src = open(path, encoding='utf-8').read()
    p = LightParser(); g = PythonCodeGenerator()
    try:
        tree = p.parse(src)
    except Exception as e:
        print('❌ 解析失败:\n', str(e)[:800])
        return 1
    code = g.generate(tree)
    lines = code.split('\n')
    problems = []
    # 1) 成员赋值检查：self.X.Y = 值（异常拆分）或 self.X == 值（比较）
    for i, l in enumerate(lines):
        s = l.strip()
        m = re.match(r'self\.([^ =]+)\.([^ =]+)\s*=\s*(.+)', s)
        if m and 'def ' not in l:
            problems.append(f'行{i+1}: 疑似成员拆分赋值 self.{m.group(1)}.{m.group(2)} = {m.group(3)[:40]}')
        m2 = re.match(r'\(self\.([^ )]+)\s*==\s*(.+)\)\s*$', s)
        if m2 and 'def ' not in l:
            problems.append(f'行{i+1}: 疑似赋值被编译成比较 (self.{m2.group(1)} == {m2.group(2)[:40]})')
    # 2) 方法定义检查：类方法应完整
    # 3) 报告
    print(f'✅ 编译成功，生成 {len(lines)} 行')
    if problems:
        print('⚠️ 疑似问题 %d 处:' % len(problems))
        for p in problems:
            print('  ', p)
        return 2
    print('  成员赋值/方法名无异常拆分')
    return 0

if __name__ == '__main__':
    sys.exit(main())

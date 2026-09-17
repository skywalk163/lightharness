# -*- coding: utf-8 -*-
"""L-172 复现矩阵探针：自动生成多个 .light 变体并逐个运行，打印 stdout/rc。"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)  # light-merge
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')

# 本地被测模块（模拟 src/ssh协议.light 的角色）
MOD = '''
段落 校验正数 接收 值:
  如果 值 < 0: 抛出 "非正数"
  返回 值
'''

CASES = {}

CASES['a_辅助无参直接按名调导入'] = '''
从 JSON 导入 解析JSON
段落 辅助:
  设 结果 为 解析JSON("{\\"a\\": 1}")
  打印(结果["a"])
段落 主:
  辅助()
  打印("主内容")
'''

CASES['b_辅助有参_尝试块内按名调导入'] = '''
从 JSON 导入 解析JSON
段落 断言相等 接收 实际, 期望, 标签:
  如果 实际 != 期望: 抛出 "反跑失败[" + 标签 + "]"
段落 废弃 接收 值:
  返回 值
段落 辅助 接收 值, 标签:
  设 捕获 为 空
  尝试:
    设 丢弃 为 解析JSON(值)
    断言相等(假, 真, 标签)
  捕获 抛了:
    设 捕获 为 "caught"
  断言相等(捕获, "caught", 标签)
段落 主:
  辅助("{bad", "t1")
  打印("主内容")
'''

CASES['c_辅助调本地_本地调导入'] = '''
从 JSON 导入 解析JSON
段落 内层 接收 值:
  返回 解析JSON(值)
段落 辅助 接收 值:
  打印(内层(值)["a"])
段落 主:
  辅助("{\\"a\\": 7}")
  打印("主内容")
'''

CASES['d_导入本地模块_辅助按名调'] = '''
从 _l172mod 导入 校验正数
段落 辅助 接收 值:
  打印(校验正数(值))
段落 主:
  辅助(3)
  打印("主内容")
'''

CASES['e_辅助在前_导入在后'] = '''
段落 辅助 接收 值:
  打印(校验正数(值))
从 _l172mod 导入 校验正数
段落 主:
  辅助(3)
  打印("主内容")
'''

CASES['f_两个辅助段落都按名调导入'] = '''
从 JSON 导入 解析JSON, 序列化JSON
段落 辅助甲 接收 值:
  打印(序列化JSON(值))
段落 辅助乙 接收 值:
  打印(解析JSON(值))
段落 主:
  辅助甲({"a": 1})
  辅助乙("{\\"b\\": 2}")
  打印("主内容")
'''

CASES['g_辅助体返回导入函数结果并被主使用'] = '''
从 JSON 导入 序列化JSON
段落 辅助 接收 值:
  返回 序列化JSON(值)
段落 主:
  设 文本 为 辅助({"a": 1})
  打印(文本)
  打印("主内容")
'''


def main():
    with open(os.path.join(HERE, '_l172mod.light'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(MOD)
    results = {}
    for name, src in CASES.items():
        p = os.path.join(HERE, name + '.light')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(src.lstrip('\n'))
        r = subprocess.run([PY, '-m', 'cli.light', 'run', p],
                           cwd=LM, capture_output=True, text=True, encoding='utf-8', timeout=120)
        results[name] = (r.returncode, (r.stdout or '')[:400], (r.stderr or '')[:400])
    for name, (rc, out, err) in results.items():
        print('=' * 70)
        print(f'### {name}   rc={rc}')
        print('--- stdout ---')
        print(out.rstrip())
        if err.strip():
            print('--- stderr ---')
            print(err.rstrip())


if __name__ == '__main__':
    main()

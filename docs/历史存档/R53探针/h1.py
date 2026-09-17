# -*- coding: utf-8 -*-
"""按 R52 报告还原「pre-fix 包裹段落」形态：每个校验器一个包裹段落，体内容按名调用被导入校验器。"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')

MOD = '''段落 校验正数 接收 值:
  如果 值 < 0: 抛出 "expected positive"
  返回 值

段落 校验文本 接收 值:
  如果 是字符串(值) == 假: 抛出 "expected string"
  返回 值
'''

CASE = '''从 _l172mod2 导入 校验正数, 校验文本

段落 断言相等 接收 实际, 期望, 标签:
  如果 实际 != 期望: 抛出 "反跑判据失败[" + 标签 + "]：实际=" + 文本(实际)

段落 断言真 接收 条件, 标签:
  如果 条件 == 假: 抛出 "反跑判据失败[" + 标签 + "]：条件为假"

段落 校验抛正数 接收 值, 期望含, 标签:
  设 捕获消息 为 空
  尝试:
    设 丢弃 为 校验正数(值)
    断言相等(假, 真, 标签 + "_应抛未抛")
  捕获 抛了:
    设 捕获消息 为 抛了.args[0]
  断言真(期望含 在 捕获消息, 标签 + "_消息含")

段落 校验抛文本 接收 值, 期望含, 标签:
  设 捕获消息 为 空
  尝试:
    设 丢弃 为 校验文本(值)
    断言相等(假, 真, 标签 + "_应抛未抛")
  捕获 抛了:
    设 捕获消息 为 抛了.args[0]
  断言真(期望含 在 捕获消息, 标签 + "_消息含")

段落 主:
  断言相等(校验正数(3), 3, "1a_合法")
  校验抛正数(-1, "expected positive", "1b_负")
  校验抛文本(5, "expected string", "1c_非串")
  打印("MAIN-OK")
'''


def main():
    with open(os.path.join(HERE, '_l172mod2.light'), 'w', encoding='utf-8', newline='\n') as f:
        f.write(MOD)
    p = os.path.join(HERE, 'h1_包裹段落形态.light')
    with open(p, 'w', encoding='utf-8', newline='\n') as f:
        f.write(CASE)
    d = subprocess.run([PY, os.path.join(HERE, 'dump.py'), p], cwd=LM,
                       capture_output=True, text=True, encoding='utf-8')
    print(d.stdout)
    r = subprocess.run([PY, '-m', 'cli.light', 'run', p], cwd=LM,
                       capture_output=True, text=True, encoding='utf-8', timeout=120)
    print('rc =', r.returncode)
    print('stdout:', repr(r.stdout))
    print('stderr:', repr(r.stderr[:300]))


if __name__ == '__main__':
    main()

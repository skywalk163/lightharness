# -*- coding: utf-8 -*-
"""终极复现尝试：lightharness 布局（examples 主文件 + src/ 真模块 + 钩子导入），
主文件内定义「按名调用被导入校验器的包裹段落」，主() 依赖自动入口。"""
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
LM = os.path.dirname(HERE)
PY = os.path.join(LM, '.venv', 'Scripts', 'python.exe')
LH = r'G:\dswork\duan-light-merge\lightharness'
EX = os.path.join(LH, 'examples')

WRAPPER = '''段落 抛路径 接收 值, 期望含, 标签:
  设 捕获消息 为 空
  尝试:
    设 丢弃 为 校验远程路径(值)
    断言相等(假, 真, 标签 + "_应抛未抛")
  捕获 抛了:
    设 捕获消息 为 抛了.args[0]
  断言真(期望含 在 捕获消息, 标签 + "_消息含")
'''

MAIN_TPL = '''从 ssh协议 导入 校验远程路径, 校验进程标识

段落 断言相等 接收 实际, 期望, 标签:
  如果 实际 != 期望: 抛出 "反跑判据失败[" + 标签 + "]"

段落 断言真 接收 条件, 标签:
  如果 条件 == 假: 抛出 "反跑判据失败[" + 标签 + "]"

{WRAPPER}
段落 主:
  断言相等(校验远程路径("/a/b"), "/a/b", "1a_合法")
  抛路径("", "expected an absolute POSIX path", "1b_空")
  打印("MAIN-OK")
{TAIL}
'''

CASES = {
    'w1_自动入口': MAIN_TPL.format(WRAPPER=WRAPPER, TAIL=''),
    'w2_显式主': MAIN_TPL.format(WRAPPER=WRAPPER, TAIL='\n主()\n'),
    'w3_包裹在导入前': ('段落 断言相等 接收 实际, 期望, 标签:\n'
                    '  如果 实际 != 期望: 抛出 "反跑判据失败[" + 标签 + "]"\n\n'
                    '段落 断言真 接收 条件, 标签:\n'
                    '  如果 条件 == 假: 抛出 "反跑判据失败[" + 标签 + "]"\n\n'
                    + WRAPPER + '\n从 ssh协议 导入 校验远程路径\n\n段落 主:\n'
                    '  抛路径("", "expected an absolute POSIX path", "1b_空")\n'
                    '  打印("MAIN-OK")\n'),
}


def main():
    for name, text in CASES.items():
        p = os.path.join(EX, '_l172w.light')
        with open(p, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        d = subprocess.run([PY, os.path.join(HERE, 'dump.py'), p], cwd=LH,
                           capture_output=True, text=True, encoding='utf-8')
        info = []
        for ln in (d.stdout or '').split('\n'):
            s = ln.strip()
            if s.startswith(('entry =', 'arity =', 'module_invokes_entry', '末尾是否含入口调用块')):
                info.append(s)
        r = subprocess.run([PY, os.path.join(LH, '运行.py'), p], cwd=LH,
                           capture_output=True, text=True, encoding='utf-8', timeout=300)
        out = [x for x in (r.stdout or '').split('\n') if x.strip()]
        print(f'{name:14s} rc={r.returncode} MAIN-OK={"MAIN-OK" in (r.stdout or "")} '
              f'输出={out[:2]}')
        print('     ', ' | '.join(info))
        if r.stderr.strip():
            print('      err:', r.stderr.strip().split('\n')[0][:140])


if __name__ == '__main__':
    main()

# -*- coding: utf-8 -*-
"""R57 任务1b：code_generator.py 类定义基类补异常名映射（错误→Exception）。
精确字符串替换，保持原文件编码/行尾。"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\src\code_generator.py')
raw = p.read_bytes()
text = raw.decode('utf-8')
was_crlf = '\r\n' in text
text_n = text.replace('\r\n', '\n')  # 归一化做替换

old = (
    "            bases = ', '.join(b if b.startswith('Generic[') else self._sanitize_name(b)\n"
    "                              for b in all_bases)"
)
new = (
    "            # R57 任务1b：类继承基类名走 _resolve_exception_type，把光明异常名\n"
    "            # （如 错误→Exception）映射成 Python 异常。此前只 _sanitize_name，\n"
    "            # `类 X 继承 错误:` 编译成 `class X(错误):`，纯光明 stdlib 经\n"
    "            # _light_import_hook 编译加载时运行期 NameError（phase9 16 条）。\n"
    "            bases = ', '.join(\n"
    "                b if b.startswith('Generic[')\n"
    "                else self._resolve_exception_type(self._sanitize_name(b))\n"
    "                for b in all_bases)"
)

if old not in text_n:
    print('[失败] 未找到目标片段')
    raise SystemExit(1)
if text_n.count(old) != 1:
    print('[失败] 目标片段出现 %d 次，非唯一' % text_n.count(old))
    raise SystemExit(1)

text_n = text_n.replace(old, new)
if was_crlf:
    text_n = text_n.replace('\n', '\r\n')
p.write_bytes(text_n.encode('utf-8'))
print('[成功] 已替换（原文件 CRLF=%s）。' % was_crlf)
for line in new.split('\n')[:6]:
    print('   ', line)

# -*- coding: utf-8 -*-
from pathlib import Path
p = Path(r'G:\dswork\duan-light-merge\light-merge\src\code_generator.py')
raw = p.read_bytes()
text = raw.decode('utf-8')
text_n = text.replace('\r\n', '\n')
lines = text_n.split('\n')
for i in range(2668, 2675):
    print(i + 1, repr(lines[i]))
print('CRLF:', '\r\n' in text)

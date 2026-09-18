# -*- coding: utf-8 -*-
"""R59 task3: relabel non-compilable illustrative fences light/光明 -> text."""
import io

EDITS = [
    ('docs/L1_白话体语法规范_v4.0.md', 207),
    ('docs/L1_白话体语法规范_v4.0.md', 229),
    ('docs/L1_白话体语法规范_v4.0.md', 321),
    ('docs/L1_白话体语法规范_v4.0.md', 523),
    ('docs/llvm_backend_design.md', 321),
    ('docs/api/stdlib.md', 32),
    ('docs/tutorials/进阶教程.md', 193),
]

for path, lineno in EDITS:
    with io.open(path, encoding='utf-8', newline='') as f:
        text = f.read()
    # split preserving line terminators
    lines = text.splitlines(keepends=True)
    cur = lines[lineno - 1].rstrip('\r\n')
    stripped = cur.strip()
    assert stripped in ('```light', '```光明'), f'{path}:{lineno} unexpected fence: {cur!r}'
    indent = cur[:len(cur) - len(cur.lstrip())]
    # preserve original terminator
    nl = lines[lineno - 1][len(cur):]
    lines[lineno - 1] = indent + '```text' + nl
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(lines)
    print(f'{path}:{lineno}  {stripped} -> ```text')
print('done')

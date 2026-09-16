# -*- coding: utf-8 -*-
"""R29 任务1+2：将验证通过的 14 条 CCW 从 lexer.py 删除（原子写 + 多重护栏）。

护栏：
  - 导入当前 lexer，断言 CCW 当前集合 == 预期 24 条（DELETABLE ∪ KEPT）；
    若其他 agent 已改动 CCW 导致不符，立即中止（不写）。
  - 逐条字符串删除 frozenset 内条目行（4 空格缩进锚定），避免误删相近条目。
  - 写临时文件 → py_compile 校验 → 正则复核条目集合 == KEPT(10) → os.replace 原子落盘。
不碰其他批条目、不改注释历史块。
"""
import os
import re
import sys
import py_compile

ROOT = r'G:/dswork/duan-light-merge'
LP = ROOT + r'/light-merge/src/lexer.py'
sys.path.insert(0, ROOT + r'/light-merge/src')
import lexer  # noqa: E402

DELETABLE = {'异步写入文件', '异步睡眠', '异步读取文件', '异步追加文件', '并发等待',
             '导入错误', '类型错误', '设指针', '设指针值', '设系统',
             '设系统错误码', '设置', '设置数组', '低级关闭'}
KEPT = {'位与', '位异或', '位或', '位非', '零除错误',
        '应当', '测试_生成问候语', '记录类型', '幂次', '除非'}

cur = set(lexer.COMMON_COMPOUND_WORDS)
assert cur == (DELETABLE | KEPT), (
    'CCW 现状与预期不符，疑似其他 agent 已改动：缺=%s 多=%s'
    % (sorted(KEPT - cur), sorted(cur - KEPT)))

text = open(LP, encoding='utf-8').read()
new = text
for e in DELETABLE:
    pat = re.compile(r"^    '%s',[^\n]*\n" % re.escape(e), re.M)
    assert pat.search(new), '未找到条目行: ' + e
    new = pat.sub('', new, count=1)

note = (
    "    # 【R29 任务1 精简】A批 删除 5 条（异步写入文件/异步睡眠/异步读取文件/\n"
    "    #   异步追加文件/并发等待）：三重判据全通过（证据 _task1_R29_A批验证_证据.json），原标注作废。\n"
    "    # 【R29 任务2 精简】B批 删除 9 条（导入错误/类型错误/设指针/设指针值/设系统/\n"
    "    #   设系统错误码/设置/设置数组/低级关闭）：三重判据全通过\n"
    "    #   （证据 _task2_R29_B批验证_证据.json），原标注作废。\n"
)
anchor = "    # ===== 保留 A：真护栏"
assert anchor in new, '未找到 保留A 锚点'
new = new.replace(anchor, note + anchor, 1)

# 原子写 + 校验
tmp = LP + '.tmp'
open(tmp, 'w', encoding='utf-8').write(new)
py_compile.compile(tmp, doraise=True)
m = re.search(r"COMMON_COMPOUND_WORDS = frozenset\(\{(.*?)\}\)\n", new, re.S)
entries = set(re.findall(r"'([^']*)'", m.group(1)))
assert entries == KEPT, '写回后条目集合不符: 实=%s 期=%s' % (sorted(entries), sorted(KEPT))
assert len(entries) == 10
os.replace(tmp, LP)
print('OK: CCW %d -> %d，删除 %d 条（任务1 A批 5 + 任务2 B批 9）'
      % (len(cur), len(entries), len(DELETABLE)))
print('保留 10 条: %s' % '、'.join(sorted(KEPT)))

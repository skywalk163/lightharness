# -*- coding: utf-8 -*-
"""R74 路5-A：对标清单.json 数据卫生（主 agent 亲自执行，因子 agent 配额 429 耗尽）。

两件事：
1) 3 条「空条目」实为字段命名不一致（用 `id` 而非 `编号`），内容有价值（R59/R60/R61 轮次交付记录）
   → 不删除，补 `编号` 字段（保留 `id` 兼容），消除脚本 KeyError。
2) #197 状态「进行中」复核：L-174 已修有实据，剩余阻塞是 0.82 全量确认（当前 SSH 不可达）
   → 保持「进行中」不谎报完成，备注追加 R74 复核记录。

写回铁律：ensure_ascii=False + indent=2 + CRLF + 无尾换行 + 改前改后各一次无损往返自证。
"""
import json

P = r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json'


def canon(d):
    return json.dumps(d, ensure_ascii=False, indent=2).encode('utf-8').replace(b'\n', b'\r\n')


raw = open(P, 'rb').read()
d = json.loads(raw.decode('utf-8'))

# ---- 改前自证 ----
print('[改前自证] 规范序列化 == 原文件:', canon(d) == raw)
assert canon(d) == raw, '改前自证失败，序列化参数不对，禁止写入'

items = d['条目']
print('条目数:', len(items))

# ---- 1) 补编号 ----
fixed = []
for idx, it in enumerate(items):
    if not str(it.get('编号', '')).strip():
        sid = str(it.get('id', '')).strip()
        if sid:
            num = int(sid.lstrip('#'))
            it['编号'] = num
            fixed.append((idx, sid, str(it.get('轮次', '')), str(it.get('标题', ''))[:40]))
print('\n补编号条目 %d 条：' % len(fixed))
for idx, sid, rnd, title in fixed:
    print('  索引%d  id=%s  轮次=%s  %s' % (idx, sid, rnd, title))

# ---- 2) #197 复核 ----
note = ('\n【R74 路M 复核（2026-09-20）】本条「进行中」复核结论：'
        'L-174（无空格赋值尾「为」丢失）**已修**且备注内有实据（examples/modules/main.light 实跑 rc=1→打印5、'
        '16 条词法红全部转绿、互举反跑 677 零新增、全语料 38084 文件仅 1 处变化且为改善）。'
        '剩余阻塞项 = 标题所述「3 新增红已定向修复待下轮全量确认」需 0.82 全量门确认；'
        'R74 本轮 0.82 门禁机（192.168.0.82）SSH 公钥未授权不可达，全量门未能补跑，'
        '**故本条状态维持「进行中」，不谎报完成**。待 SSH 就位后跑全量门确认 3 条红已消化即可转已完成。')
hit = 0
for it in items:
    if str(it.get('编号')) == '197':
        it['备注'] = it.get('备注', '') + note
        hit += 1
print('\n#197 备注追加:', hit == 1)

# ---- 写回 ----
out = canon(d)
open(P, 'wb').write(out)

# ---- 改后自证 ----
raw2 = open(P, 'rb').read()
d2 = json.loads(raw2.decode('utf-8'))
print('\n[改后自证] 规范序列化 == 新文件:', canon(d2) == raw2)
print('[回读] 条目数:', len(d2['条目']))
print('[回读] 缺编号条目数:', sum(1 for x in d2['条目'] if not str(x.get('编号', '')).strip()))
print('[回读] 尾换行:', raw2.endswith(b'\n'), '(应为 False)')
print('[回读] CRLF:', b'\r\n' in raw2)
print('\n=== 结论 ===')
print('PASS' if canon(d2) == raw2 and not raw2.endswith(b'\n') else 'FAIL')

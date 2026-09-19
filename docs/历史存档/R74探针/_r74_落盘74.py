# -*- coding: utf-8 -*-
"""R74 路M：把路5B 的 #74 更新落盘对标清单.json。

写回铁律：ensure_ascii=False + indent=2 + CRLF + 无尾换行 + 改前改后各一次无损往返自证。
"""
import json

P = r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json'


def canon(d):
    return json.dumps(d, ensure_ascii=False, indent=2).encode('utf-8').replace(b'\n', b'\r\n')


raw = open(P, 'rb').read()
d = json.loads(raw.decode('utf-8'))

print('[改前自证] 规范序列化 == 原文件:', canon(d) == raw)
assert canon(d) == raw, '改前自证失败，禁止写入'

NEW_STATE = 'done(纯逻辑层+一等异步等价实现)'
APPEND = ('；R74路5B：缺口四项（pending 请求表 / 取消信号 / flush / 流挂接）已用光明现有一等 async/await（R70-B）'
          '与 src/中止.light 的中止令牌在纯逻辑层等价实现，不再挂「依赖 node:stream 宿主包」标签——'
          'pending 表按 id 挂号 asyncio.Future 并撮合（并发乱序不串味）、取消信号经 首个完成 竞速清理 pending 并抛明确取消异常、'
          'flush 强制落已挂接可读写字节流、流挂接经 内存字节流 使传输层脱离「只吃/吐字符串」')
NEW_EVIDENCE = [
    'examples/test_R74_路5_JSONRPC深化.light',
    'src/JSONRPC传输.light',
    '_task5B_R74_JSONRPC.md',
]

hit = 0
for it in d['条目']:
    if str(it.get('编号')) == '74':
        old = it.get('状态', '')
        it['状态'] = NEW_STATE + APPEND
        ev = it.setdefault('证据', [])
        for e in NEW_EVIDENCE:
            if e not in ev:
                ev.append(e)
        hit += 1
        print('旧状态前 80 字:', old[:80])
        print('新证据数:', len(ev))

print('#74 命中:', hit == 1)
assert hit == 1

out = canon(d)
open(P, 'wb').write(out)

raw2 = open(P, 'rb').read()
d2 = json.loads(raw2.decode('utf-8'))
print()
print('[改后自证] 规范序列化 == 新文件:', canon(d2) == raw2)
print('[回读] 条目数:', len(d2['条目']))
print('[回读] 尾换行:', raw2.endswith(b'\n'), '(应 False)')
print('[回读] CRLF:', b'\r\n' in raw2)
print('[回读] #74 状态前 60 字:', [x['状态'][:60] for x in d2['条目'] if str(x.get('编号')) == '74'])
print()
print('=== 结论 ===')
print('PASS' if canon(d2) == raw2 and not raw2.endswith(b'\n') else 'FAIL')

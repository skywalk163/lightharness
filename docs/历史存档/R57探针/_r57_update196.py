# -*- coding: utf-8 -*-
"""更新对标清单 #196 备注：16 条红从「不可复现」改为「已修复（codegen）」。"""
import json
from pathlib import Path

F = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')

# 无损读取
raw = F.read_bytes().decode('utf-8')
data = json.loads(raw)
canonical = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
print('[自证] 规范序列化 == 原始文本:', canonical == raw)
assert canonical == raw, '无损自证失败，中止'

items = data['条目']
i196 = [x for x in items if x['编号'] == 196][0]
old_8 = (
    '⑧【第57轮更正】#195 所述「R54 引入 16 条新红（NameError: name \'错误\' is not defined）」'
    '**经复核不成立**：该 16 条只在 6 份基线中 5 轮红、最终真基线 072454 该文件 0 红；'
    '0.82 当前副本定向跑 tests/test_stdlib_phase9.py **57 passed**（独立复核）；'
    '错误 ∉ VERB_ARITY/STDLIB/ALL_VERB 而 R54 两处改动全以 VERB_ARITY 为键→结构上碰不到；'
    '判为当时副本局部状态，parser_stmt.py 本轮未改。'
)
new_8 = (
    '⑧【第57轮更正·路M复核】#195 所述「R54 引入 16 条新红（NameError: name \'错误\' is not defined）」'
    '**确认为真并已修复**：初判「不可复现」是定向跑假象——触发条件是 test_bootstrap_light.py 的'
    '_light_import_hook 装钩子（全量/组合跑先导入即生效）→ 编译纯光明 stdlib/断言工具.light → '
    '类继承基类名没走 exception_name_map（class 断言失败异常(错误):）→ 运行期 NameError；'
    'py3.12 xdist 下 phase9 所在 worker 是否装过钩子随机 → R56 各轮红绿抖动根因即此。'
    '修复：code_generator.py 类基类补 _resolve_exception_type（错误→Exception），本机组合复现转绿、'
    '0.82 终跑全量 99 红（phase9 16 条消失）、与真基线 072454 对拍新增红 0。'
    '归因修正：真实缺陷是「钩子+codegen 类基类不映射」，非 parser_stmt（R54 两处改动以 VERB_ARITY 为键、错误∉VERB_ARITY）。'
)

assert old_8 in i196['备注'], '未找到 #196 备注中的 ⑧ 段，中止（内容可能已变）'
i196['备注'] = i196['备注'].replace(old_8, new_8)

# 无损写回
out = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
assert not out.endswith('\n')
F.write_bytes(out.encode('utf-8'))
print('[写回] 完成')
data2 = json.loads(F.read_bytes().decode('utf-8'))
print('[回读] 条目数', len(data2['条目']), '｜ 196 备注含「确认为真并已修复」:', '确认为真并已修复' in [x['备注'] for x in data2['条目'] if x['编号'] == 196][0])

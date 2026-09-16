# -*- coding: utf-8 -*-
"""R23 任务3 探针：CCW × codegen 内建登记 交叉对比。

静态 AST 解析 src/code_generator.py，抽出所有 `self.<name>_map = {...}` 形式的映射表，
与 COMMON_COMPOUND_WORDS 交叉，输出四分类候选清单。只读。
"""
import sys, ast, json

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
sys.path.insert(0, LIGHTP + '/src')
import lexer as L  # noqa

CG = LIGHTP + '/src/code_generator.py'
tree = ast.parse(open(CG, encoding='utf-8').read())


def str_keys(node):
    """从 Dict 字面量抽字符串字面量键（支持 | 合并与 **展开的简单情形）。"""
    keys = []
    if not isinstance(node, ast.Dict):
        return keys
    for k in node.keys:
        if isinstance(k, ast.Constant) and isinstance(k.value, str):
            keys.append(k.value)
    return keys


maps = {}          # self.xxx -> [keys]
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for tgt in node.targets:
            if isinstance(tgt, ast.Attribute) and isinstance(tgt.value, ast.Name) \
                    and tgt.value.id == 'self' and tgt.attr.endswith('_map'):
                ks = str_keys(node.value)
                if ks:
                    maps.setdefault(tgt.attr, []).extend(ks)
    # 类属性形式： Name = { ... }  (模块级/类级常量)
    if isinstance(node, ast.Assign):
        for tgt in node.targets:
            if isinstance(tgt, ast.Name) and tgt.id.isupper():
                ks = str_keys(node.value)
                if ks:
                    maps.setdefault('<module:' + tgt.id + '>', []).extend(ks)

for k, v in maps.items():
    maps[k] = sorted(set(v))

CCW = sorted(L.COMPOUND_COMPOUND) if hasattr(L, 'COMPOUND_COMPOUND') else sorted(L.COMMON_COMPOUND_WORDS)

print('=== code_generator 中的映射表 ===')
for k in sorted(maps):
    print(f'  {k}: {len(maps[k])} 条')

builtin = set(maps.get('builtin_map', []))
print(f'\n=== builtin_map {len(builtin)} 条 ===')
print('  ' + '  '.join(sorted(builtin)))

print(f'\n=== COMMON_COMPOUND_WORDS {len(CCW)} 条 ===')

allmap_keys = set()
for k, v in maps.items():
    allmap_keys |= set(v)

inter_builtin = [w for w in sorted(CCW) if w in builtin]
inter_any = [w for w in sorted(CCW) if w in allmap_keys and w not in builtin]
no_map = [w for w in sorted(CCW) if w not in allmap_keys]

print(f'\n[① 在 builtin_map] {len(inter_builtin)} 条: {inter_builtin}')
print(f'\n[② 在其它映射表] {len(inter_any)} 条: {inter_any}')
print(f'\n[③ 不在任何 codegen 映射] {len(no_map)} 条:')
for w in no_map:
    print('   ', w)

json.dump({'builtin_map': sorted(builtin),
           'all_map_keys': sorted(allmap_keys),
           'ccw': CCW,
           'cat1_builtin': inter_builtin,
           'cat2_other': inter_any,
           'cat3_none': no_map,
           'maps': {k: v for k, v in maps.items()}},
          open(ROOT + '/lightharness/_r23_t3_probe.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
print('\n已写 lightharness/_r23_t3_probe.json')

# -*- coding: utf-8 -*-
"""R58 探针4：base lexer vs patched lexer 的定向 token 对照。只读。"""
import sys, os, io, importlib.util

ROOT = r'G:\dswork\duan-light-merge'
LM = os.path.join(ROOT, 'light-merge')
sys.path.insert(0, os.path.join(LM, 'src'))
sys.path.insert(0, LM)


def load(p, n):
    spec = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


b = load(os.path.join(LM, '_r58_lexer_base.py'), 'lexB')
n = load(os.path.join(LM, 'src', 'lexer.py'), 'lexN')


def s(mod, x):
    try:
        return [(t.type.name, t.value) for t in mod.Lexer(x).tokenize()
                if t.type.name != 'EOF']
    except Exception as e:
        return 'EXC %s: %s' % (type(e).__name__, e)


TESTS = ['因为百分数', '因为', '认为三', '甲因为三', '因为三', '三加五', '设甲为三。',
         '甲为三', '设 甲为三', '因为百分数很高', '不是为空', '是否为空',
         '设为三', '甲为二', '称为三', '认为是真', '因为是真', '设 甲为百',
         '甲为百', '记为三', '数为三', '甲为十', '因为十个',
         '检查是否为十六进制数字', '检查是否为八进制数字', '设 是否为零 为 假',
         '是否为零', '设甲为五。', '导出事件表', '返回码', '接收参数', '非空块',
         '外部命令', '退出码', '排序依据', '输出块表', '记录类型', '甲.返回码',
         '整理模型消息', '设格式化为百分比(值, 小数位)', '为一组']
out = []
diff = 0
for q in TESTS:
    a, c = s(b, q), s(n, q)
    tag = 'SAME' if a == c else 'DIFF'
    if a != c:
        diff += 1
    out.append('%s %r' % (tag, q))
    if a != c:
        out.append('     base: %s' % (a,))
        out.append('     new : %s' % (c,))
out.append('')
out.append('DIFF %d / %d' % (diff, len(TESTS)))
txt = '\n'.join(out)
io.open(os.path.join(ROOT, 'lightharness', '_r58_probe4.txt'), 'w', encoding='utf-8').write(txt)
print(txt)

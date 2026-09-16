# -*- coding: utf-8 -*-
"""R23 任务1 边界/风险探针：找出「通用规则」相对旧白名单新增的行为差异（语料之外）。"""
import sys, os, subprocess, tempfile, importlib.util

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
sys.path.insert(0, LIGHTP + '/src')


def load(t, n):
    d = tempfile.mkdtemp(prefix='lxrb_')
    p = os.path.join(d, n + '.py')
    open(p, 'w', encoding='utf-8', newline='').write(t)
    s = importlib.util.spec_from_file_location(n, p)
    m = importlib.util.module_from_spec(s)
    sys.modules[n] = m
    s.loader.exec_module(m)
    return m


revs = subprocess.check_output(['git', '-C', LIGHTP, 'log', '--format=%H', '-n', '30'],
                               encoding='utf-8').split()
for rev in revs:
    t = subprocess.check_output(['git', '-C', LIGHTP, 'show', '%s:src/lexer.py' % rev],
                                encoding='utf-8')
    if '_TRAILING_ALIAS_CLASS' not in t:
        base = load(t, 'base_r23b')
        break
edit = load(open(LIGHTP + '/src/lexer.py', encoding='utf-8', newline='').read(), 'edit_r23b')


def tk(m, s):
    return ' '.join('%s' % t.value for t in m.Lexer(s).tokenize() if t.type.name != 'EOF')


FRAGS = [
    # 范围运算符（至/步/到）
    '甲至10', '甲到10', '甲步2', '1至10', '1到10步2', '甲至乙',
    # 逻辑/中缀运算符尾随非汉字
    '甲或"x"', '甲且"x"', '甲非"x"', '甲或乙', '甲且乙', '甲非乙',
    '不是无且self', '值或\'"\'',
    # await
    '甲等(乙)', '甲等待(乙)', '平台信息等。',
    # 常见「语句别名」尾随（期望并入）
    '错误己', '自己', '爱己', '预设', '投掷', '承运', '宏图', '往返回',
    '筛选器', '断言为真', '去重占位',
    # 词首语义（期望切分）
    '己姓名', '设 甲 为 1', '如果 真:', '段落 主:', '当 条件:', '若 甲:',
    # 值字面量
    '返回真', '甲空', '甲假',
]

print('%-16s | %-28s | %-28s | %s' % ('片段', '断裂态(白名单)', '修复态(通用类)', '差异'))
print('-' * 100)
diff = []
for f in FRAGS:
    try:
        a = tk(base, f)
    except Exception as e:  # noqa
        a = 'ERR ' + type(e).__name__
    try:
        b = tk(edit, f)
    except Exception as e:  # noqa
        b = 'ERR ' + type(e).__name__
    same = '  同' if a == b else '★差异'
    if a != b:
        diff.append(f)
    print('%-16s | %-28s | %-28s | %s' % (f, a[:28], b[:28], same))
print()
print('新增差异片段 %d 个：%s' % (len(diff), ' '.join(diff)))

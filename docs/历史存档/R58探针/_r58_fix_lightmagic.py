# -*- coding: utf-8 -*-
"""R58：断言工具.light 首行去「纯光明实现」魔数（与缺名回退 .py 设计矛盾）。
保持行尾/编码。"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\stdlib\断言工具.light')
raw = p.read_bytes()
text = raw.decode('utf-8')
was_crlf = '\r\n' in text
text_n = text.replace('\r\n', '\n')

old = '# 断言工具 —— 纯光明实现（原生腿安全子集）'
new = (
    '# 断言工具 —— 原生腿安全子集（完整实现见同名 .py，导入钩子按缺名回退）\n'
    '#\n'
    '# 设计：本文件只含「原生腿能真编译真跑」的纯函数断言（比较 / 成员 / 类型 /\n'
    '# 字符串 / 集合 / 数值 / 链式 / 判型）。它们不依赖「调用函数值」「按名取属性」，\n'
    '# 故可在 Python 后端与原生（O0）后端都工作。\n'
    '#\n'
    '# 「函数调用类 / 属性类」断言（断言抛出异常 / 断言满足条件 / 断言属性存在 等）\n'
    '# 需要把函数作为值动态调用，原生腿无此能力，不放在本 .light 里——Python 后端\n'
    '# 的导入钩子会回退加载同名 stdlib/断言工具.py（完整 Python 实现）提供这些能力，\n'
    '# 故 phase9 / phase3 等 Python 后端测试拿到的是完整 API。\n'
    '# ⚠️ R58：本文件**不带「纯光明实现」魔数**（见 _light_import_hook.py `_is_pure_light`）——\n'
    '#   带魔数会让钩子「优先加载 .light 并无视同名 .py」，与上文"缺名回退 .py"的设计矛盾，\n'
    '#   导致 phase9 在钩子装载环境下 from 断言工具 import 断言属性存在 等高级断言 ImportError\n'
    '#   （R57 门 PASS 靠未触发钩子的运气；R58 全量 131415 暴露 6 条）。去掉魔数后 .py 优先。\n'
    '#\n'
    '# 异常基类用「错误」（原生腿与 Python 后端都映射为 Exception）。'
)

if old not in text_n:
    print('[失败] 未找到魔数行')
    raise SystemExit(1)
text_n = text_n.replace(old, new, 1)
if was_crlf:
    text_n = text_n.replace('\n', '\r\n')
p.write_bytes(text_n.encode('utf-8'))
print('[成功] 已替换首行（原 CRLF=%s）' % was_crlf)
# 回读确认无魔数
t2 = p.read_text(encoding='utf-8')
print('[回读] 首行:', t2.splitlines()[0])
print('[回读] 含魔数「纯光明实现」:', '纯光明实现' in t2[:100])

# -*- coding: utf-8 -*-
"""R60 路M 收窄：parser_expr.py 异步拦截放行已定义名（修互举反跑 3 条误伤）。"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\src\parser_expr.py')
t = p.read_text(encoding='utf-8')

old = """        # 护栏：放行 _ALLOWED_ASYNC_PREFIXED_NAMES（见上方说明）——它们是真有映射的
        # 异步原语（`异步睡眠`）或已有专属报错的异步文件原语，不该被这条误伤。
        if (tok.type == TokenType.IDENTIFIER
                and tok.value.startswith('异步')
                and tok.value not in self._ALLOWED_ASYNC_PREFIXED_NAMES):"""

new = """        # 护栏：放行 _ALLOWED_ASYNC_PREFIXED_NAMES（见上方说明）——它们是真有映射的
        # 异步原语（`异步睡眠`）或已有专属报错的异步文件原语，不该被这条误伤。
        # R60 路M 收窄：同时放行 lexer 预扫描出的**已定义名**（`异步作用域`/`异步接受`/
        # `异步信号量` 等用户/库自定义名字在表达式位置是合法值；互举反跑 677 曾因误伤
        # 这 3 处新增解析失败）。未定义且 `异步` 开头 → 仍按修饰符误用拦截。
        _user_defs = getattr(self.lexer, 'user_definitions', None) or set()
        if (tok.type == TokenType.IDENTIFIER
                and tok.value.startswith('异步')
                and tok.value not in self._ALLOWED_ASYNC_PREFIXED_NAMES
                and tok.value not in _user_defs):"""

assert old in t, '未找到拦截段'
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')
print('PATCHED')
# 回读
t2 = p.read_text(encoding='utf-8')
for i, l in enumerate(t2.splitlines(), 1):
    if '_user_defs' in l and i < 680:
        print(f'L{i}: {l.strip()[:100]}')

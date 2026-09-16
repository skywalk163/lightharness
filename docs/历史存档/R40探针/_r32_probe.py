# -*- coding: utf-8 -*-
import sys, os
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
import lexer

def seq(t):
    try:
        return [(x.type.name, x.value) for x in lexer.Lexer(t, deterministic=True).tokenize()
                if x.type.name not in ('EOF','NEWLINE')]
    except Exception as e:
        return ['ERR:'+type(e).__name__]

print("=== 当前 OPERATOR_VERBS ===", sorted(lexer.OPERATOR_VERBS))
print("=== 当前 _OPERATOR_KEYWORDS 含比较? ===",
      {k: (k in lexer._OPERATOR_KEYWORDS) for k in ['等于','大于','包含','模','幂']})
print("=== 当前 Lexer._P0A_OP 含? ===",
      {k: (k in lexer.Lexer._P0A_OP) for k in ['等于','大于','加','模','幂','与']})

forms = {
 '比较运算符': ['甲 大于 乙','甲大于乙','甲 等于 乙','甲不等于乙','甲 包含 乙','大于号','等于号','包含关系'],
 '算术运算符': ['甲 加 乙','甲加乙','甲 减 乙','甲 乘 乙','甲 除 乙','甲 除以 乙','甲 模 乙','甲 幂 乙','加法','减法','乘法','除法','模型','模块','幂次'],
}
for grp, fs in forms.items():
    print("\n===== %s =====" % grp)
    for f in fs:
        print("  %-14s -> %s" % (f, seq(f)))

# R30 任务4 探针：测试_生成问候语 通用化边界分析
# 目标：确认 test_R27 反向 / test_R29 边界 / 快速验证形态的精确 token 流
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'light-merge', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'light-merge'))

from lexer import Lexer, TokenType

lx = Lexer()

def probe(name, code):
    try:
        toks = lx.tokenize(code)
        print(f"[{name}] {code!r}")
        for t in toks:
            print(f"    {t.type.name}: {t.value!r}")
        print()
    except Exception as e:
        print(f"[{name}] ERROR: {type(e).__name__}: {e}\n")

# ---- 1. test_R27 反向关键形态（调用/段落名）----
probe('R27段落声明_测试_返回真', '段落 测试_返回真:\n    返回 真\n')
probe('R27调用_测试_返回真', '断言相等(测试_返回真(), 真)')
probe('R27段落声明_测试_捕获到', '段落 测试_捕获到:\n    返回 "捕获到异常"\n')
probe('R27调用_测试_捕获到', '断言相等(测试_捕获到(), "捕获到异常")')
probe('R27段落声明_测试_返回语句', '段落 测试_返回语句:\n    返回 42\n')
probe('R27调用_测试_返回语句', '断言相等(测试_返回语句(), 42)')

# ---- 2. test_R29 边界：测试_生成问候语（CCW 保护中）----
probe('R29段落声明_测试_生成问候语', '段落 测试_生成问候语:\n    返回 "你好"\n')

# ---- 3. 任务书 4.1 快速验证形态 ----
probe('快速验证_返回_测试_生成问候语调用', '返回 测试_生成问候语(1)')
probe('设_测试_生成问候语', '设 a 为 测试_生成问候语(1)')

# ---- 4. 参考形态：无CCW保护的 _ 后缀汉字 ----
probe('调用_测试_等待', '测试_等待(1)')
probe('调用_测试_打印', '测试_打印(1)')
probe('调用_集合_加', '集合_加(1)')
probe('调用_集合_列表', '集合_列表(1)')
probe('段落名_集合_列表', '段落 集合_列表:\n    pass\n')

# ---- 5. 英文 snake_case 参考（:2008 规则已覆盖形态）----
probe('英文_l3_math_solve_例1_2', 'l3_math_solve_例1_2')
probe('英文_foo_减1', 'foo_减1')

print("CCW =", sorted(lx.COMMON_COMPOUND_WORDS) if hasattr(lx, 'COMMON_COMPOUND_WORDS') else sorted(getattr(sys.modules['lexer'], 'COMMON_COMPOUND_WORDS', set())))
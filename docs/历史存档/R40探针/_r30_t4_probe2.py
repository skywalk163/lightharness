# R30 任务4 探针2：模拟 CCW 置空，看测试_生成问候语 行为变化
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'light-merge', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'light-merge'))
import lexer as L

# 备份并置空 CCW
orig = L.COMMON_COMPOUND_WORDS
L.COMMON_COMPOUND_WORDS = frozenset()
L.Lexer.COMMON_COMPOUND_WORDS = frozenset()
lx = L.Lexer()

def probe(name, code):
    try:
        toks = lx.tokenize(code)
        print(f"[{name}] {code!r}")
        for t in toks:
            print(f"    {t.type.name}: {t.value!r}")
        print()
    except Exception as e:
        print(f"[{name}] ERROR: {type(e).__name__}: {e}\n")

print("=== CCW 置空后 ===")
probe('R29段落名', '段落 测试_生成问候语:\n    返回 "你好"\n')
probe('快速验证_返回调用', '返回 测试_生成问候语(1)')
probe('设调用', '设 a 为 测试_生成问候语(1)')
probe('R27段落_返回真', '段落 测试_返回真:\n    返回 真\n')
probe('R27调用_返回真', '断言相等(测试_返回真(), 真)')
probe('R27调用_返回语句', '断言相等(测试_返回语句(), 42)')
probe('R27段落_捕获到', '段落 测试_捕获到:\n    返回 "x"\n')
probe('R27调用_捕获到', '断言相等(测试_捕获到(), "x")')
probe('调用_集合_列表', '集合_列表(1)')
probe('英文_l3', 'l3_math_solve_例1_2')
probe('英文_foo_减1', 'foo_减1')
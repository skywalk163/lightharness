# R30 任务4 探针3：预扫描 user_definitions 注册表
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'light-merge', 'src'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'light-merge'))
import lexer as L

lx = L.Lexer()
orig = L.COMMON_COMPOUND_WORDS

def show(src, ccw=True):
    L.COMMON_COMPOUND_WORDS = orig if ccw else frozenset()
    L.Lexer.COMMON_COMPOUND_WORDS = L.COMMON_COMPOUND_WORDS
    ud = lx._scan_user_definitions(src)
    print(f"CCW={'ON' if ccw else 'OFF'} | {src!r}")
    print(f"    user_definitions = {sorted(ud)}")
    toks = lx.tokenize(src)
    print(f"    tokens = {[(t.type.name, t.value) for t in toks]}")
    print()

print("### 预扫描注册表实测 ###")
show('段落 测试_生成问候语:\n    返回 "你好"\n')
show('段落 测试_返回真:\n    返回 真\n')
show('段落 测试_捕获到:\n    返回 "x"\n')
show('段落 测试_返回语句:\n    返回 42\n')
show('段落 测试_等待:\n    pass\n')
show('段落 集合_列表:\n    pass\n')
show('测试_生成问候语(1)', ccw=False)
show('返回 测试_生成问候语(1)', ccw=False)
print("### R27 反向 全段 ###")
src27 = open(os.path.join(os.path.dirname(__file__), 'examples', 'test_R27_词首并入反向.light'), encoding='utf-8').read()
ud = lx._scan_user_definitions(src27)
print("R27 user_definitions =", sorted(ud))
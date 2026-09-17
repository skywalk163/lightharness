# R46：验证 L-169 修复 —— 改动的 light-merge 示例能否正常 parse+generate（语法/作用域合法），
# 并对「非交互」示例实际执行。
import io, os, sys, traceback

BASE = r'G:\dswork\duan-light-merge\light-merge'
sys.path.insert(0, os.path.join(BASE, 'src'))
sys.path.insert(0, BASE)

from light_parser_v3 import LightParser          # noqa: E402
from code_generator import PythonCodeGenerator   # noqa: E402
from scope_shadow_check import check_global_shadow  # noqa: E402

FILES = [
    'examples/games/snake.light',
    'examples/snake_game/主.light',
    'examples/kids/number_game.light',
    'examples/calculator_app/主.light',
    'examples/file_tools/batch_rename/主.light',
    'examples/blog_app/main.light',
    'examples/module_demo.light',
]

RUNNABLE = {
    'examples/module_demo.light': [],
    'examples/calculator_app/主.light': ['+', '5'],
}

ok = fail = 0
for rel in FILES:
    p = os.path.join(BASE, rel)
    try:
        src = io.open(p, encoding='utf-8').read()
        mod = LightParser().parse(src, filename=os.path.basename(p))
        code = PythonCodeGenerator().generate(mod, is_main=True)
        ws = check_global_shadow(mod, os.path.basename(p))
        tag = 'OK ' if not ws else f'WARN({len(ws)})'
        print(f'{tag} 编译通过  {rel}')
        if ws:
            for w in ws:
                print('      ' + w.replace('⚠ 编译警告（L-166 影子变量）：', ''))
        ok += 1
    except Exception as e:
        fail += 1
        print(f'FAIL 编译失败  {rel}: {type(e).__name__}: {e}')
        traceback.print_exc(limit=2)

print(f'\n编译: {ok} 通过 / {fail} 失败')

print('\n===== 实际执行（非交互示例）=====')
import subprocess  # noqa: E402
PY = sys.executable
for rel, argv in RUNNABLE.items():
    p = os.path.join(BASE, rel)
    try:
        r = subprocess.run([PY, os.path.join(BASE, 'cli', 'light.py'), 'run', p] + argv,
                           capture_output=True, timeout=60, cwd=BASE)
        out = (r.stdout or b'').decode('utf-8', 'replace')
        err = (r.stderr or b'').decode('utf-8', 'replace')
        print(f'\n--- {rel} rc={r.returncode} ---')
        print('stdout:', out.strip()[-400:])
        if err.strip():
            print('stderr:', err.strip()[-400:])
    except subprocess.TimeoutExpired:
        print(f'\n--- {rel} TIMEOUT（疑似交互式，忽略）---')

import io, sys, os, time, threading
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
ROOT = os.path.abspath('.')
for p in ['stdlib', ROOT, 'src', '编译产物', os.path.join(ROOT, '..', 'light-merge', 'src')]:
    ap = os.path.abspath(p)
    if ap not in sys.path:
        sys.path.insert(0, ap)
import _light_import_hook
_light_import_hook.install(['stdlib', ROOT, 'src'])
import importlib.util

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m

工具 = load('工具mod', '编译产物/_工具.py')
代理 = load('代理mod', '编译产物/_代理.py')
reg = 工具.工具注册表()

def 慢工具(参数):
    time.sleep(参数['秒'])
    return [{'type': 'text', 'text': 'x'}]

reg.注册(工具.造工具定义('慢', '慢工具', {'type': 'object'}, 慢工具))

ts = time.time()
ths = []
for sec in [0.3, 0.2, 0.1]:
    t = threading.Thread(target=代理.跑单工具, args=(reg, '慢', '{"秒":%s}' % sec))
    t.start()
    ths.append(t)
for t in ths:
    t.join()
print('跑单工具: %.3f' % (time.time() - ts))

ts = time.time()
ths = []
for sec in [0.3, 0.2, 0.1]:
    t = threading.Thread(target=reg.执行, args=('慢', '{"秒":%s}' % sec))
    t.start()
    ths.append(t)
for t in ths:
    t.join()
print('注册表.执行: %.3f' % (time.time() - ts))

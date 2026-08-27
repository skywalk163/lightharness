# 由光明编译器生成
# 源文件: 光明代码

import sys
import os
import ctypes
from typing import Any, Optional
import math
import random

try:
    import importlib.util
except ImportError:
    importlib = None

# 解析 stdlib 路径（依次尝试多种可能）
_light_stdlib = None
try:
    _light_file_dir = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _light_file_dir = None
for _try_path in [
    os.path.join(_light_file_dir, 'stdlib') if _light_file_dir else None,
    os.path.join(_light_file_dir, '..', 'stdlib') if _light_file_dir else None,
    os.path.join(os.getcwd(), 'stdlib'),
    os.path.normpath(os.path.join(_light_file_dir, '..', '..', 'stdlib')) if _light_file_dir else None,
]:
    if _try_path and os.path.isdir(_try_path):
        _light_stdlib = _try_path
        break

if _light_stdlib and _light_stdlib not in sys.path:
    sys.path.insert(0, _light_stdlib)
if _light_stdlib:
    _light_parent = os.path.dirname(_light_stdlib)
    if _light_parent not in sys.path:
        sys.path.insert(0, _light_parent)

# 让 import 机制认识纯光明模块（只有 .light、没有 .py 的那种）
try:
    import _light_import_hook as _light_hook
    _light_hook.install([_light_stdlib, _light_file_dir, os.getcwd()])
except Exception:
    pass

# FFI 模块：尽量导入；失败则降级为占位对象（见 _light_ffi_available 特征位），避免非 FFI 程序因 stdlib 路径缺失而整体崩溃
try:
    import stdlib.FFI as _light_ffi
    _light_ffi_available = True
except Exception:
    _light_ffi_available = False
    class _LightFFIUnavailable:
        def __getattr__(self, _name):
            raise RuntimeError('FFI 不可用：未能导入 stdlib.FFI（请确认 stdlib 路径已加入 sys.path）')
    _light_ffi = _LightFFIUnavailable()

if importlib:
    try:
        _light_builtin_path = os.path.join(_light_stdlib, 'builtins.py')
        if os.path.isfile(_light_builtin_path):
            spec = importlib.util.spec_from_file_location('light_builtins', _light_builtin_path)
            _light_builtin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_light_builtin)
        else:
            raise ImportError()
    except:
        import types
        _light_builtin = types.ModuleType('_light_builtin')
        _light_builtin.读取文件 = lambda path: open(path, 'r', encoding='utf-8').read() if __import__('os').path.isfile(path) else ''
        _light_builtin._读文件 = lambda path: open(path, 'r', encoding='utf-8').read() if __import__('os').path.isfile(path) else ''
        _light_builtin.写入文件 = lambda path, content: open(path, 'w', encoding='utf-8').write(content) or None
        _light_builtin.删除文件 = lambda path: __import__('os').remove(path) if __import__('os').path.isfile(path) else None
        _light_builtin.删除目录 = lambda path: __import__('os').rmdir(path)
        _light_builtin.文件存在 = lambda path: __import__('os').path.isfile(path)
        _light_builtin.目录存在 = lambda path: __import__('os').path.isdir(path)
        _light_builtin.打印 = print
        _light_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\r\n')
        _light_builtin.读取N字节 = lambda n: sys.stdin.read(n)
        _light_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None
        _light_builtin.打印输出 = lambda t: print(t, flush=True)
        _light_builtin.刷新输出 = lambda: sys.stdout.flush()
        _light_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None
        _light_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)
        _light_builtin.解析JSON = lambda t: __import__('json').loads(t)
        _light_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))
        _light_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)
        _light_builtin.转字符串 = str
        _light_builtin.转整数 = int
        _light_builtin.转浮点 = float
        _light_builtin.chr = chr
        _light_builtin.bin = bin
        _light_builtin.hex = hex
        _light_builtin.oct = oct
        _light_builtin.列表创建 = list
        _light_builtin.列表长度 = len
        _light_builtin.列 = lambda *args: list(args)
        _light_builtin.列表追加 = lambda lst, item: lst.append(item)
        _light_builtin.列表获取 = lambda lst, i: lst[i]
        _light_builtin.列表弹出 = lambda lst, i=-1: lst.pop(i)
        _light_builtin.列表插入 = lambda lst, i, v: lst.insert(i, v)
        _light_builtin.列表包含 = lambda lst, item: item in lst
        _light_builtin.字符串包含 = lambda s, sub: sub in s
        _light_builtin.字符串反转 = lambda s: s[::-1]
        _light_builtin.字符串长度 = len
        _light_builtin.显示宽度 = lambda text: sum(2 if __import__('unicodedata').east_asian_width(ch) in ('W', 'F') else 1 for ch in str(text))
        _light_builtin.字符串获取 = lambda s, i: s[i]
        _light_builtin.截取 = lambda s, start, end: s[start:end]
        _light_builtin.转大写 = lambda s: s.upper()
        _light_builtin.转小写 = lambda s: s.lower()
        _light_builtin.结尾 = lambda s, suffix: s.endswith(suffix)
        _light_builtin.开头 = lambda s, prefix: s.startswith(prefix)
        _light_builtin.去除空白 = lambda s: s.strip()
        _light_builtin.分割字符串 = lambda s, sep=None: s.split(sep)
        _light_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)
        _light_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)
        _light_builtin.字典创建 = dict
        _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
        _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
        _light_builtin.字典键列表 = lambda d: list(d.keys())
        _light_builtin.字典包含键 = lambda d, k: k in d
        _light_builtin.时间戳 = lambda: __import__('time').time()
        _light_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)
else:
    import types
    _light_builtin = types.ModuleType('_light_builtin')
    _light_builtin.打印 = print
    _light_builtin.读取行 = lambda: sys.stdin.readline().rstrip('\n')
    _light_builtin.读取N字节 = lambda n: sys.stdin.read(n)
    _light_builtin.写入输出 = lambda t: (sys.stdout.write(t), sys.stdout.flush()) and None
    _light_builtin.打印输出 = lambda t: print(t, flush=True)
    _light_builtin.刷新输出 = lambda: sys.stdout.flush()
    _light_builtin.写入错误 = lambda t: (sys.stderr.write(t), sys.stderr.flush()) and None
    _light_builtin.打印错误 = lambda t: print(t, file=sys.stderr, flush=True)
    _light_builtin.解析JSON = lambda t: __import__('json').loads(t)
    _light_builtin.序列化JSON = lambda v, i=None: (__import__('json').dumps(v, ensure_ascii=False, indent=i) if i is not None else __import__('json').dumps(v, ensure_ascii=False))
    _light_builtin.美化JSON = lambda v: __import__('json').dumps(v, ensure_ascii=False, indent=2)
    _light_builtin.转字符串 = str
    _light_builtin.转整数 = int
    _light_builtin.转浮点 = float
    _light_builtin.chr = chr
    _light_builtin.bin = bin
    _light_builtin.hex = hex
    _light_builtin.oct = oct
    _light_builtin.列表创建 = list
    _light_builtin.列表长度 = len
    _light_builtin.列 = lambda *args: list(args)
    _light_builtin.列表追加 = lambda lst, item: lst.append(item)
    _light_builtin.列表获取 = lambda lst, i: lst[i]
    _light_builtin.列表弹出 = lambda lst, i=-1: lst.pop(i)
    _light_builtin.列表插入 = lambda lst, i, v: lst.insert(i, v)
    _light_builtin.列表包含 = lambda lst, item: item in lst
    _light_builtin.字符串包含 = lambda s, sub: sub in s
    _light_builtin.字符串反转 = lambda s: s[::-1]
    _light_builtin.字符串长度 = len
    _light_builtin.字符串获取 = lambda s, i: s[i]
    _light_builtin.截取 = lambda s, start, end: s[start:end]
    _light_builtin.转大写 = lambda s: s.upper()
    _light_builtin.转小写 = lambda s: s.lower()
    _light_builtin.结尾 = lambda s, suffix: s.endswith(suffix)
    _light_builtin.开头 = lambda s, prefix: s.startswith(prefix)
    _light_builtin.去除空白 = lambda s: s.strip()
    _light_builtin.分割字符串 = lambda s, sep=None: s.split(sep)
    _light_builtin.连接字符串 = lambda parts, sep='': sep.join(parts)
    _light_builtin.替换字符串 = lambda s, old, new: s.replace(old, new)
    _light_builtin.字典创建 = dict
    _light_builtin.字典设置 = lambda d, k, v: d.update({k: v})
    _light_builtin.字典获取 = lambda d, k, default=None: d.get(k, default)
    _light_builtin.字典键列表 = lambda d: list(d.keys())
    _light_builtin.字典包含键 = lambda d, k: k in d
    _light_builtin.时间戳 = lambda: __import__('time').time()
    _light_builtin.格式化时间 = lambda t, f='%Y-%m-%d %H:%M:%S': __import__('datetime').datetime.fromtimestamp(t).strftime(f) if isinstance(t, (int, float)) else __import__('datetime').datetime.strptime(t, '%Y-%m-%d %H:%M:%S').strftime(f)

# stdlib 物理缺失时的兜底：补齐常用 builtin + 注册 文件系统 模块
for _light_n, _light_f in [
    ('列表排序', lambda lst, 反向=False: lst.sort(reverse=反向)),
    ('列表反转', lambda lst: lst.reverse()),
    ('列表清空', lambda lst: lst.clear()),
    ('列表移除', lambda lst, item: lst.remove(item)),
    ('列表长度', len),
    ('追加文件', lambda path, content, encoding='utf-8': open(path, 'a', encoding=encoding).write(content) or None),
    ('删除文件', lambda path: __import__('os').remove(path) if __import__('os').path.isfile(path) else None),
    ('复制文件', lambda src, dst: __import__('shutil').copy2(src, dst)),
    ('移动文件', lambda src, dst: __import__('shutil').move(src, dst)),
    ('创建目录', lambda path: __import__('os').makedirs(path, exist_ok=True)),
    ('删除目录', lambda path: __import__('shutil').rmtree(path)),
    ('路径连接', lambda *parts: __import__('os').path.join(*parts)),
    ('当前工作目录', lambda: __import__('os').getcwd()),
]:
    if not hasattr(_light_builtin, _light_n):
        setattr(_light_builtin, _light_n, _light_f)
if (not _light_stdlib) or (not os.path.isdir(_light_stdlib or '')):
    try:
        import types as _light_types
        _light_fs = _light_types.ModuleType('文件系统')
        for _light_fn in ('读取文件', '写入文件', '追加文件', '文件存在', '删除文件', '复制文件', '移动文件', '创建目录', '删除目录', '目录存在', '路径连接', '当前工作目录', '读取行'):
            if hasattr(_light_builtin, _light_fn):
                setattr(_light_fs, _light_fn, getattr(_light_builtin, _light_fn))
        sys.modules.setdefault('文件系统', _light_fs)
    except Exception:
        pass
# 可空类型解包辅助函数
def _light_unwrap(_x):
    assert _x is not None, "尝试解包空值"
    return _x

# 断言辅助函数
def _light_assert(_cond, _msg=''):
    if not _cond:
        raise AssertionError(_msg)

# 连接辅助函数（列表.连接(分隔符) 与 分隔符.连接(列表) 均可）
def _light_join(_o, _s=''):
    if isinstance(_o, str):
        return _o.join(_s)
    return _s.join([_x if isinstance(_x, str) else str(_x) for _x in _o])

class 事件总线:
    def __init__(self):
        self.监听器表 = {}

    def 订阅(self, 事件名, 处理器):
        if ((事件名 in self.监听器表) == False):
            self.监听器表[事件名] = []
        self.监听器表[事件名].append(处理器)
        return 造取消处理器(self, 事件名, 处理器)

    def 发布(self, 事件名, 参数):
        if ((事件名 in self.监听器表) == False):
            return
        for 处理器 in self.监听器表[事件名]:
            处理器(参数)

    def 瀑布(self, 事件名, 参数, 收尾):
        处理过 = False
        if (事件名 in self.监听器表):
            for 处理器 in self.监听器表[事件名]:
                已消费 = 处理器(参数)
                if 已消费:
                    处理过 = True
                    return True
        if (收尾 != None):
            收尾(参数)
        return False

    def 有监听器(self, 事件名):
        return ((事件名 in self.监听器表) and (len(self.监听器表[事件名]) > 0))


def 造取消处理器(总线, 事件名, 处理器):
    def 取消():
        if (事件名 in 总线.监听器表):
            表 = 总线.监听器表([事件名])
            新表 = []
            for 项 in 表:
                if (项 != 处理器):
                    新表.append(项)
            总线.监听器表[事件名] = 新表

    return 取消

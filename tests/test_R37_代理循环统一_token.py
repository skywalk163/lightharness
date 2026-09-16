# -*- coding: utf-8 -*-
"""R37 任务5：代理循环统一（R34-D3）pytest。

覆盖：
  1) 同名冲突已消除：`代理循环.light` 只存在于 src/，stdlib/ 下已无该名；
     重命名目标 `代理运行时.light` 存在于 stdlib/。
  2) 导入路径正确性：`examples/test_代理循环.light` 与 `examples/test_R34_集成测试.light`
     从 `代理循环` 模块导入的每个符号，都在 `src/代理循环.light` 的导出清单中
     （即解析对象是 src 新版，而非旧 stdlib 版）。
  3) 统一后文件 tokenize 正常（词法零异常）。
  4) 剩余同名冲突登记（`加密.light`/`重试.light`，均为 R37 范围外的既有分层）——
     用「已知集合」守卫，防止再新增未处理的同名模块。

注：agent-default-model（任务2）核心功能覆盖**待任务2 交付后补做**，见
    examples/test_R37_集成测试.light §5 占位。
"""
import os
import re
import sys
import glob

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
STDLIB = os.path.join(ROOT, 'stdlib')
EXAMPLES = os.path.join(ROOT, 'examples')
sys.path.insert(0, os.path.join(ROOT, '..', 'light-merge', 'src'))
import lexer  # noqa: E402

# R37 范围外、已知的既有同名分层（src 与 stdlib 各有一份）；代理循环 已在 R37 统一。
KNOWN_REMAINING_COLLISIONS = {'加密.light', '重试.light'}


def _basenames(d):
    return {os.path.basename(p) for p in glob.glob(os.path.join(d, '*.light'))}


def _exports(path):
    """解析 .light 文件里 `导出 a b c` / `导出 a, b` 形式的导出名集合。"""
    names = set()
    for line in open(path, encoding='utf-8-sig', errors='replace'):
        s = line.strip()
        if s.startswith('导出 '):
            for tok in re.split(r'[\s,]+', s[len('导出 '):].strip()):
                if tok:
                    names.add(tok)
    return names


def _module_imports(path):
    """解析 `从 X 导入 a, b, c` → {X: {a,b,c}}。"""
    out = {}
    for line in open(path, encoding='utf-8-sig', errors='replace'):
        s = line.strip()
        m = re.match(r'^从\s+(\S+)\s+导入\s+(.+)$', s)
        if m:
            mod = m.group(1)
            syms = {t for t in re.split(r'[,\s]+', m.group(2).strip()) if t}
            out.setdefault(mod, set()).update(syms)
    return out


def test_代理循环_同名冲突已消除():
    src = _basenames(SRC)
    std = _basenames(STDLIB)
    assert '代理循环.light' in src, 'src/代理循环.light 应存在（核心层）'
    assert '代理循环.light' not in std, 'stdlib/ 下不应再有 代理循环.light（R37 已重命名）'
    assert '代理运行时.light' in std, 'stdlib/代理运行时.light 应存在（重命名目标）'


def test_剩余同名冲突仅为已知集合():
    inter = _basenames(SRC) & _basenames(STDLIB)
    assert inter <= KNOWN_REMAINING_COLLISIONS, (
        f'出现未处理的 src/stdlib 同名模块：{sorted(inter - KNOWN_REMAINING_COLLISIONS)}；'
        f'请像 R37 的 代理循环 那样评估统一方案')


def test_导入符号由src代理循环导出():
    """两个从 `代理循环` 模块导入的测试，其符号必须都在 src/代理循环.light 导出清单内。"""
    exports = _exports(os.path.join(SRC, '代理循环.light'))
    for tf in ['test_代理循环.light', 'test_R34_集成测试.light']:
        p = os.path.join(EXAMPLES, tf)
        assert os.path.isfile(p), f'{tf} 不存在'
        imps = _module_imports(p)
        assert '代理循环' in imps, f'{tf} 应从 代理循环 模块导入'
        missing = imps['代理循环'] - exports
        assert not missing, f'{tf} 从 代理循环 导入的符号不在 src 导出中：{sorted(missing)}'


def _tokenize_ok(path):
    text = open(path, encoding='utf-8-sig', errors='replace').read()
    list(lexer.Lexer(text, deterministic=True).tokenize())
    return True


@pytest.mark.parametrize('path', [
    os.path.join(STDLIB, '代理运行时.light'),
    os.path.join(SRC, '代理循环.light'),
    os.path.join(EXAMPLES, 'test_R37_集成测试.light'),
])
def test_统一相关文件tokenize正常(path):
    assert _tokenize_ok(path), f'{path} tokenize 应无异常'


def test_代理运行时保留旧版导出():
    """重命名不改模块内容：旧版导出（会话/代理循环）应保持。"""
    exports = _exports(os.path.join(STDLIB, '代理运行时.light'))
    assert {'会话', '代理循环'} <= exports, f'代理运行时 导出应含 会话/代理循环，实际 {sorted(exports)}'

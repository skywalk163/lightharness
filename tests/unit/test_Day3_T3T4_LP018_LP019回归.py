# -*- coding: utf-8 -*-
"""Day3 清晨 T3/T4：LP-D-018（SRC `返回 关键字词变量名`）与 LP-D-019②（ANTLR 判型族注册）
的探针回归用例。

背景与口径：
  · LP-D-018：`返回 跳过`（跳过 是已声明关键字词变量）在 SRC 后端返回 None。
    根因在 src/lexer.py 的「已声明关键字词重分类」——它只在变量名后随
    `.`/`[`/`(` 时才降级为 IDENTIFIER，`返回 跳过` 处无后缀故漏降级，
    被 parser_stmt._parse_return_stmt 当语句关键字吃掉，产物成了裸 `return`。
    修法：补「前随 返回/返 且**同行**」的降级分支。
  · ⚠️ 同行约束是硬要求（本文件 test_LP018_反例* 就是防它复发）：
    向前回溯若跨过 NEWLINE，会把「裸 返回 之后另起一行的 跳过 语句」
    （含跨 DEDENT 出块的情形）误降级，continue 被改写成 `跳过()` 表达式
    —— 循环不再短路，且对同名整型变量求值调用直接 TypeError。
    实测（改动跨行回溯版）：lp018_反例_返回后隔DEDENT跳过 → rc=1
    TypeError: 'int' object is not callable；改为同行回溯后 rc=0 输出 3。
  · LP-D-019②：ANTLR 后端未注册判型族内置 `是数字`/`是数字符` → 未定义的变量。
    修法：antlrparser/light_builtins.py 注册两条，语义与 SRC 对齐：
      是数字(x)   = 是数值（int/float，排 bool）
      是数字符(s) = str.isdigit

探针（docs/国庆7天/probes/，本文件不改探针，只按绝对路径调用）：
  · lp018_返回关键字词变量.light      —— 主症；两后端都应输出两行 [7]
  · lp018_对照_普通名.light           —— 反向对照（变量名换成普通名）；两后端 [7]/[7]
  · lp018_反例_返回后跟跳过.light      —— 同行反例：裸返回后另起一行 跳过（同缩进）
  · lp018_反例_返回后隔DEDENT跳过.light —— 跨块反例：裸返回缩进更深，跳过 在块外
  · lp019_判型族.light                —— 判型族；两后端都应 True/False/True

运行方式（Git Bash）：
  cd /g/dswork/duan-light-merge/lightharness && python -m pytest \
      tests/unit/test_Day3_T3T4_LP018_LP019回归.py -q -o "addopts=" -p no:xdist
"""
import os
import subprocess
from pathlib import Path

import pytest

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_LIGHT_MERGE = _WORKSPACE_ROOT / 'light-merge'
_VENV_PYTHON = _LIGHT_MERGE / '.venv' / 'Scripts' / 'python.exe'
_CLI = _LIGHT_MERGE / 'cli' / 'light.py'
_PROBES_DIR = _WORKSPACE_ROOT / 'lightharness' / 'docs' / '国庆7天' / 'probes'

_P_LP018_主症 = _PROBES_DIR / 'lp018_返回关键字词变量.light'
_P_LP018_对照 = _PROBES_DIR / 'lp018_对照_普通名.light'
_P_LP018_反例同行 = _PROBES_DIR / 'lp018_反例_返回后跟跳过.light'
_P_LP018_反例跨块 = _PROBES_DIR / 'lp018_反例_返回后隔DEDENT跳过.light'
_P_LP019_判型族 = _PROBES_DIR / 'lp019_判型族.light'

_ALL_PROBES = (_P_LP018_主症, _P_LP018_对照, _P_LP018_反例同行,
               _P_LP018_反例跨块, _P_LP019_判型族)

_SUBPROC_ENV = {**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8'}
_TIMEOUT = 120


def _run_probe(probe: Path, backend: str):
    """真实 CLI 调用：python cli/light.py run <探针绝对路径> [--backend antlr]。"""
    cmd = [str(_VENV_PYTHON), str(_CLI), 'run', str(probe)]
    if backend != 'src':
        cmd += ['--backend', backend]
    r = subprocess.run(
        cmd, capture_output=True, text=True, encoding='utf-8',
        cwd=str(_LIGHT_MERGE), timeout=_TIMEOUT, env=_SUBPROC_ENV,
    )
    return r.returncode, r.stdout, r.stderr


def _require_paths():
    """路径不齐（venv/CLI/探针缺失）时 skip，不误报为断言失败。"""
    missing = [str(p) for p in (_VENV_PYTHON, _CLI, *_ALL_PROBES) if not p.exists()]
    if missing:
        pytest.skip(f'路径缺失，跳过: {missing}')


def _lines(out: str):
    return [ln.strip() for ln in out.splitlines() if ln.strip()]


# ── LP-D-018 主症：SRC 后端 `返回 跳过` 必须取到值 ──────────────────────────

def test_LP018_主症_SRC_两行都是7():
    _require_paths()
    rc, out, err = _run_probe(_P_LP018_主症, 'src')
    assert rc == 0, f'[SRC 主症] 退出码 {rc}:\n{err}\n{out}'
    assert _lines(out) == ['[7]', '[7]'], (
        f'[SRC 主症] 期望 [7]/[7]，实际 {_lines(out)}（None = 返回未取到变量值）:\n{out}'
    )


def test_LP018_主症_ANTLR_两行都是7():
    _require_paths()
    rc, out, err = _run_probe(_P_LP018_主症, 'antlr')
    assert rc == 0, f'[ANTLR 主症] 退出码 {rc}:\n{err}\n{out}'
    assert _lines(out) == ['[7]', '[7]'], f'[ANTLR 主症] 实际 {_lines(out)}:\n{out}'


def test_LP018_两后端输出一致():
    _require_paths()
    rc_s, out_s, _ = _run_probe(_P_LP018_主症, 'src')
    rc_a, out_a, _ = _run_probe(_P_LP018_主症, 'antlr')
    assert (rc_s, _lines(out_s)) == (rc_a, _lines(out_a)), (
        f'两后端不一致：SRC rc={rc_s} {_lines(out_s)} / ANTLR rc={rc_a} {_lines(out_a)}'
    )


def test_LP018_反向对照_普通名两后端均7():
    """缺口来自「关键字词作变量名」而非「返回列表」本身。"""
    _require_paths()
    for be in ('src', 'antlr'):
        rc, out, err = _run_probe(_P_LP018_对照, be)
        assert rc == 0, f'[对照 {be}] 退出码 {rc}:\n{err}\n{out}'
        assert _lines(out) == ['[7]', '[7]'], f'[对照 {be}] 实际 {_lines(out)}:\n{out}'


# ── LP-D-018 反例：`跳过` 作为 continue 语句不得被误降级（防跨行回溯复发）──────

def test_LP018_反例同行_裸返回后接跳过仍是continue():
    """`返回`（裸）之后另起一行的 `跳过`（同缩进）必须仍是 continue 语句。
    若被误降级 → 变成无副作用表达式 → 落穿到下一句 → 多打「不应到达」。"""
    _require_paths()
    rc, out, err = _run_probe(_P_LP018_反例同行, 'src')
    assert rc == 0, f'[反例同行 SRC] 退出码 {rc}:\n{err}\n{out}'
    assert _lines(out) == ['3'], f'[反例同行 SRC] 期望 3，实际 {_lines(out)}:\n{out}'


def test_LP018_反例跨块_裸返回缩进更深的跳过仍是continue():
    """`返回`（在更深的块内）之后、回到外层缩进的 `跳过` 必须仍是 continue。
    跨行回溯版曾把 continue 改写成 `跳过()` → TypeError: 'int' object is not callable。"""
    _require_paths()
    rc, out, err = _run_probe(_P_LP018_反例跨块, 'src')
    assert rc == 0, (
        f'[反例跨块 SRC] 退出码 {rc}（continue 疑似被误降级成表达式调用）:\n{err}\n{out}'
    )
    assert _lines(out) == ['3'], f'[反例跨块 SRC] 期望 3，实际 {_lines(out)}:\n{out}'
    assert 'not callable' not in (out + err), f'[反例跨块 SRC] 出现调用错误:\n{err}'


def test_LP018_反例跨块_ANTLR同语义():
    """ANTLR 侧本就是 continue 语句，作为 SRC 的对齐基准。"""
    _require_paths()
    rc, out, err = _run_probe(_P_LP018_反例跨块, 'antlr')
    assert rc == 0, f'[反例跨块 ANTLR] 退出码 {rc}:\n{err}\n{out}'
    assert _lines(out) == ['3'], f'[反例跨块 ANTLR] 期望 3，实际 {_lines(out)}:\n{out}'


# ── LP-D-019② 判型族：ANTLR 注册面补齐 ────────────────────────────────────

def test_LP019判型族_两后端输出一致():
    _require_paths()
    rc_s, out_s, err_s = _run_probe(_P_LP019_判型族, 'src')
    rc_a, out_a, err_a = _run_probe(_P_LP019_判型族, 'antlr')
    assert rc_s == 0, f'[LP-D-019② SRC] 退出码 {rc_s}:\n{err_s}\n{out_s}'
    assert rc_a == 0, (
        f'[LP-D-019② ANTLR] 退出码 {rc_a}（判型族未注册 → 未定义的变量）:\n{err_a}\n{out_a}'
    )
    assert _lines(out_s) == _lines(out_a), (
        f'[LP-D-019②] 两后端不一致：SRC {_lines(out_s)} / ANTLR {_lines(out_a)}'
    )


def test_LP019判型族_语义正确():
    """是数字(x)=数值类型判定（排 bool）；是数字符(s)=str.isdigit。"""
    _require_paths()
    rc, out, err = _run_probe(_P_LP019_判型族, 'src')
    assert rc == 0, f'[LP-D-019② 语义] 退出码 {rc}:\n{err}\n{out}'
    assert _lines(out) == ['True', 'False', 'True'], (
        f'[LP-D-019② 语义] 期望 是数字(7)=True / 是数字("7")=False / 是数字符("7")=True，'
        f'实际 {_lines(out)}:\n{out}'
    )

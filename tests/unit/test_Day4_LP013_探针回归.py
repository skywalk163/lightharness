# -*- coding: utf-8 -*-
"""Day4 任务：LP-D-013 两例探针固化为 pytest 回归用例。

背景：
  lightharness/docs/国庆7天/probes/lp013_probe.light 与 lp013_probe2.light 是
  LP-D-013（中文词根/关键字词作成员访问基名）的已验证探针，在默认 SRC 后端
  已闭环销账。Day2 已选方案 A 收口 ANTLR 后端，故两个后端各跑同例回归。

探针内容（逐字摘自 docs/国庆7天/probes/，本文件不改探针文件，直接用绝对路径调用）：
  · lp013_probe.light：设 出 为 [] → 出.追加(1) → 打印(转字符串(甲()))，期望输出 [1]；
  · lp013_probe2.light：词根「跳过」作成员访问基名，期望退出码 0，且输出
    不得出现「无法识别的语法元素 '.'」。

✅ Day2 主会话实测（2026-10-02，light-merge d6b84a716 / lightharness f21c0191）：
  · SRC 后端两例 rc=0：probe1 输出 [1]；probe2 无「无法识别的语法元素」。
  · ANTLR 后端两例 rc=1：
    - probe1 第4行 第5列「多余的 '.'，此处应为 《、ID 等」+ 第3行「期望《、ID，却遇到了'为'」；
    - probe2 第4行 第6列「多余的 '.'，此处应为 <EOF>、K_IF、设 等」。
  · 原始日志：logs/day2/S4_antlr_lp013_probe_{src,antlr}.log{,.err}、
    logs/day2/S4_antlr_lp013_probe2_{src,antlr}.log{,.err}。
  · 判定：立账（ANTLR 后端对关键字/词根词作成员访问基名仍解析失败）。
    SRC 后端已销账；ANTLR 缺口保留为 xfail(strict=True 会因 strict=False 维持
    现状——此策略不变，仅把 reason 从「未实测」刷新为「已实测立账」）。

运行方式（Git Bash）：
  cd /g/dswork/duan-light-merge/lightharness && python -m pytest \
      tests/unit/test_Day4_LP013_探针回归.py -q -o "addopts=" -p no:xdist
  （-o addopts= 清掉 lightharness/pytest.ini 的 --timeout=60 -n 4 全局插件参数）
"""
import os
import subprocess
from pathlib import Path

import pytest

# 工作区根 = lightharness/tests/unit/test_*.py 的上三级（不写死盘符以外的相对歧义路径）
_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_LIGHT_MERGE = _WORKSPACE_ROOT / 'light-merge'
_VENV_PYTHON = _LIGHT_MERGE / '.venv' / 'Scripts' / 'python.exe'
_CLI = _LIGHT_MERGE / 'cli' / 'light.py'
_PROBES_DIR = _WORKSPACE_ROOT / 'lightharness' / 'docs' / '国庆7天' / 'probes'
_PROBE1 = _PROBES_DIR / 'lp013_probe.light'
_PROBE2 = _PROBES_DIR / 'lp013_probe2.light'

# 与 _archive/tmp-dirs/_tmp_head_A/tests 同款环境铺法：强制 UTF-8，避免 GBK 乱码
_SUBPROC_ENV = {
    **os.environ,
    'PYTHONUTF8': '1',
    'PYTHONIOENCODING': 'utf-8',
}

_TIMEOUT = 120  # 秒，任务指定

_ANTLR_XFAIL_REASON = (
    'Day2 主会话实测（light-merge d6b84a716）：ANTLR 后端两例均 rc=1，'
    'probe1 报「第4行第5列 多余的 .」+「第3行 期望《、ID却遇到为」；'
    'probe2 报「第4行第6列 多余的 .，应为 <EOF>/K_IF/设」。'
    'SRC 后端两例 rc=0 已销账；ANTLR 缺口立账，xfail 保留。'
    '日志：logs/day2/S4_antlr_lp013_probe*_{src,antlr}.log'
)


def _run_probe(probe: Path, backend: str):
    """真实 CLI 调用：python cli/light.py run <探针绝对路径> [--backend antlr]。

    与任务指定的运行方式一致：cd light-merge 后用 .venv 的 python 跑 cli/light.py。
    """
    cmd = [str(_VENV_PYTHON), str(_CLI), 'run', str(probe)]
    if backend != 'src':
        cmd += ['--backend', backend]
    r = subprocess.run(
        cmd,
        capture_output=True, text=True, encoding='utf-8',
        cwd=str(_LIGHT_MERGE), timeout=_TIMEOUT, env=_SUBPROC_ENV,
    )
    return r.returncode, r.stdout, r.stderr


def _require_paths():
    """路径不齐（venv/CLI/探针缺失）时 skip，不误报为断言失败。"""
    missing = [str(p) for p in (_VENV_PYTHON, _CLI, _PROBE1, _PROBE2) if not p.exists()]
    if missing:
        pytest.skip(f'路径缺失，跳过（不作为 LP-D-013 断言失败）: {missing}')


# ── SRC 默认后端：按任务规格断言（非本次实测结果，见文件头实测状态说明） ──────

def test_LP013_probe1_SRC_退出码0_输出含1():
    _require_paths()
    rc, out, err = _run_probe(_PROBE1, 'src')
    assert rc == 0, f'[SRC probe1] 退出码 {rc}:\n{err}\n{out}'
    assert '[1]' in out, f'[SRC probe1] 输出不含 [1]:\n{out[-500:]}'


def test_LP013_probe2_SRC_退出码0_无语法元素报错():
    _require_paths()
    rc, out, err = _run_probe(_PROBE2, 'src')
    assert rc == 0, f'[SRC probe2] 退出码 {rc}:\n{err}\n{out}'
    assert '无法识别的语法元素' not in (out + err), (
        f'[SRC probe2] 输出出现「无法识别的语法元素」:\n{(out + err)[-500:]}'
    )


# ── ANTLR 后端（--backend antlr）：实测未完成，按保守兜底 xfail(strict=False) ─
# 待主会话按步骤 1 真实跑过 4 个组合后：
#   · ANTLR 通过 → 去掉 xfail，改用与 SRC 相同的断言；
#   · ANTLR 失败 → 把真实失败输出（stdout/stderr 摘要）写进下方注释，替换本说明。

@pytest.mark.xfail(reason=_ANTLR_XFAIL_REASON, strict=False)
def test_LP013_probe1_ANTLR_退出码0_输出含1():
    _require_paths()
    rc, out, err = _run_probe(_PROBE1, 'antlr')
    # 期望（任务规格）：退出码 0，输出含 [1]（实跑后按真实结果收敛本断言）
    assert rc == 0, f'[ANTLR probe1] 退出码 {rc}:\n{err}\n{out}'
    assert '[1]' in out, f'[ANTLR probe1] 输出不含 [1]:\n{out[-500:]}'


@pytest.mark.xfail(reason=_ANTLR_XFAIL_REASON, strict=False)
def test_LP013_probe2_ANTLR_退出码0_无语法元素报错():
    _require_paths()
    rc, out, err = _run_probe(_PROBE2, 'antlr')
    # 期望（任务规格）：退出码 0，输出不含「无法识别的语法元素 '.'」
    assert rc == 0, f'[ANTLR probe2] 退出码 {rc}:\n{err}\n{out}'
    assert '无法识别的语法元素' not in (out + err), (
        f'[ANTLR probe2] 输出出现「无法识别的语法元素」:\n{(out + err)[-500:]}'
    )

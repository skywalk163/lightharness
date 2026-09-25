# -*- coding: utf-8 -*-
"""lightharness 单元测试共享基建（路线1：黑盒 .light 片段）。

设计
====
写小 .light 片段，用 `python 运行.py` 在隔离临时目录跑，断言退出码与 stdout。
.light 片段里可直接 `从 <src模块名> 导入 <符号>`——运行器会把 src/ 与 stdlib/
挂入导入路径，无需在片段里手写路径。

用法（在 tests/unit/test_xxx.py 里）::

    from tests.unit.test_support import run_light_source, assert_success, out_contains

    def test_会话格式往返():
        r = run_light_source('''
            从 会话格式 导入 编码V2事件, 解码V3事件
            从 JSON 导入 序列化JSON
            段落 主程序:
              设 帧 为 编码V2事件(新建事件())
              打印("LEN=" + 转字符串(长(帧)))
        ''')
        assert_success(r)
        out_contains(r, "LEN=")

也可以跑已有 .light 文件::

    r = run_light_file("examples/test_xxx.light")

隔离与副作用
=============
每个用例在 `tempfile.mkdtemp()` 里跑，文件副作用（临时目录、会话落盘、日志）
不污染仓库。examples/*.py 助手脚本会拷入临时目录的 examples/ 子目录，保持
与 test_回归.py 一致的相对引用能力。

与 test_回归.py 的分工
======================
- test_回归.py：523 个 examples 端到端退出码门禁（黑盒大场，不看内部状态）。
- tests/unit/：按模块编写的细粒度单测，一个 .light 片段聚焦一个函数/分支，
  stdout 打印关键中间值，Python 侧断言。这是 deepseek-harness 风格的包内
  单测层，只是 lightharness 的单测通过 .light 片段而非直调 Python 实现。
"""
from __future__ import annotations

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from typing import Optional

# tests/unit/test_support.py → tests/unit → tests → lightharness/
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNNER = os.path.join(ROOT, '运行.py')
EXAMPLES = os.path.join(ROOT, 'examples')


@dataclass
class LightResult:
    """一次 `python 运行.py <file.light>` 的结果。"""
    rc: int
    stdout: str
    stderr: str
    workdir: str
    light_file: str

    @property
    def output(self) -> str:
        """stdout + stderr 合并视图（与 test_回归.py 的 out 口径一致）。"""
        return (self.stdout or '') + (self.stderr or '')

    def tail(self, n: int = 800) -> str:
        return self.output[-n:]


def _prepare_workdir() -> str:
    """建隔离临时目录，拷入 examples/*.py 助手脚本。"""
    wd = tempfile.mkdtemp(prefix='lh_unit_')
    ex = os.path.join(wd, 'examples')
    os.makedirs(ex, exist_ok=True)
    for py in glob.glob(os.path.join(EXAMPLES, '*.py')):
        shutil.copy2(py, ex)
    return wd


def _invoke(light_file: str, wd: str, timeout: int, env: Optional[dict]) -> LightResult:
    full_env = dict(os.environ)
    full_env.setdefault('HARNESS_PY', sys.executable)
    if env:
        full_env.update(env)
    try:
        p = subprocess.run(
            [sys.executable, RUNNER, light_file],
            capture_output=True, text=True, encoding='utf-8', errors='replace',
            timeout=timeout, cwd=wd, env=full_env,
        )
        return LightResult(
            rc=p.returncode,
            stdout=p.stdout or '',
            stderr=p.stderr or '',
            workdir=wd,
            light_file=light_file,
        )
    finally:
        # 调用方决定是否保留 workdir（debug 时可设 keep_workdir=True）。
        # 默认清理；需要排查时设 LKEEP=1 环境变量。
        if not os.environ.get('LKEEP'):
            shutil.rmtree(wd, ignore_errors=True)


def run_light_source(source: str, *, timeout: int = 60, env: Optional[dict] = None,
                     filename: str = '_unit.light') -> LightResult:
    """把 .light 源码写到临时文件并运行。

    Args:
        source: .light 源码（UTF-8）。必须含 `段落 主程序:` 入口。
        timeout: 秒，默认 60。hang 住会被 kill 并抛 TimeoutExpired。
        env: 额外环境变量。
        filename: 临时 .light 文件名（仅用于报错定位，默认 _unit.light）。
    """
    wd = _prepare_workdir()
    lf = os.path.join(wd, filename)
    with open(lf, 'w', encoding='utf-8') as fh:
        fh.write(source)
    return _invoke(lf, wd, timeout, env)


def run_light_file(path: str, *, timeout: int = 60, env: Optional[dict] = None) -> LightResult:
    """跑已有 .light 文件（相对路径相对 lightharness 根，绝对路径原样）。"""
    if not os.path.isabs(path):
        path = os.path.join(ROOT, path)
    wd = _prepare_workdir()
    return _invoke(path, wd, timeout, env)


# ── 断言 helper ──────────────────────────────────────────────────────────

def assert_success(r: LightResult, msg: str = "") -> None:
    """断言 rc == 0。失败时打印输出尾便于定位。"""
    assert r.rc == 0, (
        f"期望 rc=0，实际 rc={r.rc}"
        + (f"（{msg}）" if msg else "")
        + f"\n--- stdout ---\n{r.stdout[-1500:]}"
        + f"\n--- stderr ---\n{r.stderr[-1500:]}"
    )


def assert_failure(r: LightResult, msg: str = "") -> None:
    """断言 rc != 0（反向哨兵：编译期/运行期应报错而非静默通过）。"""
    assert r.rc != 0, (
        f"期望 rc!=0（应报错），实际 rc=0（静默通过了！）"
        + (f"（{msg}）" if msg else "")
        + f"\n--- stdout ---\n{r.stdout[-800:]}"
    )


def out_contains(r: LightResult, needle: str, msg: str = "") -> None:
    """断言 stdout 包含 needle（在合并 output 里找，与门禁口径一致）。"""
    assert needle in r.output, (
        f"输出里找不到 {needle!r}"
        + (f"（{msg}）" if msg else "")
        + f"\n--- output tail ---\n{r.output[-1200:]}"
    )


def out_not_contains(r: LightResult, needle: str, msg: str = "") -> None:
    assert needle not in r.output, (
        f"输出里不该出现 {needle!r}"
        + (f"（{msg}）" if msg else "")
        + f"\n--- output tail ---\n{r.output[-1200:]}"
    )


def out_lines(r: LightResult) -> list[str]:
    """stdout 按行切分（去空行）。"""
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


# ── 模块清单（供分发与覆盖率对照用）────────────────────────────────────────
# 按业务域分组的核心模块。路1/路2/路3 分发时按此切分。
CORE_MODULES = {
    '会话域': ['会话格式', '会话存储', '会话持久化JSONL', '会话查询', '会话日志深化',
              '会话标题', '会话冷读', '会话引用深化', '会话轮次大纲', '会话控制类型'],
    '压缩与计量': ['压缩', '压缩E5', '令牌计量', '令牌估算', '溢出', '溢出保留'],
    '工具与执行': ['工具', '工具执行', '工具_bash', '工具_写文件', '工具_读文件',
                  '工具_搜索文件', '文件系统工具', '路径规则', '路径安全'],
    '权限与沙箱': ['审批', '权限', '安全策略', '沙箱', '沙箱策略', '授权链', '附件准入'],
    '代理与子代理': ['代理循环', '子代理核心', '子智能体', '子代理深化', '代理策略',
                   '目标折叠', '目标轮驱动', '团队花名册', '团队依赖图'],
    '宿主与IO': ['宿主IO', '宿主工具', '宿主运行时', '宿主配置', '宿主上下文',
                '真实文件系统提供者', '真实HTTP客户端', 'shell环境', '外壳环境'],
    '网络与外部': ['mcp客户端', 'webhook会话', '网络钩子GitHub', '搜索提供商',
                 '网页搜索', '真实抓取提供', 'web服务器', 'JSONRPC传输'],
    '存储与持久化': ['存储', '存储核心', '存储域', '持久化', '工作区', '工作区路径'],
    '协议与框架': ['系统提示', '交互命令', '交互工具', '钩子协议', '遥测',
                 '类型系统', '作用域', '预设', '预设深化', '消息'],
}

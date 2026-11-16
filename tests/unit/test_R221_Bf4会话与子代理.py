# -*- coding: utf-8 -*-
"""T-0369（R221-Bf4）判据：批量追加 / 运行时上下文提醒 / 子代理中断默认关。

被判对象：
  src/会话日志深化.light     （追加事件批 / 上下文提醒文本 / 上下文清空标记 / 上下文需刷新）
  src/会话.light             （记录事件批 类方法）
  src/子代理预设选择.light   （预选中断默认 / 预选含中断工具 / 预选工具名表）
  examples/test_R221_Bf4会话与子代理.light（30+ 组断言）

pytest 这层额外钉住两件 .light 判据难覆盖的事：
  ① 批量追加必须「先全量校验再落盘」（落盘语句在循环之后）；
  ② 中断默认的两个层次（内置组合=假 / 插件默认=真）不能被合并成一个开关。
"""
import io
import re
from pathlib import Path

from test_support import assert_success, out_contains, run_light_file

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "src" / "会话日志深化.light"
SESSION = ROOT / "src" / "会话.light"
SUB = ROOT / "src" / "子代理预设选择.light"
EXAMPLE = ROOT / "examples" / "test_R221_Bf4会话与子代理.light"

NEW_PARAGRAPHS = {
    "追加事件批": "会话日志深化.light",
    "上下文提醒文本": "会话日志深化.light",
    "上下文清空标记": "会话日志深化.light",
    "上下文需刷新": "会话日志深化.light",
    "记录事件批": "会话.light",
    "预选中断默认": "子代理预设选择.light",
    "预选含中断工具": "子代理预设选择.light",
    "预选工具名表": "子代理预设选择.light",
}


def _read(p: Path) -> str:
    assert p.exists(), f"缺文件 {p}"
    return io.open(p, encoding="utf-8").read()


def test_示例判据全绿():
    r = run_light_file("examples/test_R221_Bf4会话与子代理.light", timeout=180)
    assert_success(r, "R221-Bf4 光明判据")
    out_contains(r, "--- 测试 R221_Bf4会话与子代理 通过 ---")


def test_示例断言数不少于28():
    n = len(re.findall(r"^\s*断言(?:相等|真|含|抛含)\(", _read(EXAMPLE), flags=re.M))
    assert n >= 28, f"断言行只有 {n} 条，低于 28"


def test_新段落只在指定模块出现一次():
    names = {}
    for f in ROOT.joinpath("src").glob("*.light"):
        for line in _read(f).splitlines():
            m = re.match(r"^\s*段落\s+([^\s(]+)\s*\(", line)
            if m:
                names.setdefault(m.group(1), []).append(f.name)
    for p, owner in NEW_PARAGRAPHS.items():
        assert p in names, f"缺段落 {p}"
        assert names[p] == [owner], f"段落 {p} 位置异常：{names[p]}"


def test_新段落已导出():
    log_text = _read(LOG)
    sub_text = _read(SUB)
    for name in ("追加事件批", "上下文提醒文本", "上下文清空标记", "上下文需刷新"):
        assert any(l.startswith("导出 ") and name in l for l in log_text.splitlines()), f"会话日志深化 未导出 {name}"
    for name in ("预选中断默认", "预选含中断工具", "预选工具名表"):
        assert any(l.startswith("导出 ") and name in l for l in sub_text.splitlines()), f"子代理预设选择 未导出 {name}"


def test_批量追加先全量校验再落盘():
    """落盘语句必须出现在循环之后；在循环里写就会产生半批。"""
    text = _read(LOG)
    m = re.search(r"段落 追加事件批\(.*?\n(?=段落 )", text, flags=re.S)
    assert m, "找不到 追加事件批"
    body = m.group(0)
    loop_end = body.rindex("设 序号 为 序号 + 1")
    dump = body.index('列表追加(日志["事件表"], 记录)')
    assert dump > loop_end, "落盘语句出现在循环内（会写半批）"
    assert "全量校验通过后才落盘" in body


def test_中断默认两个层次分开():
    text = _read(SUB)
    m = re.search(r"段落 预选中断默认\(.*?\):(.*?)\n段落 ", text, flags=re.S)
    assert m, "找不到 预选中断默认"
    body = m.group(1)
    # 内置组合分支在前且返回假；兜底返回真
    assert body.index("返回 假") < body.index("返回 真"), "内置组合与插件默认被合并或顺序颠倒"


def test_会话批量方法复用单事件():
    """记录事件批 必须复用 记录事件（序号连续/钩子广播同源），不能另写一套。"""
    text = _read(SESSION)
    m = re.search(r"段落 记录事件批\(事件表\):(.*?)\n\n", text, flags=re.S)
    assert m, "找不到 记录事件批"
    body = m.group(1)
    assert "己.记录事件(" in body, "批量方法没有复用单事件入口"
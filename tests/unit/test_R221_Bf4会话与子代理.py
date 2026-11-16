# -*- coding: utf-8 -*-
"""T-0369（R221-Bf4）判据：批量追加 / 运行时上下文提醒 / 子代理中断默认关。

被判对象（上游 dsh-v0.2.2-rc.3 = 38a6a5c965）：
  src/会话.light             （记录事件 双重重载 + 记录事件批）
  src/会话日志深化.light     （追加事件批 + 上下文提醒/清空标记/需刷新 + 会话提醒* 投影组）
  src/子代理预设选择.light   （预选中断默认等中断两层次判定）
  src/代理团队.light         （Team 模式同规则 + 中断不改任务归属/队列）
  examples/test_R221_Bf4会话与子代理.light（判据文件）

pytest 这层额外钉住四件 .light 判据难覆盖或容易回退的事：
  ① 批量追加必须「先全量校验再落盘」（落盘语句在循环之后）；
  ② 批量与单事件必须是同一条入口（形状分派），不能另写一套；
  ③ 中断默认的两个层次（内置组合=假 / 插件默认=真）不能被合并成一个开关；
  ④ 运行时上下文提醒的首份引导语**不宣称**覆盖更早上下文，且正文转义闭合标签。
"""
import io
import re
from pathlib import Path

from test_support import assert_success, out_contains, run_light_file

ROOT = Path(__file__).resolve().parents[2]
LOG = ROOT / "src" / "会话日志深化.light"
SESSION = ROOT / "src" / "会话.light"
SUB = ROOT / "src" / "子代理预设选择.light"
TEAM = ROOT / "src" / "代理团队.light"
EXAMPLE = ROOT / "examples" / "test_R221_Bf4会话与子代理.light"

NEW_PARAGRAPHS = {
    "追加事件批": "会话日志深化.light",
    "上下文提醒文本": "会话日志深化.light",
    "上下文清空标记": "会话日志深化.light",
    "上下文需刷新": "会话日志深化.light",
    "上下文节表": "会话日志深化.light",
    "会话提醒投影": "会话日志深化.light",
    "会话提醒保留态": "会话日志深化.light",
    "会话提醒回灌": "会话日志深化.light",
    "会话提醒转义正文": "会话日志深化.light",
    "会话提醒渲染快照": "会话日志深化.light",
    "记录事件批": "会话.light",
    "预选中断默认": "子代理预设选择.light",
    "预选含中断工具": "子代理预设选择.light",
    "预选工具名表": "子代理预设选择.light",
    "预选插件默认中断": "子代理预设选择.light",
    "预选是内置组合": "子代理预设选择.light",
    "预选组合含中断": "子代理预设选择.light",
    "预选控制工具面": "子代理预设选择.light",
    "会话提醒团队工具名表": "代理团队.light",
    "会话提醒团队含中断": "代理团队.light",
    "会话提醒中断后任务快照": "代理团队.light",
}

# 本卡新增的「会话提醒」前缀段落（任务书要求的前缀）
PREFIX_PARAGRAPHS = (
    "会话提醒开标签", "会话提醒闭标签", "会话提醒清空正文", "会话提醒转义正文",
    "会话提醒引导语", "会话提醒拼正文", "会话提醒渲染快照", "会话提醒造源",
    "会话提醒保留态", "会话提醒投影", "会话提醒回灌",
    "会话提醒团队任务工具名表", "会话提醒团队工具名表", "会话提醒团队含中断",
    "会话提醒中断后任务快照", "会话提醒中断后未读数",
)


def _read(p: Path) -> str:
    assert p.exists(), f"缺文件 {p}"
    return io.open(p, encoding="utf-8").read()


def _body(text: str, name: str) -> str:
    """取一个段落的完整正文（到下一个段落/文件尾）。"""
    m = re.search(rf"段落 {re.escape(name)}\(.*?\n(?=段落 |\Z)", text, flags=re.S)
    assert m, f"找不到段落 {name}"
    return m.group(0)


def test_示例判据全绿():
    r = run_light_file("examples/test_R221_Bf4会话与子代理.light", timeout=180)
    assert_success(r, "R221-Bf4 光明判据")
    out_contains(r, "--- 测试 R221_Bf4会话与子代理 通过 ---")


def test_示例断言数不少于24():
    """任务书要求断言 ≥ 24 条（实际远超，这里只钉下限防回退）。"""
    n = len(re.findall(r"^\s*断言(?:相等|真|含|不含|抛含)\(", _read(EXAMPLE), flags=re.M))
    assert n >= 24, f"断言行只有 {n} 条，低于任务书下限 24"


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


def test_会话提醒前缀段落零冲突():
    """任务书：新增段落名一律带本卡专属前缀 会话提醒，且跨 src 不得重名。"""
    names = {}
    for f in ROOT.joinpath("src").glob("*.light"):
        for line in _read(f).splitlines():
            m = re.match(r"^\s*段落\s+([^\s(]+)\s*\(", line)
            if m:
                names.setdefault(m.group(1), []).append(f.name)
    for p in PREFIX_PARAGRAPHS:
        assert p.startswith("会话提醒"), f"{p} 缺本卡专属前缀"
        assert p in names, f"缺段落 {p}"
        assert len(names[p]) == 1, f"段落 {p} 跨文件冲突：{names[p]}"


def test_新段落已导出():
    log_text = _read(LOG)
    sub_text = _read(SUB)
    team_text = _read(TEAM)
    for name in ("追加事件批", "上下文提醒文本", "上下文清空标记", "上下文需刷新",
                 "上下文节表", "会话提醒投影", "会话提醒保留态", "会话提醒回灌",
                 "会话提醒转义正文", "会话提醒渲染快照"):
        assert any(l.startswith("导出 ") and name in l for l in log_text.splitlines()), f"会话日志深化 未导出 {name}"
    for name in ("预选中断默认", "预选含中断工具", "预选工具名表", "预选插件默认中断",
                 "预选是内置组合", "预选组合含中断", "预选控制工具面"):
        assert any(l.startswith("导出 ") and name in l for l in sub_text.splitlines()), f"子代理预设选择 未导出 {name}"
    for name in ("会话提醒团队任务工具名表", "会话提醒团队工具名表",
                 "会话提醒团队含中断", "会话提醒中断后任务快照"):
        assert any(l.startswith("导出 ") and name in l for l in team_text.splitlines()), f"代理团队 未导出 {name}"


def test_批量追加先全量校验再落盘():
    """落盘语句必须出现在循环之后；在循环里写就会产生半批。"""
    body = _body(_read(LOG), "追加事件批")
    loop_end = body.rindex("设 序号 为 序号 + 1")
    dump = body.index('列表追加(日志["事件表"], 记录)')
    assert dump > loop_end, "落盘语句出现在循环内（会写半批）"
    assert "全量校验通过后才落盘" in body


def test_会话双重重载是同一条入口():
    """记录事件 必须形状分派到 记录事件批，且批量方法复用 记录事件（不另写一套）。"""
    text = _read(SESSION)
    single = _body(text, "记录事件")
    assert "是字符串(类型) == 假" in single, "记录事件 没有按形状分派"
    assert "己.记录事件批(类型)" in single, "记录事件 未把数组形参转给 记录事件批"
    batch = _body(text, "记录事件批")
    assert "己.记录事件(" in batch, "批量方法没有复用单事件入口"
    # 空数组必须早退成空数组（对齐上游 inputs.length === 0）
    assert "[]" in batch, "批量方法缺空数组早退"


def test_中断默认两个层次分开():
    text = _read(SUB)
    plugin = _body(text, "预选插件默认中断")
    assert "返回 真" in plugin, "插件默认必须为真（上游 z.boolean().default(true)）"
    body = _body(text, "预选中断默认")
    # 内置组合分支在前且返回假；兜底返回真
    assert body.index("返回 假") < body.index("返回 真"), "内置组合与插件默认被合并或顺序颠倒"


def test_内置组合名表覆盖上游四处配置():
    """上游：base + web-app 的 standard/cordis/ptc 都写了 interrupt: false。"""
    text = _read(SUB)
    body = _body(text, "预选内置组合名表")
    for name in ("base", "standard", "cordis", "ptc"):
        assert f'"{name}"' in body, f"内置组合名表缺 {name}"


def test_中断关只关工具不关服务():
    text = _read(SUB)
    service = _body(text, "预选中断服务可用")
    assert "返回 真" in service, "中断服务 API 必须仍可用（上游 ctx.subagents.interrupt() 保留）"
    face = _body(text, "预选控制工具面")
    assert "中断服务可用" in face, "工具面没暴露服务可用性"


def test_上下文首份不宣称覆盖():
    """首份引导语必须**不宣称**覆盖更早上下文；后续才明确覆盖摘要。"""
    text = _read(LOG)
    first = _body(text, "会话提醒引导语")
    assert "不覆盖更早的上下文" in first, "首份引导语缺失或改成宣称覆盖"
    idx_first = first.index("不覆盖更早的上下文")
    idx_later = first.index("覆盖对话摘要里保留的旧上下文")
    assert idx_first < idx_later, "首次/后续分支顺序颠倒"


def test_上下文正文转义闭合标签():
    """正文里的 </system-reminder> 必须被转义，否则能提前关掉插件自己的框架。"""
    text = _read(LOG)
    esc = _body(text, "会话提醒转义正文")
    assert "转小写" in esc, "转义没做大小写不敏感（上游 /gi）"
    assert '"\\\\"' in esc or "\\\\" in esc, "转义没插入反斜杠"
    body_render = _body(text, "会话提醒渲染快照")
    assert "会话提醒转义正文" in body_render, "渲染快照没走转义"


def test_上下文清空标记形状():
    """清空标记必须带 form=snapshot 与空 sections（上游 CLEARED 常量的 source 形状）。"""
    text = _read(LOG)
    body = _body(text, "上下文清空标记")
    assert '"snapshot"' in body, "清空标记缺 form=snapshot"
    assert '"sections"' in body, "清空标记缺 sections"
    assert re.search(r'源\["sections"\]\s*为\s*\[\]', body), "清空标记的 sections 必须为空表"
    cleared = _body(text, "会话提醒清空正文")
    assert "Current runtime context: none." in cleared, "空快照正文与上游 CLEARED 常量不一致"


def test_旧记录只刷新一次的实现依据():
    """回灌后同条目必须判等 → 不再产消息；这要求投影做 deepEqual 与「有旧」判定。"""
    text = _read(LOG)
    proj = _body(text, "会话提醒投影")
    assert "旧节表 == 节表" in proj, "投影没做条目全等判定（会每轮刷文案）"
    assert "有旧 == 假" in proj, "投影没区分「从未有过快照」与「有过」"
    refeed = _body(text, "会话提醒回灌")
    assert '"存在"] 为 真' in refeed or '["存在"] 为 真' in refeed, "回灌没把保留态置为有"

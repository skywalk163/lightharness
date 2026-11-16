# -*- coding: utf-8 -*-
"""T-0364（R221-B7）判据：llm-deepseek 增补（R220 漏项，补做）。

被判对象：
  src/模型目录.light                     （新增 §B7：选择器徽章解码 + listed-catalog 徽章收集 + catalogModelInfo）
  src/模型列表缓存.light                  （新增 §B7：maxAge=0 语义 / 自动刷新排程 / 清单变化通知 / refresh 结算）
  examples/test_R221_B7模型增补.light     （光明判据，逐条标注上游 spec 名）

pytest 这层额外守住 .light 判据测不到的四件事：
  ① 示例必须真的绿（rc=0 且打印通过行与唯一标记串）；
  ② 两个被改模块的字节数比改前不减少（防「删旧逻辑充数」）；
  ③ 新增段落名跨 src/*.light 唯一且统一带「模型增补」前缀（光明里重名会静默串味）；
  ④ 反跑：把示例里一条断言的期望值改反，子进程 rc 必须变 1（防止判据假绿）。
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "src" / "模型目录.light"
CACHE = ROOT / "src" / "模型列表缓存.light"
EXAMPLE = ROOT / "examples" / "test_R221_B7模型增补.light"

EXAMPLE_REL = "examples/test_R221_B7模型增补.light"
PASS_LINE = "--- 测试 R221_B7模型增补 通过 ---"
UNIQUE_MARKER = "R221-B7-BADGE-MARKER"

# 改前字节数（R221-B7 起点提交 217b208 的本机工作树口径，CRLF）。只允许变大。
BASE_CATALOG_BYTES = 28906
BASE_CACHE_BYTES = 6693

NEW_CATALOG_PARAGRAPHS = [
    "模型增补_在区间", "模型增补_是控制码位", "模型增补_是行段分隔", "模型增补_是双向控制",
    "模型增补_是不可读码位", "模型增补_含不可读码位", "模型增补_是空白码位",
    "模型增补_是默认可忽略码位", "模型增补_有可见字素", "模型增补_是区域指示符",
    "模型增补_是附加记号", "模型增补_字素簇数", "模型增补_徽章文本", "模型增补_语言标识合法",
    "模型增补_本地化徽章文本", "模型增补_可选对象", "模型增补_非法徽章", "模型增补_徽章文本原因",
    "模型增补_选定色调", "模型增补_徽章", "模型增补_收集徽章", "模型增补_目录模型信息",
]
NEW_CACHE_PARAGRAPHS = [
    "模型增补缓存_视图刷新时机", "模型增补缓存_自动刷新延迟", "模型增补缓存_清单变化了",
    "模型增补缓存_通知", "模型增补缓存_通知失败文案", "模型增补缓存_刷新失败文案",
    "模型增补缓存_刷新结算", "模型增补缓存_释放结算", "模型增补缓存_作用域变了",
]
NEW_PARAGRAPHS = NEW_CATALOG_PARAGRAPHS + NEW_CACHE_PARAGRAPHS

OLD_CATALOG_EXPORTS = [
    "派生凭据引用", "校验收据路由", "合并提供商目录", "可删除判定", "删除序列",
    "构造发现请求", "发现地址", "发现请求头", "解析发现响应", "渲染提供商目录", "发现文案",
    "协议白名单", "默认协议", "模型清单地址", "已知模态", "容量值", "条目需求",
    "条目能力", "解码模型清单", "模型清单模态", "客户端产品",
]
OLD_CACHE_EXPORTS = [
    "默认列表超时_MS", "默认列表最大年龄_MS", "最大计时延迟_MS", "解析列表时序",
    "建模型列表缓存", "当前视图", "重定域", "启动", "视图", "失效", "释放",
]

# 上游逐字文案：改动即语义漂移，钉死。
PINNED_UPSTREAM_TEXT = [
    "client_metadata is not an object",
    ".badge.text is not a string or an object of lowercase language ids",
    "characters on one line",
    " shows no badge: ",
    "model listing change notification failed (",
    "reload the model catalog",
    "model listing refresh failed (",
    "keeping the previous catalog; check listing configuration and credentials",
]


def _read(p: Path) -> str:
    assert p.exists(), f"缺文件 {p}"
    return p.read_text(encoding="utf-8")


def _run_example(rel: str = EXAMPLE_REL, timeout: int = 180) -> subprocess.CompletedProcess:
    """按任务书口径跑光明判据：cwd=仓库根，捕获输出，180s 超时。"""
    return subprocess.run(
        [sys.executable, "运行.py", rel],
        cwd=str(ROOT), capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def _output(r: subprocess.CompletedProcess) -> str:
    return (r.stdout or "") + (r.stderr or "")


def test_示例判据全绿():
    r = _run_example()
    assert r.returncode == 0, (
        f"期望 rc=0，实际 rc={r.returncode}\n--- stdout ---\n{r.stdout[-1500:]}"
        f"\n--- stderr ---\n{r.stderr[-2500:]}"
    )
    out = _output(r)
    assert "通过" in out, f"输出里没有「通过」：{out[-1200:]}"
    assert PASS_LINE in out, f"缺通过行 {PASS_LINE!r}：{out[-1200:]}"
    assert UNIQUE_MARKER in out, f"缺唯一标记串 {UNIQUE_MARKER!r}（示例没真的跑到 B7 标记）"


def test_示例断言数不少于20且带上游标注():
    text = _read(EXAMPLE)
    n = len(re.findall(r"^\s*断言(?:相等|真|含|抛含)\(", text, flags=re.M))
    assert n >= 20, f"断言行只有 {n} 条，低于任务书要求的 20"
    # 每条断言组都在注释里标了上游用例/行为名（本卡的硬要求）。
    tags = set(re.findall(r"\[(?:badge\d*\w*|nobadge\d+|meta\d+|text\d+|proto|lang\d|"
                          r"catalog\d+|modelinfo\d+|timing\d+|publish\d+|identical\d+|"
                          r"retain\d|disabled\d+|signedout\d+|credlookup\d+|dispose\d+)\]", text))
    assert len(tags) >= 20, f"上游标注标签只有 {len(tags)} 个，低于 20"


def test_两个模块字节数不减少():
    """防止「删旧逻辑充数」：只允许变大。"""
    cat = CATALOG.stat().st_size
    cache = CACHE.stat().st_size
    assert cat >= BASE_CATALOG_BYTES, f"模型目录.light 从 {BASE_CATALOG_BYTES} 缩到 {cat}"
    assert cache >= BASE_CACHE_BYTES, f"模型列表缓存.light 从 {BASE_CACHE_BYTES} 缩到 {cache}"


def test_新段落全部存在且跨src不重名且统一前缀():
    names: dict[str, list[str]] = {}
    for f in ROOT.joinpath("src").glob("*.light"):
        for line in _read(f).splitlines():
            m = re.match(r"^段落\s+([^\s(:]+)\s*(?:\(|:)", line)
            if m:
                names.setdefault(m.group(1), []).append(f.name)
    for p in NEW_PARAGRAPHS:
        assert p.startswith("模型增补"), f"段落 {p} 没带「模型增补」前缀"
        assert p in names, f"缺段落 {p}"
        assert len(names[p]) == 1, f"段落 {p} 出现在多处：{names[p]}"
        owner = names[p][0]
        expect = "模型目录.light" if p in NEW_CATALOG_PARAGRAPHS else "模型列表缓存.light"
        assert owner == expect, f"段落 {p} 应在 {expect}，实际在 {owner}"


def test_既有导出未丢():
    for path, olds in ((CATALOG, OLD_CATALOG_EXPORTS), (CACHE, OLD_CACHE_EXPORTS)):
        text = _read(path)
        export_lines = [l for l in text.splitlines() if l.startswith("导出 ")]
        assert export_lines, f"{path.name} 没有导出行"
        blob = " ".join(export_lines)
        missing = [n for n in olds if n not in blob]
        assert not missing, f"{path.name} 既有导出被删：{missing}"


def test_上游文案逐字钉死():
    blob = _read(CATALOG) + _read(CACHE)
    for s in PINNED_UPSTREAM_TEXT:
        assert s in blob, f"缺上游逐字文案：{s!r}"


def test_反跑_改反一条期望值必须红():
    """卡上要求的反跑：改反示例里一条断言的期望值 → 子进程 rc=1；原文件不动。"""
    original = _read(EXAMPLE)
    needle = '"client_metadata is not an object"'
    assert original.count(needle) >= 1, "反跑锚点丢失"
    mutated = original.replace(needle, '"client_metadata IS not an object"', 1)
    with tempfile.TemporaryDirectory(prefix="lh_b7_flip_") as td:
        target = Path(td) / "test_R221_B7反跑.light"
        target.write_text(mutated, encoding="utf-8")
        r = _run_example(str(target), timeout=180)
    assert r.returncode != 0, (
        "改反期望值后仍然 rc=0（判据假绿！）\n--- stdout ---\n" + (r.stdout or "")[-1500:]
    )
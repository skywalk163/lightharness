# -*- coding: utf-8 -*-
"""T-0452 判据：网页工具接线（web_search / web_fetch），全部离线。

判据（对应任务卡）：
1. 缺 key：web_search 返回 isError=真，且文案点名缺哪个环境变量（不是空串）；
2. 注入假 provider：web_search 返回归一后的 sources（title/url/snippet），条数受 limit 约束；
3. web_fetch 拒绝 http://127.0.0.1/x、http://10.0.0.5/x、file:///etc/passwd、ftp://x，
   文案可读，且判定走 抓取策略（不自己写第二套）；
4. web_fetch 合法假响应：正文 > 32KB 时返回截断标志 + 头尾预览，不吐全文；
5. 两个工具定义过 工具.校验工具定义形状，名字恰为 web_search / web_fetch；
6. 反跑 A 锚点：私网拒绝那一行仍在源码里（删掉 → 用例 3 立红，反跑记录见 .hive/summary.md）。

红线：不联网（执行器/抓取器全部是假函数）、不新增依赖、错误文案可操作。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests" / "unit"))

from test_support import run_light_source, assert_success  # noqa: E402

SRC = ROOT / "src" / "工具_网页.light"
# 清空所有搜索密钥环境变量：用例 1/2 的「缺 key」「显式给 key」都不受宿主环境影响
CLEAR_ENV = {
    "DEEPSEEK_API_KEY": "",
    "HARNESS_API_KEY": "",
    "EXA_API_KEY": "",
    "PERPLEXITY_API_KEY": "",
}


def _run(source: str):
    r = run_light_source(source, env=CLEAR_ENV, timeout=90)
    assert_success(r)
    return r


# ---------------------------------------------------------------- 1. 缺 key
def test_缺key报错点名环境变量():
    r = _run('''
从 工具_网页 导入 造网页搜索工具定义

段落 空执行器(请求):
  返回 {}

段落 主程序:
  设 定义项 为 造网页搜索工具定义({"提供商": "deepseek-official", "密钥": "", "执行器": 空执行器})
  设 结果 为 定义项["execute"]({"query": "光明语言"})
  打印("ERR=" + 转字符串(结果["isError"]))
  打印("TXT=" + 结果["content"][0]["text"])
''')
    assert "ERR=True" in r.stdout, r.output
    assert "DEEPSEEK_API_KEY" in r.stdout, "缺 key 文案必须点名环境变量名\n" + r.output
    # 文案不是空串、且说明「不发请求」
    txt = [ln for ln in r.stdout.splitlines() if ln.startswith("TXT=")][0][4:]
    assert len(txt) > 20, "缺 key 文案过短：" + txt
    assert "不会发请求" in txt, txt


def test_缺key按提供商给对应变量名():
    r = _run('''
从 工具_网页 导入 造网页搜索工具定义, 网页工具状态

段落 空执行器(请求):
  返回 {}

段落 主程序:
  设 艾 为 造网页搜索工具定义({"提供商": "exa", "密钥": "", "执行器": 空执行器})
  打印("EXA=" + 艾["execute"]({"query": "x"})["content"][0]["text"])
  设 彭 为 造网页搜索工具定义({"提供商": "perplexity", "密钥": "", "执行器": 空执行器})
  打印("PPX=" + 彭["execute"]({"query": "x"})["content"][0]["text"])
  设 状态 为 网页工具状态({"提供商": "perplexity", "执行器": 空执行器})
  打印("可用=" + 转字符串(状态["搜索"]["可用"]))
  打印("原因=" + 状态["搜索"]["原因"])
''')
    assert "EXA_API_KEY" in r.stdout, r.output
    assert "PERPLEXITY_API_KEY" in r.stdout, r.output
    assert "可用=False" in r.stdout, r.output
    assert "PERPLEXITY_API_KEY" in [ln for ln in r.stdout.splitlines() if ln.startswith("原因=")][0]


# ------------------------------------------------- 2. 假 provider + limit 截断
def test_假provider归一且受limit约束():
    r = _run('''
从 工具_网页 导入 造网页搜索工具定义

段落 假执行器(请求):
  返回 {"content": [
    {"type": "web_search_tool_result", "content": [
      {"type": "web_search_result", "url": "https://a.example/1", "title": "A1", "page_age": "2026-01-01"},
      {"type": "web_search_result", "url": "https://a.example/2", "title": "A2"},
      {"type": "web_search_result", "url": "https://a.example/3", "title": "A3"},
      {"type": "web_search_result", "url": "https://a.example/4", "title": "A4"},
      {"type": "web_search_result", "url": "https://a.example/5", "title": "A5"}
    ]},
    {"type": "text", "text": "小结", "citations": [
      {"url": "https://a.example/1", "cited_text": "S1"},
      {"url": "https://a.example/2", "cited_text": "S2"},
      {"url": "https://a.example/3", "cited_text": "S3"},
      {"url": "https://a.example/4", "cited_text": "S4"},
      {"url": "https://a.example/5", "cited_text": "S5"}
    ]}
  ]}

段落 主程序:
  设 定义项 为 造网页搜索工具定义({"执行器": 假执行器, "密钥": "sk-test"})
  设 结果 为 定义项["execute"]({"query": "测试", "limit": 2})
  打印("ERR=" + 转字符串(结果["isError"]))
  打印("TXT=" + 结果["content"][0]["text"])
''')
    assert "ERR=False" in r.stdout, r.output
    txt = [ln for ln in r.stdout.splitlines() if ln.startswith("TXT=")][0][4:]
    payload = json.loads(txt)
    assert payload["query"] == "测试"
    assert payload["truncated"] is True
    assert len(payload["sources"]) == 2, txt
    first = payload["sources"][0]
    assert first["url"] == "https://a.example/1"
    assert first["title"] == "A1"
    assert first["snippet"] == "S1"
    assert payload["sources"][1]["url"] == "https://a.example/2"


# --------------------------------------------------------- 3. 四类非法目标拒绝
def test_抓取四类非法目标全部拒绝且不调用抓取器():
    r = _run('''
从 工具_网页 导入 造网页抓取工具定义

设 计数 = {"次": 0}

段落 假抓取(网址):
  设 计数["次"] = 计数["次"] + 1
  返回 {"状态": 200, "内容类型": "text/plain", "体": "不该到这里"}

段落 主程序:
  设 定义项 为 造网页抓取工具定义({"抓取器": 假抓取})
  遍历 网址 之 ["http://127.0.0.1/x", "http://10.0.0.5/x", "file:///etc/passwd", "ftp://x"]:
    设 结果 为 定义项["execute"]({"url": 网址})
    打印("CASE=" + 网址 + "|ERR=" + 转字符串(结果["isError"]) + "|TXT=" + 结果["content"][0]["text"])
  打印("CALLS=" + 转字符串(计数["次"]))
''')
    lines = [ln for ln in r.stdout.splitlines() if ln.startswith("CASE=")]
    assert len(lines) == 4, r.output
    for ln in lines:
        head, rest = ln.split("|ERR=", 1)
        url = head[5:]
        err, txt = rest.split("|TXT=", 1)
        assert err == "True", ln
        assert url in txt, "文案须点名被拒目标：" + txt
        assert "拒绝抓取" in txt, ln
    # 私网/回环：原因必须可读（走 抓取策略 的非公网字面量判定）
    assert "私网" in r.stdout and "SSRF" in r.stdout, r.output
    assert "127.0.0.1" in r.stdout and "10.0.0.5" in r.stdout, r.output
    # 非 http(s)：原因必须点明协议面
    assert "只允许 http(s)" in r.stdout, r.output
    assert "unsupported URL scheme" in r.stdout, r.output
    # 四次拒绝都在外呼之前：抓取器一次都没被调用
    assert "CALLS=0" in r.stdout, r.output


# --------------------------------------------- 4. 超 32KB：截断标志 + 头尾预览
def test_超32KB返回截断标志与头尾预览():
    r = _run('''
从 工具_网页 导入 造网页抓取工具定义

段落 假抓取(网址):
  设 体 为 ""
  设 i 为 0
  当 i < 20000:
    设 体 为 体 + "A"
    设 i 为 i + 1
  设 体 为 体 + "MIDMARK"
  设 j 为 0
  当 j < 20000:
    设 体 为 体 + "B"
    设 j 为 j + 1
  返回 {"状态": 200, "内容类型": "text/plain; charset=utf-8", "体": 体}

段落 主程序:
  设 定义项 为 造网页抓取工具定义({"抓取器": 假抓取})
  设 结果 为 定义项["execute"]({"url": "https://example.com/big"})
  打印("ERR=" + 转字符串(结果["isError"]))
  打印("TXT=" + 结果["content"][0]["text"])
''')
    assert "ERR=False" in r.stdout, r.output
    payload = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("TXT=")][0][4:])
    assert payload["truncated"] is True
    assert payload["bytes"] == 40007
    assert payload["status"] == 200
    assert payload["kind"] == "text"
    text = payload["text"]
    assert "Omitted 7239 bytes" in text, "省略计数应为 40007-32768=7239：" + text[-200:]
    assert "只返回头尾预览" in text
    assert "MIDMARK" not in text, "正文中段必须被省略，不能吐全文"
    assert len(text) < 33000, "预览长度应接近 32KB 而不是全文"


def test_未超32KB原样返回不截断():
    r = _run('''
从 工具_网页 导入 造网页抓取工具定义

段落 假抓取(网址):
  返回 [200, "text/html; charset=utf-8", "<html>你好</html>"]

段落 主程序:
  设 定义项 为 造网页抓取工具定义({"抓取器": 假抓取})
  设 结果 为 定义项["execute"]({"url": "https://example.com/small"})
  打印("TXT=" + 结果["content"][0]["text"])
''')
    payload = json.loads([ln for ln in r.stdout.splitlines() if ln.startswith("TXT=")][0][4:])
    assert payload["truncated"] is False
    assert payload["text"] == "<html>你好</html>"
    assert payload["kind"] == "html"


# ----------------------------------------------- 5. 定义形状与名字
def test_两个工具定义形状合法且名字对齐DSH():
    r = _run('''
从 工具_网页 导入 造网页搜索工具定义, 造网页抓取工具定义
从 工具 导入 校验工具定义形状

段落 空执行器(请求):
  返回 {}

段落 假抓取(网址):
  返回 {"状态": 200, "内容类型": "text/plain", "体": "ok"}

段落 主程序:
  设 搜 为 造网页搜索工具定义({"执行器": 空执行器, "密钥": "sk-test"})
  设 取 为 造网页抓取工具定义({"抓取器": 假抓取})
  打印("SNAME=" + 搜["name"])
  打印("FNAME=" + 取["name"])
  打印("SSHAPE=" + 序列化JSON(校验工具定义形状(搜)))
  打印("FSHAPE=" + 序列化JSON(校验工具定义形状(取)))
  打印("SREQ=" + 序列化JSON(搜["parameters"]["required"]))
  打印("FREQ=" + 序列化JSON(取["parameters"]["required"]))
  打印("SPROPS=" + 序列化JSON(搜["parameters"]["properties"]))
''')
    assert "SNAME=web_search" in r.stdout, r.output
    assert "FNAME=web_fetch" in r.stdout, r.output
    assert "SSHAPE=[]" in r.stdout, r.output
    assert "FSHAPE=[]" in r.stdout, r.output
    assert 'SREQ=["query"]' in r.stdout, r.output
    assert 'FREQ=["url"]' in r.stdout, r.output
    # limit 是可选参数（snake_case 对齐上游），不在 required 里
    assert '"limit"' in r.stdout, r.output


# --------------------------------------------------------- 6. 反跑 A 锚点
def test_反跑锚点_私网拒绝行仍在源码():
    """删掉这一行 → 用例 3 的私网两类必须立红；本锚点断言同步变红。"""
    text = SRC.read_text(encoding="utf-8")
    assert "主机是否非公网字面量(主机) == 真" in text, "私网拒绝行（反跑 A 锚点）被删掉了"
    assert "反跑 A 变异锚点" in text, "反跑 A 锚点注释缺失"


def test_只走抓取策略不写第二套判定():
    """私网判定必须复用 抓取策略，而不是在接线层自建 IP 解析。"""
    text = SRC.read_text(encoding="utf-8")
    assert "从 抓取策略 导入" in text
    assert "校验抓取地址" in text and "主机是否非公网字面量" in text

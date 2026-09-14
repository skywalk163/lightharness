# -*- coding: utf-8 -*-
"""test_R20_词法边界.py —— 第20轮 任务4：词法分析器边界 token 切分验证（pytest 级）

用 light-merge 词法 API 直接验证（examples/test_R20_词法边界综合.light 是运行期自校验，
本文件是编译期 token 层验证，两层互补）：
  1) 关键字前缀标识符：定义登记后（模拟真实文件：段落定义+使用同源码）整名保持 IDENTIFIER；
  2) 合法关键字语句：如果/否则/否则若/遍历/当/尝试/捕获/最终/设...为 真|假|空 的关键字 token 形态；
  3) `设 X为 <值起始>` 赋值尾巴（如 设 合并为 {}）：第19轮 EMBED 为-词尾合并的回归面，
     第20轮任务1 已修复 → 本文件断言 `为` 交还 KEYWORD（见 test_assign_tail_keyword_split）；
  4) 第20轮回归守卫：函数调用语境（整串后紧随 '('）绝不切分，守护 `断言为真(...)` 家族
     （见 test_call_context_never_split / test_midfix_regression_guard_for_six_cases）；
  5) 运算符动词函数调用语境（见 test_operator_verb_call_context）。
"""
import os
import sys

import pytest

LIGHT_MERGE = os.environ.get("LIGHT_MERGE", r"G:\dswork\duan-light-merge\light-merge")
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))

from lexer import Lexer  # noqa: E402

LEXER = Lexer()

NAMES = [
    "去重占位", "作用域匹配", "排序函数", "遍历器", "筛选器", "求和函数", "求最大值", "读取器",
    "输出流", "调试器", "跳过标记", "继续标记", "等待器", "推迟执行", "映射表", "加载器",
    "关闭标记", "开启标记", "保护器", "使用者", "定义表", "实现类", "继承链", "抽象类",
    "最终值", "构造器", "枚举值", "类型表", "模块名", "函数表", "段落名", "情况表",
    "那么分支", "否则分支", "如果条件", "当循环", "尝试块", "捕获块", "抛出异常", "打印函数",
    "新建对象", "返回值", "设值器", "等于判断", "不等于判断", "大于判断", "小于判断", "加上操作",
    "减去操作", "乘以操作", "除以操作", "外部函数",
    "否则若分支", "退出循环标记", "静态方法表", "类型别名表", "标准库函数表",
]

LEGAL_SNIPPETS = [
    "如果 条件:",
    "否则:",
    "否则若 条件:",
    "遍历 键 之 列表:",
    "当 条件:",
    "尝试:",
    "捕获 异常 为 甲:",
    "最终:",
    "设 甲 为 真",
    "设 甲 为 假",
    "设 甲 为 空",
    "返回 真",
    "返回 假",
    "抛出 新建 错误(\"探测\")",
]

ASSIGN_TAIL_BROKEN = [
    # (源码, 被并坏的整体名) —— 第20轮任务1 修复后应改为断言正确切分
    ("设 合并为 {}", "合并为"),
    ("设 监听域为 {}", "监听域为"),
]


@pytest.mark.parametrize("name", NAMES)
def test_keyword_prefix_identifier_keeps_whole(name):
    """定义登记后（段落定义+使用同源码），关键字前缀名应整体成 IDENTIFIER。"""
    src = ("段落 %s 接收:\n" % name
           + "    返回 %s()\n" % name)
    toks = LEXER.tokenize(src)
    ids = [t.value for t in toks if t.type.name == "IDENTIFIER"]
    assert name in ids, "关键字前缀名 %s 未整体成 IDENTIFIER（切分=%r）" % (
        name, [(t.type.name, t.value) for t in toks])


@pytest.mark.parametrize("snippet", LEGAL_SNIPPETS)
def test_legal_keyword_statements(snippet):
    """合法关键字语句的关键字必须保持 KEYWORD token（不被并入标识符）。"""
    head = snippet.split()[0].rstrip(":")
    toks = LEXER.tokenize(snippet)
    kw_or_id = [(t.type.name, t.value) for t in toks]
    if head in ("如果", "否则", "否则若", "遍历", "当", "尝试", "捕获", "最终", "设", "返回", "抛出"):
        assert ("KEYWORD", head) in kw_or_id, "语句头 %s 未识别为 KEYWORD（%r）" % (head, kw_or_id)


def test_han_identifier_no_embed_split():
    """第19轮修复回归保护：末位行为/错误己/配下标 等形态的 token 形态。"""
    cases = [
        ("设 末位行为 为 1", "IDENTIFIER", "末位行为"),
        ("捕获 异常 错误己:", "IDENTIFIER", "错误己"),
        ("打印 配[0]", "IDENTIFIER", "配"),      # L-119 下标访问
    ]
    for src, ttype, value in cases:
        toks = LEXER.tokenize(src)
        pair = (ttype, value)
        assert pair in [(t.type.name, t.value) for t in toks], \
            "%r 缺少 %r（实际 %r）" % (src, pair, [(t.type.name, t.value) for t in toks])


def _tok(src):
    return [(t.type.name, t.value) for t in LEXER.tokenize(src)]


def test_assign_tail_keyword_split():
    """第20轮任务1 修复翻转点（原 skip 测试的断言已翻转）：
    `设 X为 <值起始>` 的 `为` 必须交还 KEYWORD（前缀独立成 IDENTIFIER）。
    修复前：ID(合并为) / ID(监听域为) → 解析报「期望'为'或'等于'，但得到 {」。
    """
    cases = [
        ("设 合并为 {}", "合并", "为"),
        ("设 监听域为 {}", "监听域", "为"),
        ("设 甲为空", "甲", "为"),          # 情形 (a)：紧邻值字面量尾巴
        ("设 甲为真", "甲", "为"),
        ("设 甲为假", "甲", "为"),
    ]
    for src, prefix, kw in cases:
        toks = _tok(src)
        assert ("IDENTIFIER", prefix) in toks and ("KEYWORD", kw) in toks, \
            "%r 未把 %r 切回关键字（实际 %r）" % (src, kw, toks)


def test_call_context_never_split():
    """第20轮回归守卫（6 用例：test_代理策略/启动环境/大模型回放/文件深/时间上下文/联调CLI）：
    「整串后紧随 '('」= 函数调用语境 → 含 为/返回/尝试 的函数名必须整体成 IDENTIFIER，绝不切分。
    修复前：`断言为真(…)` 被切成 `断言为` + `真` → 「真 是保留关键字，不能直接作为语句开头」。
    """
    names = ["断言为真", "判定为空", "断言为假", "合并为", "头版本为",
             "内层返回", "结算被终止尝试", "断言为真值"]
    for name in names:
        src = "段落 %s 接收 参数甲:\n    返回 参数甲\n" % name
        toks = _tok(src)
        ids = [v for t, v in toks if t == "IDENTIFIER"]
        assert name in ids, "%s 应整体成 IDENTIFIER（实际 %r）" % (name, toks)
    # 直接验证调用点：首个 token 即完整函数名
    for name in ["断言为真", "判定为空"]:
        toks = _tok("%s(1)" % name)
        assert toks[0] == ("IDENTIFIER", name), \
            "%s(...) 调用点首 token 应为完整函数名（实际 %r）" % (name, toks)


def test_midfix_regression_guard_for_six_cases():
    """上述 6 个回归用例的真实调用形态（`断言为真(...)` 作语句头）必须解析通过。"""
    src = ('段落 主:\n'
           '    断言为真(判定为空(1), "标签")\n'
           '段落 断言为真 接收 条件, 标签:\n'
           '    返回 条件\n'
           '段落 判定为空 接收 值:\n'
           '    返回 值 == 空\n')
    toks = _tok(src)
    assert ("IDENTIFIER", "断言为真") in toks
    assert ("IDENTIFIER", "判定为空") in toks


def test_operator_verb_call_context():
    """第20轮修复点A：运算符动词嵌于纯 CJK 长串且整串后紧随 '(' → 整体成标识符。"""
    toks = _tok("删除属性(子, \"共享\")")
    assert toks[0] == ("IDENTIFIER", "删除属性"), "删除属性(...) 应整体成词（实际 %r）" % toks
    # 反向：中缀 `甲加乙`（后无括号）仍按运算符切分
    toks = _tok("甲加乙")
    assert toks == [("IDENTIFIER", "甲"), ("KEYWORD", "加"), ("IDENTIFIER", "乙"), ("EOF", None)], \
        "甲加乙 应保持中缀切分（实际 %r）" % toks


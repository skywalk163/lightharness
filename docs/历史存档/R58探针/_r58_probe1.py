# -*- coding: utf-8 -*-
"""R58 任务1 探针：16 条词法红的 token 流与保护表成员实测。只读。"""
import io, os, sys

ROOT = r"G:\dswork\duan-light-merge\light-merge"
sys.path.insert(0, os.path.join(ROOT, "src"))

import lexer as L
from lexer import Lexer

out = []


def dump(src):
    try:
        toks = Lexer(src).tokenize()
        v = [(t.type.name, t.value) for t in toks if t.type.name != 'EOF']
    except Exception as e:
        v = "EXC %s: %s" % (type(e).__name__, e)
    out.append("  %-34r -> %s" % (src, v))


out.append("=== 表规模 ===")
for n in ("COMMON_COMPOUND_WORDS", "_COMPOUND_SAFE_SINGLE_KEYWORDS", "_EMBED_MAX_MATCH_KEYWORDS",
          "_VALUE_LITERAL_KEYWORDS", "_AWAIT_KEYWORDS"):
    val = getattr(L, n, "<missing>")
    out.append("  %-38s len=%s" % (n, len(val) if hasattr(val, '__len__') else val))
for n in ("_P0A_HEAD_MERGE_SINGLE", "_P0A_HEAD_MERGE_DUAL", "_R27_BCLASS",
          "_P0A_TAIL_CUT_SINGLE", "_P0A_HEAD_SPLIT_SINGLE", "_R26_STMT_HEAD_SINGLE"):
    val = getattr(L, n, "<missing>")
    out.append("  %-38s = %s" % (n, sorted(val) if hasattr(val, '__iter__') else val))
out.append("  Lexer._P0A_MERGE_WHOLE = %s" % sorted(Lexer._P0A_MERGE_WHOLE))
out.append("  Lexer._TRAILING_ALIAS_CLASS = %s" % sorted(Lexer._TRAILING_ALIAS_CLASS))
out.append("  Lexer._P0A_OP = %s" % sorted(Lexer._P0A_OP))
out.append("  Lexer._P0A_SUFFIX_SPLIT_SINGLE = %s" % sorted(Lexer._P0A_SUFFIX_SPLIT_SINGLE))
out.append("  Lexer._P0A_NEVER_SPLIT = %s" % sorted(Lexer._P0A_NEVER_SPLIT))

out.append("")
out.append("=== 目标 9 单字 成员矩阵 ===")
CS = L._COMPOUND_SAFE_SINGLE_KEYWORDS
HM = L._P0A_HEAD_MERGE_SINGLE
DUAL = L._P0A_HEAD_MERGE_DUAL
F = set(Lexer._TRAILING_ALIAS_CLASS)
AWAIT = L._AWAIT_KEYWORDS
for ch in "除匹异常等断跃现引":
    out.append("  %s: CS=%s HM=%s DUAL=%s F=%s AWAIT=%s ALL_KW=%s 1char_kw=%s" % (
        ch, ch in CS, ch in HM, ch in DUAL, ch in F, ch in AWAIT,
        ch in L.ALL_KEYWORDS, ch in L._ALL_KEYWORDS_WITH_VERBS))

out.append("")
out.append("=== token 流实测 ===")
for s in ("设甲为三。", "三加五", "九十那么大", "三加",
          "导出事件表", "整理模型消息", "返回码", "退出码", "接收参数", "非空块",
          "外部命令", "排序依据", "输出块表",
          "捕 除类型错误：\n    印 1。\n", "设 匹配度 为 1",
          "设 甲 为 1。\n打印 甲加5。"):
    dump(s)

io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_r58_probe1.txt"),
        "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))

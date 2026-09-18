# -*- coding: utf-8 -*-
"""R58 探针2：p0a 压力词在真实语境下是否被通用规则覆盖；数字前缀边界。只读。"""
import io, os, sys

ROOT = r"G:\dswork\duan-light-merge\light-merge"
sys.path.insert(0, os.path.join(ROOT, "src"))
from lexer import Lexer

out = []


def sig(src):
    try:
        return [(t.type.name, t.value) for t in Lexer(src).tokenize()
                if t.type.name not in ('EOF', 'NEWLINE', 'INDENT', 'DEDENT')]
    except Exception as e:
        return "EXC %s: %s" % (type(e).__name__, e)


def show(src):
    out.append("  %-30r -> %s" % (src, sig(src)))


out.append("=== p0a 压力词：裸串 vs 真实语境 ===")
for w in ('导出事件表', '整理模型消息', '返回码', '退出码', '接收参数', '非空块',
          '外部命令', '排序依据', '输出块表'):
    show(w)
out.append("  --- 语境 ---")
for s in ('设 甲 为 导出事件表', '导出事件表 为 1', '接收参数(甲)', '外部命令(甲)',
          '甲.返回码', '返回码 为 1', '整理模型消息(甲)', '非空块 为 真',
          '记录类型', '记录类型 为 1'):
    show(s)

out.append("")
out.append("=== 数字前缀边界 ===")
for s in ('那么大', '那么', '大', '九十那么大', '九十那么', '三加五', '三加',
          '三乘五', '三减五', '三除五', '三模五', '三到五', '三真五', '三空五',
          '零除错误', '百分位数', '二元运算符表等于甲', '三加五等于八'):
    show(s)

out.append("")
out.append("=== L-174 相关 ===")
for s in ('设甲为三。', '设甲为三', '甲为三', '为三', '甲为', '设甲', '设甲为',
          '设 甲为三', '设 甲 为 三', '甲为真', '甲为空', '甲为1', '甲为[1]'):
    show(s)

out.append("")
out.append("=== 除/位/应 前缀类 ===")
for s in ('捕 除类型错误：', '除非', '除非 甲：', '位与', '应当', '除类型错误',
          '除 类型错误', '捕获 除类型错误：'):
    show(s)

io.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_r58_probe2.txt"),
        "w", encoding="utf-8").write("\n".join(out))
print("\n".join(out))

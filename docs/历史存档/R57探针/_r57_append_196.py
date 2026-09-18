# -*- coding: utf-8 -*-
"""R57 任务5：对标清单追加 #196（先无损往返自证，再插入，保 CRLF + 无尾换行）"""
import json, sys
from pathlib import Path

F = Path(r"G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json")

raw = F.read_bytes().decode("utf-8")

# ---- 1. 无损往返自证 ----
data = json.loads(raw)
canonical = json.dumps(data, ensure_ascii=False, indent=1).replace("\n", "\r\n")
print("[自证] 规范序列化 == 原始文本:", canonical == raw)
if canonical != raw:
    # 定位第一处差异
    for i, (a, b) in enumerate(zip(canonical, raw)):
        if a != b:
            print("  首处差异 @%d: 规范=%r 原始=%r" % (i, a, b))
            print("  规范上下文:", canonical[max(0, i - 60):i + 60])
            print("  原始上下文:", raw[max(0, i - 60):i + 60])
            break
    sys.exit(1)

# ---- 2. 构造 #196 ----
new_item = {
    "编号": 196,
    "功能": "词法器通用缺陷修复（L-173）+ flaky/墙钟性能断言处置 + 复现用例入全量门（G7）+ gate_remote 透传 --py（G8）+ 101 存量红分类画像",
    "原模块": "light-merge 词法器与 tests 层（R56 遗留：4 例 example 红、flaky 抖动、性能断言假红、复现用例只在 examples/ 不进全量门）",
    "光明模块": "light-merge/src/lexer.py（L-173 预扫描修复）+ tests/test_distributed_eval_light.py（flaky）+ tests/unit/test_lexer_perf.py（性能阈值）+ light-merge/tests/test_R57_L170回归.py + lightharness/tests/test_R57_复现回归.py + lightharness/scripts/多平台矩阵.py（--py 透传）",
    "状态": "已完成",
    "完成轮次": "第57轮",
    "备注": "任务1/2/3/4/5+路M 合并交付。①L-173 已修：预扫描 _scan_user_definitions 把名字内关键字当分隔符→名字截断注册（段落分支无空格回退只认「接收」+ 设分支 collected_something 守卫，2 hunk 最小 diff）。全语料 38084 个 .light A/B token 对拍**只有 4 个目标文件变化**；0.82 py3.12 4 例 example rc=0；互举反跑 677 文件 0 新增（并修复基线内 2 条）；test_回归 -k R22/R26/R27 9 failed→9 passed。②L-174 登记未修（设甲为三 属嵌入块分支，修需把中文数字加入 _emb_value_heads 会扩大语义面）。③flaky：方案 A + 决定性杠杆（本用例心跳窗口 0.5s/间隔 0.05s），0.82 实测 30%→0/10；根因实测：监控循环完成条件先成立即跳出、失联来不及标，kill→报告 1.01~1.53s 压 1.5s 窗口。④性能断言：LEXER_PERF_LIMIT 2.0→10.0（并行实测 3.6s 留 2.8× 余量，仍拦 O(n²)）。⑤G7 闭环：复现用例挂进 tests/（test_R57_复现回归.py 11 例 + test_R57_L170回归.py 1 例），进全量门收集；修复前（旧 lexer）红、修复后绿，判别力实证。⑥G8：gate_remote 透传 --py（默认仍 3.12）。⑦任务4 画像：真基线 100 红 = 12 类（语义债 21+14+12+5+3、缺依赖环境红 18=cryptography4+requests6+lunardate8、词法层 8+8、解析层 7、异步 5、文档 2、性能 1、examples 聚合 1）。⑧【第57轮更正】#195 所述「R54 引入 16 条新红（NameError: name '错误' is not defined）」**经复核不成立**：该 16 条只在 6 份基线中 5 轮红、最终真基线 072454 该文件 0 红；0.82 当前副本定向跑 tests/test_stdlib_phase9.py **57 passed**（独立复核）；错误 ∉ VERB_ARITY/STDLIB/ALL_VERB 而 R54 两处改动全以 VERB_ARITY 为键→结构上碰不到；判为当时副本局部状态，parser_stmt.py 本轮未改。⑨路M：**全程仅 1 次 0.82 全量**（用户指示：不并行全量、尽量少全量、全量只走 0.82 py3.12），fast 与 072454 同口径对拍新增红=0。",
    "证据": [
        "light-merge/_task1_R57_解析链修复.md",
        "lightharness/_task2_R57_tests修复.md",
        "lightharness/_task3_R57_复现用例入tests.md",
        "lightharness/_task4_R57_存量红画像.md",
        "lightharness/_task5_R57_docs+移档.md",
        "lightharness/reports/_task4_R57_存量红明细_072454.json",
        "lightharness/reports/082_lightmerge基线_2026-09-18-072454.json",
        "lightharness/tests/test_R57_复现回归.py",
        "light-merge/tests/test_R57_L170回归.py",
        "light-merge/src/lexer.py",
        "lightharness/docs/历史存档/R57探针/"
    ],
}

# ---- 3. 插入（最后一个条目的 `  }` 之前加逗号 + 新条目）----
assert raw.rstrip("\r\n").endswith("}")
# 找最后一个 `  }\n ]\n}` 结构
tail_marker = "  }\r\n ]\r\n}"
idx = raw.rfind(tail_marker)
if idx == -1:
    tail_marker = "  }\n ]\n}"
    idx = raw.rfind(tail_marker)
if idx == -1:
    print("[失败] 找不到尾部结构标记")
    sys.exit(1)
print("[插入] 尾部结构 @%d" % idx)

item_json = json.dumps(new_item, ensure_ascii=False, indent=1).replace("\n", "\r\n")
# dumps(indent=1) 顶层没有缩进，插入处需要整体缩进 1 空格（对标清单条目在数组内缩进 1）
item_json_indented = "\r\n".join(" " + line if line else line for line in item_json.split("\r\n"))
# 去掉 item 自身的首尾大括号行缩进处理：第一个 { 前无缩进、最后 } 后跟行
new_text = raw[:idx] + "  },\r\n" + item_json_indented + "\r\n" + raw[idx + len("  }"):]
# 注意：item_json 以 { 开头 } 结尾；上方拼接 raw[:idx] 保留到上一个 `  }`（不含换行），加 `,\r\n` 再放新条目
# 然后接 raw[idx + len("  }"):]（即 `\r\n ]\r\n}`）

# ---- 4. 写回（UTF-8 无 BOM + CRLF + 无尾换行）----
assert not new_text.endswith("\n"), "不应有尾换行"
F.write_bytes(new_text.encode("utf-8"))
print("[写回] 完成，大小 %d 字节" % F.stat().st_size)

# ---- 5. 回读验证 ----
data2 = json.loads(F.read_bytes().decode("utf-8"))
print("[回读] 条目数: %d (原 %d) ｜ 196 存在: %s" % (len(data2["对标"]), len(data["对标"]), any(x.get("编号") == 196 for x in data2["对标"])))

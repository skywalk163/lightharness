# -*- coding: utf-8 -*-
"""R58 任务3 —— 归因明细 JSON+CSV 构建脚本（合并 A/B/C 三组，35 条）"""
import json, csv, os
from collections import Counter

BASE = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE, "docs/历史存档/R58探针/_r58_task3_A.json"), encoding="utf-8") as f:
    A = json.load(f)
assert len(A["items"]) == 13, len(A["items"])

L175 = "无关（已用 R57 终跑 100010 junitxml 交叉核对：35 条 message 与 072454 基线实质一致——31 条全同、4 条仅空白差异，未变化）"
COMMON_CG = ("粘连 self 前缀「己X」只在语句位被展开：parser_stmt.py:959 _parse_self_assignment → SelfAssignment → "
             "code_generator.py:2531-2535 发射 self.X = …（本机复现：赋值位正确）。而表达式/实参位置的「己X」经 lexer "
             "整词成单个 IDENTIFIER（实测 tokenize('列表追加(己项, 值)') → IDENTIFIER '己项'），读取位无任何一层展开："
             "unified code_generator_unified.py:586-611 _resolve_name 只匹配裸 己/自 与 己./自. 前缀，且该后端无类属性回退分支；"
             "src 后端 code_generator.py:4342-4359 的类属性分支（:4356）按整名 raw_name in _class_attr_names 匹配，"
             "『己名称』不在（表里是『名称』）同样落空 → 发射裸名 → 运行期 NameError。读写两侧不对称是直接根因。")

def why_of(size):
    return {"小": "只改测试断言/期望文本，不动编译器源码",
            "中": "需动两个 codegen 后端的 _resolve_* 并互举反跑，防误伤『己方/自己』类普通标识符",
            "大": "涉及语义设计变更"}[size]

def item(id, cat, hong, gen, kind, fix, size):
    return {"id": id, "category": cat, "红因": hong, "根因": gen, "根因类别": kind,
            "修复建议": fix, "改动面": size, "改动面理由": why_of(size), "与L-175相关性": L175}

BID = "tests/test_context_manager.py::"
B = {"group": "B_context_manager", "items": [
    item(BID+"TestL2OOPCodegen::test_自_param_and_body_both_self", "语义债-代码生成断言",
         "断言 'self.姓名 = 姓名' in 产物；实测发射 _light_attr_set(self, '姓名', 姓名)（本机复现）",
         "手工 AST 的 Assignment(MemberAccess(自,姓名),…) 走 L-096 属性赋值发射（code_generator.py:1684-1693）；"
         "helper 定义处注释（:1329-1344）说明 dict→键访问、类实例→setattr 是有意设计，运行期语义等价。期望停留在旧直发文本。",
         "测试期望过时", "改断言为 _light_attr_set 形态，或改行为断言（exec 后实例属性正确）", "小"),
    item(BID+"TestAwaitMemberAccess::test_await_chained_member", "语义债-代码生成断言",
         "断言 'await 甲.乙.丙()' in 产物；实测 'await _light_attr_get(甲, '乙').丙()'（本机复现）",
         "await 链式成员的属性读取走 L-096 helper（code_generator.py:3819-3822），方法调用 .丙() 仍直发（:3806）。"
         "getattr(甲,'乙').丙() ≡ 甲.乙.丙()，语义等价，断言文本过时。",
         "测试期望过时", "改断言接受 _light_attr_get 形态或行为断言", "小"),
    item(BID+"TestJueyiE遍历为连接词::test_为搭配函数调用", "语义债-代码生成断言",
         "断言 '==' not in 产物 失败；实测 for i in range(1, 10): 发射正确，'==' 来自产物头部运行时预置"
         "（内置 lambda 表，如『是负零』: isinstance(v, float) and v == 0.0 …，本机定位到具体行）",
         "『为 被吞成 ==』的防线本体没坏，是全产物子串断言过宽：内置预置随版本增长（含合法 ==），子串断言失控。",
         "测试期望过时", "断言收窄到循环行（或检查产物不含 'in range(1, 10) =='），不动 codegen", "小"),
    item(BID+"TestJueyiOOP成员赋值目标::test_自之属性赋值", "语义债-代码生成断言",
         "断言 'self.姓名 = 姓名' in 产物；实测 _light_attr_set(self, '姓名', 姓名)",
         "带点/之 形态的赋值目标走 L-096 发射（code_generator.py:1684-1693），setattr 语义等价。断言过时。",
         "测试期望过时", "改断言为 helper 形态或行为断言", "小"),
    item(BID+"TestJueyiOOP成员赋值目标::test_自之属性带索引赋值", "语义债-代码生成断言",
         "断言 'self.成绩[科目] = 分数' in 产物；实测 _light_attr_get(self,'成绩')[科目] = 分数",
         "L-096 读取 helper + 原生下标赋值，运行期等价。断言过时。",
         "测试期望过时", "改断言为 helper 形态或行为断言", "小"),
    item(BID+"TestJueyiOOP成员赋值目标::test_普通标识符之成员赋值", "语义债-代码生成断言",
         "断言 'obj.字段 = 1' in 产物；实测 _light_attr_set(obj, '字段', 1)",
         "L-096 属性赋值统一发射（code_generator.py:1684-1693），语义等价。断言过时。",
         "测试期望过时", "改断言为 helper 形态或行为断言", "小"),
    item(BID+"TestJueyiOOP成员赋值目标::test_点号成员赋值未被破坏", "语义债-代码生成断言",
         "断言 'obj.字段 = 1' in 产物；实测 _light_attr_set(obj, '字段', 1)",
         "同上：L-096 形态，『未被破坏』由 setattr 保证。断言过时。",
         "测试期望过时", "改断言为 helper 形态或行为断言", "小"),
    item(BID+"TestL0SingleCharClassKeywords::test_继承链可用", "语义债-类/成员访问",
         "运行期 NameError: name '己名称' is not defined（exec 生成代码时；源码 返 己名称）",
         COMMON_CG, "codegen缺陷",
         "在 _resolve_identifier_name（src 后端 :4342）与 _resolve_name（unified :586）同加：类方法内 name 以 己/自 开头"
         "且剩余部分 ∈ _class_attr_names → self.剩余；改后互举反跑 + 定向验证", "中"),
    item(BID+"TestChaoSuper::test_chao_dot_plain_method", "语义债-类/成员访问",
         "运行期 NameError: name '己名称' is not defined（exec 时，源码 返 己名称）",
         COMMON_CG, "codegen缺陷", "同 test_继承链可用（一条修复同时转绿）", "中"),
    item(BID+"TestChaoSuper::test_chao_zhi_form", "语义债-类/成员访问",
         "运行期 NameError: name '己名称' is not defined（超 之 形态，同源）",
         COMMON_CG + "（超 之 构/描述 与 父 同路，红因与超 无关，仍是 粘连 己名称 读取位不展开）",
         "codegen缺陷", "同 test_继承链可用", "中"),
    item(BID+"TestChaoSuper::test_chao_de_form", "语义债-类/成员访问",
         "运行期 NameError: name '己名称' is not defined（超 的 形态，同源）",
         COMMON_CG + "（超 的 形态同理）", "codegen缺陷", "同 test_继承链可用", "中"),
]}

C = {"group": "C_runtime_class_member", "items": []}
def addC(id, hong, extra=""):
    C["items"].append(item(id, "语义债-类/成员访问", hong,
        COMMON_CG + extra, "codegen缺陷", "同 test_继承链可用（一条修复同时转绿）", "中"))
addC("tests/test_frontend_blockers_run.py::test_a24_泛型类真跑",
     "[run] 退出码 1: [运行错误] name '己项' is not defined（本机 AST 复现：构造里 己项 为 列表创建() → self.项 正确；列表追加(己项, 值) 实参位发射裸 己项）")
addC("tests/test_frontend_blockers_run.py::test_a24_多参数泛型类", "[run] 退出码 1: name '己左' is not defined（返回 己左 读取位）")
addC("tests/test_frontend_blockers_run.py::test_a25_两个嵌套类且外层成员不被吞", "[run] 退出码 1: name '己号' is not defined（返回 己号 读取位）")
addC("tests/integration/test_class_system.py::TestClassInheritance::test_constructor_with_inheritance", "NameError: name '己名字' is not defined")
addC("tests/integration/test_class_system.py::TestClassBasic::test_class_with_attributes", "NameError: name '己姓名' is not defined（打印 己姓名 读取位）")
addC("tests/integration/test_class_system.py::TestMethodOverride::test_method_override", "NameError: name '己半径' is not defined（己半径 乘 己半径 表达式位）")
addC("tests/integration/test_class_system.py::TestClassAdvanced::test_self_method_call", "NameError: name '己值' is not defined")
addC("tests/integration/test_class_system.py::TestMultipleClasses::test_multiple_classes_in_one_file", "NameError: name '己品牌' is not defined")
addC("tests/test_level6_types.py::TestTypeScenarioClass::test_class_instantiation", "NameError: name '己当前' is not defined")
addC("tests/test_edge_cases.py::TestEdgeCasesClasses::test_class_with_multiple_methods", "RuntimeError: 执行错误: name '己初始值' is not defined（message 内附完整生成代码可复核）")
C["items"].append(item("tests/test_async_class_method.py::TestAsyncClassMethod::test_03_async_method读写己属性", "语义债-代码生成断言",
    "断言 'self.值 = (self.值 + 1)' in 产物；实测 _light_attr_set(self, '值', (self.值 + 1))；读取侧 return self.值 已正确（本机复现）",
    "带点 己.值 读写正常，仅写入语句走 L-096 helper 形态。断言文本过时，exec+asyncio 行为本身可过。",
    "测试期望过时", "改断言为 helper 形态（exec 行为断言保留）", "小"))

summary = {
    "总条数": 35,
    "测试期望过时": 21,
    "codegen缺陷-粘连己X读取不展开": 14,
    "需语义评审": 0, "待验证": 0,
    "R59修复路径": "① 21 条改测试断言（小）；② 14 条共用同一 codegen 修复：类方法内粘连 己X/自X 读取位展开"
                "（src+unified 两后端 _resolve_* 同步加分支，按类属性表/就近绑定防误伤），改后互举反跑+0.82 定向验证",
    "L-175交叉核对": "35 条在 100010 与 072454 中 message 实质一致（31 全同、4 仅空白差异），与 L-175 无关",
}
out = {"meta": "R58 任务3 归因明细（A/B/C 合并；A 组来自 _r58_task3_A.json，已随探针移档 docs/历史存档/R58探针/）",
       "汇总": summary, "groups": {"A": A, "B": B, "C": C}}
with open(os.path.join(BASE, "_task3_R58_代码生成语义债归因明细.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

rows = []
for gname, g in (("A", A), ("B", B), ("C", C)):
    for it in g["items"]:
        rows.append({"id": it["id"], "category": it["category"], "红因": it["红因"], "根因": it["根因"],
                     "根因类别": it["根因类别"], "修复建议": it["修复建议"], "改动面": it["改动面"],
                     "改动面理由": it.get("改动面理由", ""), "与L-175相关性": it["与L-175相关性"], "组": gname})
with open(os.path.join(BASE, "_task3_R58_代码生成语义债归因明细.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    w.writeheader(); w.writerows(rows)
print("items:", len(rows), Counter(r["根因类别"] for r in rows))

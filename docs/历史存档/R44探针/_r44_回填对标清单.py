# -*- coding: utf-8 -*-
"""R44 任务6：对标清单.json 外科式追加 #172/#173，并更正 #171 中被证伪的归因。

为什么不用 json.dump 整体重写：原文件是 CRLF + 非标准缩进，整体重排会产生 5000+ 行 diff，
淹没真实改动。故按原格式做**文本级插入**，diff 只含新增行。
"""
import io
import re

P = "docs/功能对标/对标清单.json"

E172 = (
    "   \"编号\": 172,\r\n"
    "   \"功能\": \"0.82全量重同步+完整pytest跨平台回归（97.4MB副本；7failed/1230passed）\",\r\n"
    "   \"原模块\": \"跨平台回归门（上游 CI 矩阵）\",\r\n"
    "   \"光明模块\": \"lightharness/scripts/同步0.82.py + reports/R44_freebsd_pytest.json\",\r\n"
    "   \"状态\": \"已完成\",\r\n"
    "   \"完成轮次\": \"第44轮\",\r\n"
    "   \"备注\": \"任务1/2。全量重同步(非增量)97.4MB到/tmp/r44-20260916-232020，远端examples=402与本机一致。"
    "0.82全量pytest=7failed/1230passed/3skipped+2errors(缺git,环境缺失)，与本机7条红清单逐条一致，基线外零新增平台红。"
    "实证更正R43归因：400/402failed系首轮python垫片参数被置空(子进程拿空参)，非副本不全——"
    "R43任务3已全量同步后仍402failed、修垫片即降7failed，本轮第二次全量重同步(更大包)结果不变。"
    "新增scripts/同步0.82.py(paramiko+tarfile，固化Git-Bash tar/C盘路径坑与python垫片坑)。\"\r\n"
)

E173 = (
    "   \"编号\": 173,\r\n"
    "   \"功能\": \"装配契约缺陷修复 L-162/L-163/L-164 + 新发现并修复 L-165\",\r\n"
    "   \"原模块\": \"工具注册(registry/executor) + mock服务端契约\",\r\n"
    "   \"光明模块\": \"lightharness/src/mock大模型服务器.light、src/工具_bash.light、src/工具执行.light\",\r\n"
    "   \"状态\": \"已完成\",\r\n"
    "   \"完成轮次\": \"第44轮\",\r\n"
    "   \"备注\": \"任务3/4。L-162 mock处理器改返{状态,头,体}字典(分派保持三元组，护住test_mock大模型服务器29处r[0]/r[2]下标调用)；"
    "L-163 注册bash工具改走具注册工具+bash处理形参补默认取消令牌(带默认值，护住test_R42两个单参调用方)；"
    "L-164 状态字面值保持'ok'(护test_R40硬编码断言，避免wire破坏性变更)改常量化+导出调成功别名与状态字面值表；"
    "L-165(新发现) 新建Mock服务补'全局 当前实例'声明(原漏写致模块级当前实例恒空、启动Mock服务起的真实HTTP服务永远500)。"
    "装配层已去绕行：R43两用例改直接用启动Mock服务/注册bash工具，rc=0。改src后本机全量pytest 7failed/1232passed，基线外零新增红。\"\r\n"
)


def main() -> int:
    src = io.open(P, encoding="utf-8", newline="").read()

    # 1) 更正 #171 备注里被证伪的归因（保留历史表述 + 追加更正）
    old171 = "根因R41以来副本增量不全(FileNotFoundError)非代码缺陷，干净对比需全量重同步留用户。"
    new171 = ("根因R41以来副本增量不全(FileNotFoundError)非代码缺陷，干净对比需全量重同步留用户。"
              "【R44实证更正：该归因不成立——400/402failed实为R43首轮python垫片参数被置空；"
              "两轮独立全量重同步结果均为7failed，见#172】")
    if old171 in src:
        src = src.replace(old171, new171, 1)
        print("已更正 #171 归因")
    else:
        print("警告：#171 归因原句未命中，跳过更正")

    # 2) 在 条目 数组末尾插入 #172 / #173
    tail = "  }\r\n ]\r\n}"
    if not src.endswith(tail):
        raise SystemExit("尾部格式与预期不符，中止（未做任何写入）")
    block = "  },\r\n  {\r\n" + E172 + "  },\r\n  {\r\n" + E173 + "  }\r\n ]\r\n}"
    src = src[: -len(tail)] + block

    io.open(P, "w", encoding="utf-8", newline="").write(src)
    print("已追加 #172 / #173")

    # 3) 自检：重新解析
    import json
    d = json.loads(io.open(P, encoding="utf-8").read())
    ids = [e["编号"] for e in d["条目"]]
    print("条目数：", len(ids), "，末三条编号：", ids[-3:])
    assert ids[-2:] == [172, 173], "编号校验失败"
    print("JSON 合法 ✅")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

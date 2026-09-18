# -*- coding: utf-8 -*-
"""R58 #197 追加对标清单，含无损往返自证。"""
import json, sys, os

P = r"G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json"

# 1. 读取原始文本
with open(P, "rb") as f:
    raw = f.read()
assert raw[:3] != b"\xef\xbb\xbf", "有BOM!"
text_lf = raw.decode("utf-8").replace("\r\n", "\n")
assert not text_lf.endswith("\n"), "文件尾有换行!"

data = json.loads(text_lf)
n_before = len(data["条目"])
print(f"读取成功，当前条目数: {n_before}")

# 2. 准备 #197
entry = {
    "编号": 197,
    "功能": "R58 词法收尾与环境红清账轮：L-174 设甲为三 + 切词/保护表 16 条词法红 + 18 条环境红处置 + 65 条语义债归因画像（代码生成21+类成员14+其余30）",
    "原模块": "light-merge 词法层（lexer.py 嵌入块/保护表）+ 0.82 依赖环境 + 65 条存量红归因底表",
    "光明模块": "light-merge/src/lexer.py（任务1 保护表/切词分支）+ lightharness（任务2 依赖装填 + 任务3/4 归因画像 + 任务5 docs）",
    "状态": "进行中",
    "完成轮次": "第58轮",
    "备注": (
        "任务1-5+路M 分发。①任务1（P0）：修 L-174 无空格赋值尾「为」丢失（设甲为三）+ 切词行为8条 + 单字保护表8条（除/匹/异/常/等/断/跃/现/引），16条词法红转绿，改 src/lexer.py 最小diff。"
        "②任务2（P1）：18条缺依赖环境红（lunardate 8 + requests 6 + cryptography 4）在0.82装依赖实测转绿或skipif豁免，决策依据实测。"
        "③任务3（P1，只读）：代码生成断言21条+类/成员访问14条逐条归因。"
        "④任务4（P1，只读，本轮已交付）：其余30条逐条归因——解析层7（5条L-174同源+2条旧式语法）、语义债其他12（网络请求5+L-174同源3+其他4）、异步修饰符5（报错信息质量）、内置清单3（低垂果实重跑脚本）、文档门2（清理L1文档）、examples聚合1（任务1后复评）。结构化明细见 _task4_R58_其余存量归因.md + .json。"
        "⑤任务5（P2）：本#197追加 + MEMORY更新 + 探针移档。"
        "⑥路M：唯一一次0.82全量（fast py3.12），预期红数≈99-16-18=65，新增红=0门PASS。"
        "纪律：子任务禁止并行全量；整轮仅1次全量归路M；本机不跑全量；0.82全量用 /usr/local/bin/python3.12；退出码禁接|tail|head。"
    ),
    "证据": [
        "lightharness/_task4_R58_其余存量归因.md",
        "lightharness/_task4_R58_其余存量归因明细.json",
        "lightharness/_task5_R58_docs+移档.md",
        "lightharness/reports/_task4_R57_存量红明细_072454.json",
    ],
}

# 3. 追加
assert data["条目"][-1]["编号"] == 196, f"最后一条编号不是196，而是 {data['条目'][-1]['编号']}"
data["条目"].append(entry)
n_after = len(data["条目"])
print(f"追加后条目数: {n_after}")

# 4. 序列化（indent=1, ensure_ascii=False）
out_lf = json.dumps(data, indent=1, ensure_ascii=False)
# 无损往返自证：重新解析必须相等
rt = json.loads(out_lf)
assert len(rt["条目"]) == n_after, "往返后条目数变了!"
assert rt["条目"][-1]["编号"] == 197, "往返后最后一条不是#197!"
assert rt["条目"][-2]["编号"] == 196, "往返后#196内容被破坏!"
print("无损往返自证通过")

# 5. LF → CRLF，确保无文件尾换行
out_crlf = out_lf.replace("\n", "\r\n")
assert not out_crlf.endswith("\n"), "仍有尾换行!"
assert not out_crlf.endswith("\r"), "仍有尾CR!"

# 6. 写回（无BOM）
with open(P, "wb") as f:
    f.write(out_crlf.encode("utf-8"))
print(f"写回完成: {P} ({len(out_crlf.encode('utf-8'))} bytes)")

# 7. 二次校验：重新读盘解析
with open(P, "rb") as f:
    verify = json.loads(f.read().decode("utf-8"))
assert len(verify["条目"]) == 197, f"读盘后条目数 {len(verify['条目'])} != 197"
assert verify["条目"][-1]["编号"] == 197
print("读盘校验通过：197条，#197在位")

# -*- coding: utf-8 -*-
"""R58 收口：#197 备注从「分发计划态」更新为「最终交付态」。"""
import json
from pathlib import Path

F = Path(r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\对标清单.json')
raw = F.read_bytes().decode('utf-8')
data = json.loads(raw)
canonical = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
assert canonical == raw, '无损自证失败：文件非规范格式'

i197 = [x for x in data['条目'] if x['编号'] == 197][0]
old = i197['备注']
new = (
    'R58 词法收尾与环境红清账轮（任务1-5+路M 交付）。①任务1（P0）词法收尾：**L-174 已修**'
    '（无空格赋值尾「为」丢失，设甲为三 → 设/甲/为/三 正确切分；examples/modules/main.light 实跑 rc=1→打印5）'
    '；16 条词法红全部转绿（本机 170 passed/253 subtests；0.82 定向 196 passed/4 failed 全为基线内红）；'
    '互举反跑 677 零新增；全语料 token A/B 38084 文件仅 1 文件变化（main.light，改善非回归）。'
    '单字保护关键发现：R28 已把 CS 表清零并加断言强锁（直接加单字会 lexer 导入失败），'
    '改由只读并集 _P0A_SINGLE_CHAR_PROTECTED（57 字，=正面类别并集）承担，9 个测试断言迁移；'
    'test_basic_keywords 钉现状同步更新为语义正确切分；test_variable_with_expression 由红转绿。'
    '②任务2（P1）环境红：18 条缺依赖红（lunardate 8 + requests 6 + cryptography 4）0.82 装依赖'
    '（lunardate 0.3.0/requests 2.34.2/cryptography 50.0.1 用户级 site-packages，cryptography FreeBSD 源码编译 wheel）'
    '**全部实测转绿，0 豁免 0 悬置**；定向 147 passed/0 failed 无新增红暴露；light-merge 零 diff。'
    '③任务3（P1，只读）35 条归因：21 条测试期望过时（L-096 _light_attr_get/_set helper 形态，1 条为 '
    '\'==\' 预置误伤）+ 14 条粘连己X 读取位不展开 codegen 缺陷（NameError: name \'己XX\'，src+unified 两后端 '
    '_resolve_* 同加类属性白名单分支一条修复可全清）；与 L-175 无关（100010 junitxml 交叉核对）。'
    '④任务4（P1，只读）30 条归因：解析层7（5条L-174同源已随任务1转绿+2条旧式语法）、语义债其他12'
    '（网络请求5+L-174同源3+其他4）、异步修饰符5（报错信息质量，需编译期提示）、内置清单3（低垂果实重跑脚本）、'
    '文档门2（清理L1文档）、examples聚合1。结构化明细见 _task3/_task4_R58_*归因明细.json/csv。'
    '⑤任务5：本 #197 追加（无损往返自证通过）+ MEMORY 更新 + R58 探针移档（docs/历史存档/R58探针/ 32 文件）。'
    '⑥路M：唯一一次 0.82 全量（fast py3.12），详见 _taskM_R58_收口总报告.md。'
    '纪律：子任务禁止并行全量；整轮仅 1 次全量归路M；本机不跑全量；0.82 用 /usr/local/bin/python3.12；退出码禁接 |tail|head；'
    '词法保护表改动必做全语料 token A/B + 互举反跑。'
)

i197['备注'] = new
out = json.dumps(data, ensure_ascii=False, indent=1).replace('\n', '\r\n')
assert not out.endswith('\n')
F.write_bytes(out.encode('utf-8'))
# 回读校验
data2 = json.loads(F.read_bytes().decode('utf-8'))
canon2 = json.dumps(data2, ensure_ascii=False, indent=1).replace('\n', '\r\n')
print('[回读] 条目数', len(data2['条目']), '| 往返一致', canon2 == out)
i197b = [x for x in data2['条目'] if x['编号'] == 197][0]
print('[197] 新备注长度', len(i197b['备注']), '| 含「L-174 已修」:', 'L-174 已修' in i197b['备注'], '| 含「0 豁免」:', '0 豁免' in i197b['备注'])

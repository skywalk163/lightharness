# R45 一次性脚本：向 docs/功能对标/对标清单.json 追加 #174 / #175
# 为什么不用 json.dump 整体重写：该文件是 CRLF + 非标准缩进，整体序列化会产生
# 5000+ 行 diff。这里做「外科式文本插入」，只增不改。
import io
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
P = os.path.join(ROOT, 'docs', '功能对标', '对标清单.json')

raw = io.open(P, encoding='utf-8', newline='').read()

NEW = [
    {
        "编号": 174,
        "功能": "影子变量编译告警 L-166（函数内写模块级同名变量未声明『全局』）",
        "原模块": "（语言层新增能力，非既有模块对标）",
        "光明模块": "light-merge/src/scope_shadow_check.py + cli/light.py 接入",
        "状态": "已完成",
        "说明": ("L-165 类缺陷（漏写『全局 当前实例』导致模块级变量静默不被写回、"
                 "HTTP 服务恒 500）在编译期零报错零警告。新增静态检查：解析后扫描，"
                 "判定『函数内赋值名 ∈ 模块级名 且 ∉ 全局声明 且 ∉ 形参』→ 告警。"
                 "接入点是真正生效的编译入口 cli/light.py::_compile_src 与 "
                 "_resolve_local_imports（light run 不走 LightCompiler.compile()，"
                 "一开始接错实测 0 条告警）；输出 stderr，LIGHT_WARN_GLOBAL_SHADOW=0 可关。"
                 "顺带补齐 LightCompiler.compile() 此前不返回 warnings 的洞（L-068 告警一直不可见）。"
                 "全语料 702 文件命中 12 文件/40 条，其中 22 条为潜在缺陷（另登记 L-168/L-169）。"),
    },
    {
        "编号": 175,
        "功能": "0.82 git 就位 + 双平台回归完全对齐 + flaky 加固 L-167",
        "原模块": "跨平台验证（FreeBSD 15.1）",
        "光明模块": "lightharness/scripts/同步0.82.py、stdlib/外部命令.py、examples/test_子进程后台.light",
        "状态": "已完成",
        "说明": ("复核 0.82 已装 git 2.54.0；第44轮 2 条 ERROR 消失，但退化为 SKIP"
                 "（/tmp 副本不是 git 工作树）。给同步脚本加 --with-git 连 .git 一起同步"
                 "（97MB→172MB，上传 10.8s），远端 HEAD=141aa2c，该测试文件在 0.82 上 2 passed。"
                 "flaky 加固：外部命令.等待进程 超时 kill 后未收尸（僵尸/管道泄漏）登记并修复为 L-167；"
                 "test_子进程后台 改用运行器注入的 HARNESS_PY 而非写死 python、等待 5s→20s、"
                 "失败消息带输出/错误（语义断言一条未减）。"
                 "最终双平台：本机与 0.82 同为 7 failed/1238 passed/3 skipped/0 errors，"
                 "失败清单逐条一致，基线外零新增红。"),
    },
]

# 逐条校验可序列化（避免写出非法 JSON）
for e in NEW:
    json.dumps(e, ensure_ascii=False)

# 兼容 CRLF / LF 两种行尾（本仓 core.autocrlf=true，blob 应是 LF）
marker = "\r\n ]\r\n}" if raw.endswith("\r\n ]\r\n}") else "\n ]\n}"
assert raw.endswith(marker), "尾部格式不符：" + repr(raw[-20:])
head, tail = raw[:-len(marker)], marker
nl = "\r\n" if marker.startswith("\r\n") else "\n"

parts = [head]
for e in NEW:
    parts.append("," + nl + "  " + json.dumps(e, ensure_ascii=False, indent=None))
parts.append(tail)
out = "".join(parts)

io.open(P, 'w', encoding='utf-8', newline='').write(out)

d = json.loads(io.open(P, encoding='utf-8').read())
print(f"JSON 合法；条目数 {len(d['条目'])}；末条编号 {d['条目'][-1]['编号']}")

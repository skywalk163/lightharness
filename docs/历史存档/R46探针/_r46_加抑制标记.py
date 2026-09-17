# R46：给「本意就是局部变量」的合法遮蔽加行尾抑制标记 `# 抑制L166`
# 依据：第45/46轮全语料审定——这些段落刻意用局部同名变量（纯函数/夹具/累加器），
#       加『全局』反而会引入跨段状态，所以标注抑制而不是改语义。
import io, os

BASE = r'G:\dswork\duan-light-merge\lightharness'
MARK = '  # 抑制L166'

# (相对路径, 行号(1-based), 说明)
PLAN = [
    ('src/会话格式.light', 41, '非负整数/占：局部占位累加器'),
    ('src/会话格式.light', 45, '判版本/占：局部占位累加器'),
    ('src/会话格式.light', 321, '解码V3事件/占：局部占位累加器'),
    ('src/会话格式.light', 560, '记录助手轮/占：局部占位累加器'),
    ('examples/test_R28_列词尾切出.light', 29, '测试_遍历序列/序列：局部测试数据'),
    ('examples/test_字符串替换编辑器.light', 48, '造宿主/文件表：局部夹具'),
    ('examples/test_字符串替换编辑器.light', 66, '造限宿主/宿主：局部夹具'),
    ('examples/test_文件系统工具.light', 42, '造宿主/文件表：局部夹具'),
    ('examples/test_文件系统工具.light', 44, '造宿主/已观察快照：局部夹具'),
    ('examples/test_文件系统工具.light', 57, '造宿主/头字节表：局部夹具'),
    ('examples/test_预设.light', 286, '反跑_可删判定/系统预设：局部快照'),
]

for rel, lineno, why in PLAN:
    p = os.path.join(BASE, rel)
    raw = io.open(p, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in raw else '\n'
    lines = raw.split(nl)
    idx = lineno - 1
    if idx >= len(lines):
        print(f'!! {rel}:{lineno} 越界，跳过')
        continue
    line = lines[idx]
    if '抑制L166' in line:
        print(f'== {rel}:{lineno} 已有抑制标记，跳过')
        continue
    lines[idx] = line.rstrip() + MARK
    io.open(p, 'w', encoding='utf-8', newline='').write(nl.join(lines))
    print(f'OK {rel}:{lineno}  ({why})')
    print('     ' + lines[idx].strip()[:100])

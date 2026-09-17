# R46：给 light-merge 示例段落补『全局 X』声明（修 L-169 真缺陷）
# 用法：python _r46_加全局.py [--apply]
#   不带 --apply = dry-run，只打印将要插入的位置
import io, os, sys, re

BASE = r'G:\dswork\duan-light-merge\light-merge'

# (相对路径, 段落名, [变量名...], 句末是否带「。」)
PLAN = [
    ('examples/games/snake.light', '初始化游戏', ['蛇身', '方向', '分数', '游戏结束'], True),
    ('examples/games/snake.light', '移动蛇', ['分数', '游戏结束'], True),
    ('examples/games/snake.light', '处理输入', ['方向', '游戏结束'], True),

    ('examples/snake_game/主.light', '加载最高分', ['最高分'], True),
    ('examples/snake_game/主.light', '初始化游戏', ['蛇身', '方向', '分数', '游戏结束'], True),
    ('examples/snake_game/主.light', '移动蛇', ['分数', '游戏结束'], True),
    ('examples/snake_game/主.light', '显示游戏结束', ['最高分'], True),
    ('examples/snake_game/主.light', '处理输入', ['方向', '游戏结束'], True),

    ('examples/kids/number_game.light', '玩一局', ['总游戏次数', '总猜测次数', '最高分'], False),

    ('examples/calculator_app/主.light', '计算', ['当前值'], True),
    ('examples/calculator_app/主.light', '主程序', ['当前值'], True),

    ('examples/file_tools/batch_rename/主.light', '执行批量重命名', ['计数器'], True),
    ('examples/file_tools/batch_rename/主.light', '解析参数',
     ['当前目录', '要添加前缀', '要添加后缀', '预览模式'], True),

    ('examples/blog_app/main.light', '处理创建文章', ['下一文章ID'], True),
]

APPLY = '--apply' in sys.argv


def find_paragraph_line(lines, name):
    """返回段落定义行下标列表（行首『段落 name』/『异步 段落 name』，后跟 空/:/：/空格/接收）"""
    hits = []
    for i, ln in enumerate(lines):
        s = ln.lstrip()
        if s.startswith('异步 段落 '):
            rest = s[len('异步 段落 '):]
        elif s.startswith('段落 '):
            rest = s[len('段落 '):]
        else:
            continue
        # 取名字：到 空格/: /：/换行 为止
        m = re.match(r'^([^\s:：]+)', rest)
        if m and m.group(1) == name:
            hits.append(i)
    return hits


def body_insert_pos(lines, def_idx):
    """段落定义行之后，第一个非空且非注释行的下标"""
    i = def_idx + 1
    while i < len(lines):
        s = lines[i].strip()
        if s == '' or s.startswith('#') or s.startswith('//'):
            i += 1
            continue
        return i
    return None


def main():
    pending = {}
    for rel, para, names, period in PLAN:
        path = os.path.join(BASE, rel)
        raw = io.open(path, encoding='utf-8', newline='').read()
        nl = '\r\n' if '\r\n' in raw else '\n'
        lines = raw.split(nl)
        hits = find_paragraph_line(lines, para)
        if len(hits) != 1:
            print(f'!! {rel} 段落『{para}』匹配 {len(hits)} 处，跳过')
            continue
        pos = body_insert_pos(lines, hits[0])
        if pos is None:
            print(f'!! {rel} 段落『{para}』找不到段落体，跳过')
            continue
        indent = re.match(r'^[\s　]*', lines[pos]).group(0)
        dot = '。' if period else ''
        add = [indent + '全局 ' + n + dot for n in names]
        # 幂等：已声明的不再插
        exist = set()
        j = pos
        while j < len(lines) and lines[j].strip().startswith('全局 '):
            m = re.match(r'^\s*全局\s+([^\s。]+)', lines[j])
            if m:
                exist.add(m.group(1))
            j += 1
        add = [a for a in add if a.strip().replace('全局 ', '').rstrip('。') not in exist]
        if not add:
            print(f'== {rel}『{para}』已声明，跳过')
            continue
        print(f'-- {rel} 段落『{para}』(定义行{hits[0]+1}) → 在行{pos+1}前插入:')
        for a in add:
            print('     ' + a)
        pending.setdefault(path, (raw, nl, lines, []))[3].append((pos, add))

    if not APPLY:
        print('\n[dry-run] 未写入。加 --apply 执行。')
        return
    for path, (raw, nl, lines, inserts) in pending.items():
        # 从后往前插，避免下标偏移
        for pos, add in sorted(inserts, key=lambda x: -x[0]):
            lines[pos:pos] = add
        io.open(path, 'w', encoding='utf-8', newline='').write(nl.join(lines))
        print('written:', path)


main()

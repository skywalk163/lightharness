# -*- coding: utf-8 -*-
"""R24 任务5 反跑（全量回归扫描）：阶段D 单字通用化（任务1 + 任务3）前后零回归验证。

对比基准（**不用裸 HEAD**，按项目反跑纪律自动上溯）：
  断裂态 = 最近一个「不含 R24 标记」的祖先提交的 src/lexer.py
           （判定标记：`_p0a_contains_sep` —— 任务1 落库的新增 helper。
            R24 若已提交，HEAD 会自带该标记，此时判据 A 会恒假 ⇒ 自动退到
            HEAD^ / HEAD^^ … 直到命中）。
  修复态 = 当前工作区 src/lexer.py。

本轮工作区改动（相对基准，见交付报告 §改动清单）：
  · 任务1：R21「非语句起始关键字前缀标识符整体成词」分支新增**第 4 道闸门**——
          整串含成员/关系分隔符（_P0A_SEP：之/在/于/为/与）时不并入。修复
          `自之姓名` 在表达式/实参/调用位置被并成一词（编译期 NameError）。
          新增 helper `_p0a_contains_sep` 与类属性 `_P0A_SEP_CHAR_HINTS`。
  · 任务3：CR1 规则（成员访问段首并入，`_seg_after_sep` 游标）+ 删除全库零引用
          死代码 `_P0A_COMPOUND_SAFE`。CS 保持 30 条（审计结论：13 字保留）。
  · 任务4（同文件并行）：仅注释 + import 期等价断言，**无行为改动**（§改动清单已核）。

判据：
  [A] 基线自检：同一模块两次 dump 一致（确定性）。
  [B] 真实源 token 变化仅限预期（`学生模块.light` 的 `自之成绩` 修正）；
      生成产物树 light-merge/bootstrap/** 的漂移仅记录（已损坏生成产物，不落任何测试断言路径）。
  [C] 性能：修复态不应下降（>10% 判回归）。
  [D] 100+ 自由名专项：清单内每个自由名在两侧都整体成词（单 IDENTIFIER）且逐字节一致。
  [E] 语句起始裸名/关键字切分：两侧逐字节一致（约束 6）。
  [F] 核心用例（L-084/L-092/L-119/L-120/L-152 家族…）编译运行 rc/stdout 两侧一致。
  [G] R24 新增 4 个 .light 用例在修复态 rc=0。
  [H] 真实变化文件（学生模块.light）编译 A/B：修复态不得比基准更差。
  [I] OLD 路径（deterministic=False，遗留模式）真实源变化仅留痕，不门控。

反跑脚本在 finally 中恢复 src/lexer.py 并用 sha256 校验还原。
证据写入 _task5_R24_全量回归证据.json。
"""
import os
import sys
import glob
import json
import time
import hashlib
import tempfile
import subprocess
import importlib.util
import statistics

ROOT = r'G:/dswork/duan-light-merge'
LIGHTP = ROOT + '/light-merge'
HARNESS = ROOT + '/lightharness'
LEXER = os.path.join(LIGHTP, 'src', 'lexer.py')
sys.path.insert(0, os.path.join(LIGHTP, 'src'))

PATTERNS = [
    HARNESS + '/examples/**/*.light',
    HARNESS + '/src/**/*.light',
    HARNESS + '/tests/**/*.light',
    LIGHTP + '/examples/**/*.light',
    LIGHTP + '/stdlib/**/*.light',
    LIGHTP + '/bootstrap/**/*.light',
    LIGHTP + '/src/**/*.light',
    LIGHTP + '/tests/**/*.light',
]
CORPUS = sorted(set(sum((glob.glob(g, recursive=True) for g in PATTERNS), [])))
GENERATED_TREES = [os.path.join(LIGHTP, 'bootstrap')]

R24_MARKER = '_p0a_contains_sep'

CORE_CASES = [
    HARNESS + '/examples/test_L084.light',
    HARNESS + '/examples/test_L092.light',
    HARNESS + '/examples/test_L119.light',
    HARNESS + '/examples/test_L120.light',
    HARNESS + '/examples/test_R21_L152家族嵌套形参.light',
    HARNESS + '/examples/test_R21_L152嵌套段落形参.light',
]

R24_NEW_CASES = [
    HARNESS + '/examples/test_R24_的递归修复.light',
    HARNESS + '/examples/test_R24_运算符单字守卫.light',
    HARNESS + '/examples/test_R24_值字面量守卫.light',
    HARNESS + '/examples/test_R24_单字通用规则.light',
]

# 任务5 验证标准 3：100+ 自由名（通用化后必须仍整体成词）。
# 本清单 175 条**已预分类验证**：两侧均为单 IDENTIFIER 且逐字节一致。
FREE_NAMES = [
    # —— 任务书点名 ——
    '去除空格', '索引', '种类', '阶乘',
    # —— 单字保护表的真实护栏场景（词首/词中/词尾并入）——
    '对象', '列表',
    '加法', '减法', '乘法表', '余数', '除法',
    '真实', '空白', '空值', '真空', '真假标志',
    '错误己', '自己', '爱己', '知己',
    '低级关闭', '正则匹配', '环境枚举',
    '输出结果', '输出格式', '输出块表', '输出列表', '可打印',
    '返回码', '退出码', '接收参数', '非空块', '导出事件表', '整理模型消息',
    '外部命令', '排序依据', '列表包含', '列表长度', '字典设置', '字典获取',
    '合并为', '尝试记录',
    # —— 含 `的` 的自由名（任务1 的 `的` 契约）——
    '我的书', '红色的花', '小的大的',
    # —— 含运算符/值字面量字面的自由名（约束 5）——
    '去除空白', '乘法口诀',
    '增加', '体重增加', '减少', '加数', '除数', '余数表',
    # —— L-120 / 标识符切分红线的安全对照（L-119/L-120）——
    '错误甲', '文本长', '首条表', '占位A', '伪终端会话',
    # —— 常见复合词 / 内建名 ——
    '平方根', '四舍五入', '随机整数', '十六进制',
    '字符串转整数', '整数转字符串',
    '文件存在', '目录存在', '路径连接', '绝对路径', '规范化路径',
    '写入文件', '读取文件', '创建临时目录',
    # —— 序列化 / 数据结构 ——
    '序列化JSON', '反序列化JSON', '字典键列表', '键值列表',
    '二叉树', '红黑树', '哈希表', '优先队列', '双向链表',
    # —— 具身/业务域词（防止通用规则误伤）——
    '机械臂关节角', '末端执行器', '力矩传感器', '惯性测量单元',
    '供应链节点', '库存周转率', '资产负债率',
    # —— 标准库/算法/系统/网络域词（扩充至 100+）——
    '列表追加', '列表插入', '列表删除', '列表排序', '列表反转',
    '字典合并', '字典删除', '字典键', '字典值',
    '字符串长度', '字符串查找', '字符串替换', '字符串分割', '字符串连接', '字符串反转',
    '整数转换', '浮点转换', '文件读取', '时间戳', '日期格式', '随机数',
    '冒泡排序', '快速排序', '二分查找', '深度优先', '广度优先', '动态规划',
    '向量点积', '协方差', '标准差', '正态分布', '激活函数', '损失函数',
    '梯度下降', '反向传播', '注意力机制', '强化学习', '遗传算法', '模拟退火',
    '卡尔曼滤', '状态估计', '路径规划', '运动规划', '位姿估计', '关节角度',
    '扭矩控制', '力觉反馈', '视觉伺服', '点云配准', '目标检测', '语义分割',
    '特征提取', '特征匹配', '光流估计', '深度估计', '视觉里程',
    '数组长度', '集合交集', '集合差集', '映射转换',
    '过滤器', '迭代器', '装饰器', '上下文管理', '错误处理',
    '日志记录', '性能分析', '内存管理', '垃圾回收', '引用计数',
    '线程锁', '信号量', '条件变量', '事件循环', '协程调度', '进程池', '线程池',
    '连接池', '缓存命中', '哈希映射', '布隆过滤', '一致性哈希',
    '负载均衡', '故障转移', '健康检查', '灰度发布', '蓝绿部署',
]

# 契约串（多 token，但**两侧必须逐字节一致**）：任务1 的 `之/在/于/为/与`
# 分隔符契约 + `的` 契约 + 值字面量/运算符契约。这些串在基线上本就不是单标识符
# （`对于` → 对+于），[D] 只要求「两侧一致」，不要求单 token。
CONTRACT_CASES = [
    '10的幂', '当前值', '自加乙', '定义幂', '取余',
    '异常己', '异常甲', '断言之', '断言为真', '判定为空',
    '函数的参数', '自之姓名', '对象之方法', '甲之乙', '人之构造',
    '甲属于乙', '不在', '对于',
    '断言大于', '断言大于等于', '定义文件存在', '定义目录存在',
    '除类型错误', '是否为空', '等于空', '被除数',
    '接收数', '段落阶乘接收数', '现金流量表',
]

PROBE_DIR = os.path.join(tempfile.gettempdir(), 'r24_t5_probe')
PROBE_FILES = {}


def is_generated(f):
    nf = os.path.normpath(f)
    return any(nf.startswith(os.path.normpath(t) + os.sep) or nf == os.path.normpath(t)
               for t in GENERATED_TREES)


def sha256_text(t):
    return hashlib.sha256(t.encode('utf-8')).hexdigest()


def git_show(rev, path):
    return subprocess.check_output(['git', '-C', LIGHTP, 'show', '%s:%s' % (rev, path)],
                                   encoding='utf-8')


def resolve_baseline():
    """上溯找到第一个不含 R24 标记的提交（返回 (rev, src_text)）。"""
    revs = subprocess.check_output(['git', '-C', LIGHTP, 'log', '--format=%H', '-n', '30'],
                                   encoding='utf-8').split()
    for rev in revs:
        try:
            txt = git_show(rev, 'src/lexer.py')
        except subprocess.CalledProcessError:
            continue
        if R24_MARKER not in txt:
            return rev, txt
    raise RuntimeError('未能在 30 个祖先提交中找到 R24 之前的 lexer.py')


def load_lexer_from_source(src_text, modname):
    d = tempfile.mkdtemp(prefix='lxr24_')
    p = os.path.join(d, modname + '.py')
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(src_text)
    spec = importlib.util.spec_from_file_location(modname, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


def tok_key(mod, src, old=False):
    try:
        toks = mod.Lexer(src, deterministic=(not old)).tokenize()
        return hashlib.sha256(
            repr([(t.type.name, t.value) for t in toks]).encode()).hexdigest()
    except Exception as e:  # noqa
        return 'ERR:' + type(e).__name__


def tok_pairs(mod, src):
    return [(t.type.name, t.value) for t in mod.Lexer(src, deterministic=True).tokenize()
            if t.type.name != 'EOF']


def read(f):
    with open(f, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def write_probes():
    os.makedirs(PROBE_DIR, exist_ok=True)
    a = os.path.join(PROBE_DIR, 'probe_之成员访问.light')
    with open(a, 'w', encoding='utf-8', newline='\n') as f:
        f.write(
            '类 学生:\n'
            '    段落 初始化 接收 姓名:\n'
            '        己.姓名 = 姓名\n'
            '    段落 问候:\n'
            '        返回 "你好 " + 己.姓名\n'
            '段落 主:\n'
            '    设 甲 为 新建 学生("小明")\n'
            '    打印 甲.问候()\n'
            '    设 成绩表 为 {甲: 90}\n'
            '    打印 成绩表[甲]\n'
            '    设 数列 为 [1, 2, 3]\n'
            '    遍历 项 之 数列:\n'
            '        打印 项\n\n主()\n')
    b = os.path.join(PROBE_DIR, 'probe_自由名保留.light')
    with open(b, 'w', encoding='utf-8', newline='\n') as f:
        f.write(
            '段落 主:\n'
            '    设 甲 为 去除空格("  x  ")\n'
            '    设 乙 为 10的幂(2)\n'
            '    设 丙 为 阶乘(5)\n'
            '    设 丁 为 列表长度([1, 2])\n'
            '    设 戊 为 平方根(16.0)\n'
            '    打印 甲\n'
            '    打印 乙\n'
            '    打印 丙\n'
            '    打印 丁\n'
            '    打印 戊\n\n主()\n')
    for p in (a, b):
        PROBE_FILES[p] = read(p)


def main():
    print('语料 .light 文件：%d' % len(CORPUS))
    base_rev, base_text = resolve_baseline()
    cur_text = read(LEXER)
    print('断裂态基准提交：%s（%s）'
          % (base_rev[:12],
             subprocess.check_output(['git', '-C', LIGHTP, 'log', '-1', '--format=%s', base_rev],
                                     encoding='utf-8').strip()[:60]))
    print('修复态 lexer.py sha256：%s' % sha256_text(cur_text)[:16])

    base_mod = load_lexer_from_source(base_text, '_lexer_base_r24')
    edit_mod = load_lexer_from_source(cur_text, '_lexer_edit_r24')

    print('基准 CS：%d 条  →  修复态 CS：%d 条'
          % (len(base_mod._COMPOUND_SAFE_SINGLE_KEYWORDS),
             len(edit_mod._COMPOUND_SAFE_SINGLE_KEYWORDS)))
    print('基准 CCW：%d 条  →  修复态 CCW：%d 条'
          % (len(base_mod.COMMON_COMPOUND_WORDS), len(edit_mod.COMMON_COMPOUND_WORDS)))
    print('死代码 _P0A_COMPOUND_SAFE：基准有=%s ｜ 修复态有=%s'
          % (hasattr(base_mod, '_P0A_COMPOUND_SAFE'), hasattr(edit_mod, '_P0A_COMPOUND_SAFE')))
    assert not hasattr(edit_mod, '_P0A_COMPOUND_SAFE'), '修复态应已删除死代码'
    assert len(edit_mod._COMPOUND_SAFE_SINGLE_KEYWORDS) == 30, '修复态 CS 应保持 30 条'
    assert len(edit_mod.COMMON_COMPOUND_WORDS) == 37, '修复态 CCW 应保持 37 条'

    # 语料内容**一次性快照**：多 agent 并行时磁盘文件可能被并发写入，
    # 若每次 dump 重新 read(f)，[A] 基线自检会因外部写入而假红。
    TEXTS = {f: read(f) for f in CORPUS}

    def dump(mod, old=False):
        return {f: tok_key(mod, TEXTS[f], old=old) for f in CORPUS}

    NIT = 3
    base_times, edit_times = [], []
    base = edit = None
    for _ in range(NIT):
        t0 = time.time(); base = dump(base_mod); base_times.append(time.time() - t0)
        t0 = time.time(); edit = dump(edit_mod); edit_times.append(time.time() - t0)
    t_base, t_edit = statistics.median(base_times), statistics.median(edit_times)

    a_ok = (dump(base_mod) == base) and (dump(edit_mod) == edit)
    print('[A] 基线自检（两侧各两次 dump 一致）  %s' % ('PASS' if a_ok else 'FAIL'))

    changed = [f for f in base if base[f] != edit.get(f)]
    ch_real = [f for f in changed if not is_generated(f)]
    ch_gen = [f for f in changed if is_generated(f)]
    # 预期变化白名单：任务1 唯一真实源修正 = 学生模块.light 的 `自之成绩`
    EXPECTED_REAL = {os.path.normpath(LIGHTP + '/examples/L2_wenyan/学生模块.light')}
    unexpected_real = [f for f in ch_real if os.path.normpath(f) not in EXPECTED_REAL]
    b_ok = (len(unexpected_real) == 0)
    print('[B] 真实源 token 变化 %d 文件（预期 %d）｜生成树漂移 %d  %s'
          % (len(ch_real), len(EXPECTED_REAL), len(ch_gen), 'PASS' if b_ok else 'FAIL'))
    for f in ch_real:
        tag = '预期修正' if os.path.normpath(f) in EXPECTED_REAL else '★意外回归'
        print('      真实源变化[%s]: %s' % (tag, os.path.relpath(f, ROOT)))
    for f in ch_gen:
        print('      生成树漂移: %s' % os.path.relpath(f, ROOT))

    perf_ok = (t_edit <= t_base * 1.10)
    print('[C] 性能：基准中位 %.2fs vs 修复态中位 %.2fs  ×%.3f  %s'
          % (t_base, t_edit, (t_base / t_edit) if t_edit else 0,
             'PASS' if perf_ok else 'FAIL'))

    # [D] 100+ 自由名专项（单 IDENTIFIER + 两侧一致）
    free_bad = []
    for nm in FREE_NAMES:
        pb = tok_pairs(base_mod, nm)
        pe = tok_pairs(edit_mod, nm)
        single_ok = (len(pe) == 1 and pe[0][0] == 'IDENTIFIER' and pe[0][1] == nm)
        if not single_ok or pb != pe:
            free_bad.append({'name': nm, 'base': pb, 'edit': pe})
    d_ok = (len(free_bad) == 0)
    print('[D] 100+ 自由名专项：%d 条，全部整体成词且两侧一致  %s'
          % (len(FREE_NAMES), 'PASS' if d_ok else 'FAIL'))
    for it in free_bad[:10]:
        print('      ★', it)
    assert len(FREE_NAMES) >= 100, '自由名清单须 100+ 条'

    # [D2] 契约串两侧逐字节一致（多 token，含之/在/于/为/与 分隔符）
    contract_bad = []
    for s in CONTRACT_CASES:
        pb, pe = tok_pairs(base_mod, s), tok_pairs(edit_mod, s)
        if pb != pe:
            contract_bad.append({'src': s, 'base': pb, 'edit': pe})
    d2_ok = (len(contract_bad) == 0)
    print('[D2] 分隔符契约串：%d 条两侧逐字节一致  %s'
          % (len(CONTRACT_CASES), 'PASS' if d2_ok else 'FAIL'))
    for it in contract_bad[:10]:
        print('      ★', it)

    # [E] 语句起始裸名 / 关键字切分（约束 6）
    STMT_CASES = ['长度 为 5', '设甲为三。', '如果为真', '那么 返回 一',
                  '段落 阶乘 接收 n', '导出 事件表', '接收 参数', '非空 块',
                  '己姓名', '段落阶乘接收n', '如果数小于等于二那么返回一']
    stmt_bad = []
    for s in STMT_CASES:
        pb, pe = tok_pairs(base_mod, s), tok_pairs(edit_mod, s)
        if pb != pe:
            stmt_bad.append({'src': s, 'base': pb, 'edit': pe})
    e_ok = (len(stmt_bad) == 0)
    print('[E] 语句起始裸名/关键字切分：%d 例两侧逐字节一致  %s'
          % (len(STMT_CASES), 'PASS' if e_ok else 'FAIL'))
    for it in stmt_bad[:10]:
        print('      ▲', it)

    # ===== 以下 [F]/[G]/[H] 需要**原地替换** src/lexer.py 走真 CLI（含 sha256 校验还原）=====
    # ⚠️ 多 agent 并行时，替换窗口若被外部写入打断会**覆盖他人改动**。故先做
    # 「外部写入检测」：sha 与脚本起始快照不符则放弃替换（宁可不跑也不覆盖）。
    sha_cur = sha256_text(cur_text)
    assert sha256_text(read(LEXER)) == sha_cur, (
        '★ 外部写入检测：src/lexer.py 在脚本起始后被改动，放弃原地替换以免覆盖并发改动')
    f_ok = g_ok = h_ok = True
    e_report, f_report, h_report = {}, {}, {}
    REAL_CHANGED = [f for f in ch_real] + [LIGHTP + '/examples/L2_wenyan/学生模块.light']
    try:
        write_probes()
        cases = [(f, 'run') for f in CORE_CASES if os.path.exists(f)]
        cases += [(p, 'compile') for p in PROBE_FILES]
        # 真实源变化文件：只编译（模块，非入口程序），两侧记录 rc/输出特征
        h_cases = sorted(set(os.path.normpath(f) for f in REAL_CHANGED))

        for phase in ('base', 'edit'):
            blob = base_text if phase == 'base' else cur_text
            with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
                fh.write(blob)
            assert sha256_text(read(LEXER)) == sha256_text(blob), '原地替换失败'
            bucket = e_report if phase == 'base' else f_report
            for path, kind in cases:
                if kind == 'run':
                    r = subprocess.run([sys.executable, os.path.join(HARNESS, '运行.py'), path],
                                       capture_output=True, text=True, encoding='utf-8',
                                       errors='replace', timeout=600, cwd=HARNESS)
                    bucket[path] = {'rc': r.returncode,
                                    'out': (r.stdout or '') + (r.stderr or '')}
                else:
                    out_py = os.path.join(PROBE_DIR,
                                          'gen_%s_%s.py' % (phase, os.path.basename(path)))
                    r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cli.light',
                                        'compile', path, '-o', out_py, '--backend', 'src'],
                                       capture_output=True, text=True, encoding='utf-8',
                                       errors='replace', timeout=600, cwd=LIGHTP)
                    gen = read(out_py) if os.path.exists(out_py) else ''
                    bucket[path] = {
                        'rc': r.returncode, 'gen_sha': sha256_text(gen), 'gen_len': len(gen),
                        'err': '' if r.returncode == 0 else ((r.stdout or '') + (r.stderr or ''))[-400:]}
            if phase == 'base':
                for path in h_cases:
                    out_py = os.path.join(PROBE_DIR, 'gen_%s_%s.py' % (phase, os.path.basename(path)))
                    r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cli.light',
                                        'compile', path, '-o', out_py, '--backend', 'src'],
                                       capture_output=True, text=True, encoding='utf-8',
                                       errors='replace', timeout=600, cwd=LIGHTP)
                    h_report[path] = {'base_rc': r.returncode,
                                      'base_err': '' if r.returncode == 0 else ((r.stdout or '') + (r.stderr or ''))[-200:]}
            else:
                for path in h_cases:
                    out_py = os.path.join(PROBE_DIR, 'gen_%s_%s.py' % (phase, os.path.basename(path)))
                    r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'cli.light',
                                        'compile', path, '-o', out_py, '--backend', 'src'],
                                       capture_output=True, text=True, encoding='utf-8',
                                       errors='replace', timeout=600, cwd=LIGHTP)
                    h_report.setdefault(path, {})['edit_rc'] = r.returncode
                    h_report[path]['edit_err'] = '' if r.returncode == 0 else ((r.stdout or '') + (r.stderr or ''))[-200:]
    finally:
        with open(LEXER, 'w', encoding='utf-8', newline='') as fh:
            fh.write(cur_text)
        assert sha256_text(read(LEXER)) == sha_cur, '★ src/lexer.py 还原失败！'
        print('      [还原校验] src/lexer.py sha256 = %s  OK' % sha_cur[:16])

    for p in e_report:
        if e_report[p] != f_report.get(p):
            f_ok = False
            print('      [F] 差异:', os.path.basename(p))
    print('[F] 核心用例（%d 个）编译运行 rc/stdout 两侧一致  %s'
          % (len(e_report), 'PASS' if f_ok else 'FAIL'))

    # [G] R24 新增用例 rc=0（修复态）
    g_bad = []
    for p in R24_NEW_CASES:
        r = subprocess.run([sys.executable, os.path.join(HARNESS, '运行.py'), p],
                           capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=600, cwd=HARNESS)
        if r.returncode != 0:
            g_bad.append(os.path.basename(p))
    g_ok = (len(g_bad) == 0)
    print('[G] R24 新增用例（%d 个）修复态 rc=0  %s'
          % (len(R24_NEW_CASES), 'PASS' if g_ok else 'FAIL'))
    for b in g_bad:
        print('      ★ rc!=0:', b)

    # [H] 真实变化文件编译 A/B：修复态不得比基准更差
    h_bad = []
    for path, rec in h_report.items():
        brc, erc = rec.get('base_rc'), rec.get('edit_rc')
        worse = (brc == 0 and erc != 0)
        if worse:
            h_bad.append((path, brc, erc))
    h_ok = (len(h_bad) == 0)
    print('[H] 真实变化文件（%d 个）编译 A/B：修复态不劣于基准  %s'
          % (len(h_report), 'PASS' if h_ok else 'FAIL'))
    for path, rec in h_report.items():
        print('      %s: base_rc=%s → edit_rc=%s'
              % (os.path.relpath(path, ROOT), rec.get('base_rc'), rec.get('edit_rc')))

    d_base = dump(base_mod, old=True)
    d_edit = dump(edit_mod, old=True)
    d_real = [f for f in CORPUS if d_base[f] != d_edit.get(f) and not is_generated(f)]
    d_gen = [f for f in CORPUS if d_base[f] != d_edit.get(f) and is_generated(f)]
    print('[I] OLD 路径(deterministic=False) 真实源变化 %d（遗留模式，不门控）｜生成树 %d'
          % (len(d_real), len(d_gen)))

    ok = a_ok and b_ok and perf_ok and d_ok and d2_ok and e_ok and f_ok and g_ok and h_ok
    ev = {
        'baseline_rev': base_rev,
        'corpus_files': len(CORPUS),
        'real_corpus_files': len([f for f in CORPUS if not is_generated(f)]),
        'generated_corpus_files': len([f for f in CORPUS if is_generated(f)]),
        'base_cs': len(base_mod._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'edit_cs': len(edit_mod._COMPOUND_SAFE_SINGLE_KEYWORDS),
        'base_ccw': len(base_mod.COMMON_COMPOUND_WORDS),
        'edit_ccw': len(edit_mod.COMMON_COMPOUND_WORDS),
        'dead_code_P0A_COMPOUND_SAFE_removed': (not hasattr(edit_mod, '_P0A_COMPOUND_SAFE')),
        'baseline_selfcheck': a_ok,
        'token_changed_real': len(ch_real),
        'token_changed_generated': len(ch_gen),
        'changed_real_files': [os.path.relpath(f, ROOT) for f in ch_real],
        'unexpected_real_files': [os.path.relpath(f, ROOT) for f in unexpected_real],
        'changed_generated_files': [os.path.relpath(f, ROOT) for f in ch_gen],
        'free_names_count': len(FREE_NAMES),
        'free_names_bad': free_bad,
        'contract_cases_count': len(CONTRACT_CASES),
        'contract_cases_bad': contract_bad,
        'contract_cases_consistent': d2_ok,
        'stmt_cases_count': len(STMT_CASES),
        'stmt_cases_bad': stmt_bad,
        'oldpath_real_changes': len(d_real),
        'oldpath_generated_changes': len(d_gen),
        'oldpath_real_files': [os.path.relpath(f, ROOT) for f in d_real[:50]],
        'time_base_s': round(t_base, 2),
        'time_edit_s': round(t_edit, 2),
        'time_base_iters_s': [round(x, 2) for x in base_times],
        'time_edit_iters_s': [round(x, 2) for x in edit_times],
        'perf_ok': perf_ok,
        'core_cases_consistent': f_ok,
        'core_cases': {os.path.basename(p): e_report[p] for p in e_report},
        'r24_new_cases_ok': g_ok,
        'r24_new_cases_bad': g_bad,
        'real_changed_compile_ab': {os.path.relpath(p, ROOT): h_report[p] for p in h_report},
        'real_changed_compile_not_worse': h_ok,
        'codegen_consistent': all(
            e_report[p].get('gen_sha') == f_report.get(p, {}).get('gen_sha')
            and f_report.get(p, {}).get('gen_len', 0) > 0 for p in PROBE_FILES),
        'codegen': {os.path.basename(p): f_report.get(p) for p in PROBE_FILES},
        'lexer_sha_restored': sha_cur,
        'verdict': 'ALL_OK' if ok else 'REGRESS',
    }
    json.dump(ev, open(HARNESS + '/_task5_R24_全量回归证据.json', 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('判定：', ev['verdict'])
    print('ALL OK' if ok else 'FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())

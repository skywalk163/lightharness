# -*- coding: utf-8 -*-
"""R38 任务5：agent-tool-presentation（工具展示）pytest。

覆盖（词法 + 结构 + 轻量行为三层）：
  1) 核心模块 src/工具展示.light tokenize 正常（零异常）
  2) 两测试 examples/test_R38_工具展示.light 与 test_R38_集成测试.light tokenize 正常
  3) 导出符号完整（18 项：常量 + 函数 + 类 + 造代理工具展示）
  4) 导入路径健康：模块只依赖 内置核心字典 / 内置核心判型（builtins 层），
     无循环依赖、无对 src/ 其他模块的反向 import（零侵入设计）
  5) 三模式工具过滤逻辑的**符号级验证**（枚举 native/ptc/both 出现 + 注册表.描述表() 调用形态）
  6) 上游 8 契约映射表（用例 1-8）均在 examples/test_R38_集成测试.light 中覆盖

注：运行时行为（建配置/应用/注销/pending 等）已由 examples/test_R38_*.light
    两套 .light 测试覆盖（rc=0，见任务 3 交付）。本文件聚焦 pytest 惯例的
    词法/结构层 + 轻量行为断言。
"""
import os
import re
import sys
import glob

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'src')
STDLIB = os.path.join(ROOT, 'stdlib')
EXAMPLES = os.path.join(ROOT, 'examples')
sys.path.insert(0, os.path.join(ROOT, '..', 'light-merge', 'src'))
import lexer  # noqa: E402

CORE = os.path.join(SRC, '工具展示.light')
UT_TEST = os.path.join(EXAMPLES, 'test_R38_工具展示.light')
IT_TEST = os.path.join(EXAMPLES, 'test_R38_集成测试.light')

# 预期导出（与模块「导出 X」清单严格一致）
EXPECTED_EXPORTS = {
    # 常量
    '工具展示插件名', '工具展示依赖', '工具展示模式表', '运行代码工具名',
    '运行代码工具模式', '部署默认展示',
    # 函数（段落）
    '校验展示模式', '建工具展示配置', '校验工具展示配置', '获取作用域展示',
    '应用工具展示', '注销工具展示', '是否待代码运行时', '等待代码运行时',
    '获取可见工具', '生成工具SDK',
    # 类 + 工厂
    '工具展示注册表代理', '造代理工具展示',
}

# 预期 import 模块（只允许 builtins 层，验证零侵入设计）
EXPECTED_IMPORTS = {'内置核心字典', '内置核心判型'}


def _exports(path):
    names = set()
    for line in open(path, encoding='utf-8-sig', errors='replace'):
        s = line.strip()
        if s.startswith('导出 '):
            for tok in re.split(r'[\s,]+', s[len('导出 '):].strip()):
                if tok:
                    names.add(tok)
    return names


def _module_imports(path):
    out = {}
    for line in open(path, encoding='utf-8-sig', errors='replace'):
        s = line.strip()
        m = re.match(r'^从\s+(\S+)\s+导入\s+(.+)$', s)
        if m:
            mod = m.group(1)
            syms = {t for t in re.split(r'[,\s]+', m.group(2).strip()) if t}
            out.setdefault(mod, set()).update(syms)
    return out


def _tokenize_ok(path):
    text = open(path, encoding='utf-8-sig', errors='replace').read()
    list(lexer.Lexer(text, deterministic=True).tokenize())
    return True


# --------------------------------------------------------------------
# 1) tokenize 正常
# --------------------------------------------------------------------
@pytest.mark.parametrize('path', [CORE, UT_TEST, IT_TEST])
def test_tokenize_正常(path):
    assert _tokenize_ok(path), f'{path} tokenize 应无异常'


# --------------------------------------------------------------------
# 2) 导出符号完整（18 项严格等于）
# --------------------------------------------------------------------
def test_导出符号完整():
    exports = _exports(CORE)
    assert exports == EXPECTED_EXPORTS, (
        f'导出集合不匹配：缺失 {sorted(EXPECTED_EXPORTS - exports)} / '
        f'多余 {sorted(exports - EXPECTED_EXPORTS)}'
    )
    assert len(exports) == 18, f'预期 18 个导出，实际 {len(exports)} 个'


# --------------------------------------------------------------------
# 3) 导入路径健康（只依赖 builtins 层 + 零反向 import）
# --------------------------------------------------------------------
def test_导入仅为builtins层():
    """工具展示.light 只应导入 builtins 层的两个模块——验证零侵入（不依赖任何 src/ 下模块）。"""
    imps = _module_imports(CORE)
    mod_names = set(imps.keys())
    assert mod_names == EXPECTED_IMPORTS, (
        f'工具展示.light 导入模块异常：{sorted(mod_names)}（预期 {sorted(EXPECTED_IMPORTS)}）'
    )


def test_无对既有模块的反向引用():
    """扫描 src/ 下所有既有模块的 import 语句中是否出现「从 工具展示 导入」——
    零，验证零侵入设计（消费者通过代理适配层接入，不反向 import）。
    第40轮注：互举接线.light 是 R40 端到端装配层，设计职责就是接线
    （显式 import 工具展示/系统提示/作用域等模块来串链路），不在此扫描范围；
    本测试仍守护「业务/既有模块不反向 import 工具展示」。"""
    hits = []
    for p in glob.glob(os.path.join(SRC, '*.light')):
        if os.path.basename(p) in ('工具展示.light', '互举接线.light'):
            continue
        text = open(p, encoding='utf-8-sig', errors='replace').read()
        if '从 工具展示 导入' in text:
            hits.append(p)
    assert not hits, f'既有模块不应反向 import 工具展示，但命中：{hits}'


# --------------------------------------------------------------------
# 4) 三模式工具过滤逻辑的符号级验证
# --------------------------------------------------------------------
def test_三模式枚举完整():
    """验证模块源码中明确出现 native/ptc/both 三个模式常量 + 每个分支都定义。"""
    src_text = open(CORE, encoding='utf-8').read()
    # 模式枚举表
    assert '["native", "ptc", "both"]' in src_text, '应含工具展示模式表常量'
    # 每个分支的显式处理（获取可见工具 里的三段 if）
    assert "模式 == \"native\"" in src_text, '应含 native 分支'
    assert "模式 == \"ptc\"" in src_text, '应含 ptc 分支'
    assert "模式 == \"both\"" in src_text, '应含 both 分支'


def test_注册表描述表调用形态正确():
    """工具过滤的三种分支都应调用「工具注册表.描述表()」——验证接入点稳定。"""
    src_text = open(CORE, encoding='utf-8').read()
    # 至少 3 次（native 返回、both 复制追加、ptc 单 run_code、fallback）
    assert src_text.count('工具注册表.描述表()') >= 3, (
        f'工具注册表.描述表() 调用次数应 >= 3，实际 {src_text.count("工具注册表.描述表()")}'
    )


def test_代码运行时条件等待语义保留():
    """ptc/both 在无 codeRuntime 时应 pending（对齐上游 inject=['tools'] 设计）。"""
    src_text = open(CORE, encoding='utf-8').read()
    assert '工具展示依赖 为 ["tools"]' in src_text, 'inject 只声明 tools'
    assert '代码运行时=空' in src_text, '代码运行时必须是可选参数（默认空）'
    assert '待代码运行时' in src_text, '应存在 pending 状态标记'
    assert '等待代码运行时' in src_text, '应存在 等待代码运行时 段落'
    # native 不依赖 codeRuntime
    # 模式 native 分支内不出现 代码运行时 判断
    assert '"native"' in src_text and '运行代码工具名' in src_text


# --------------------------------------------------------------------
# 5) 上游 8 契约映射覆盖（test_R38_集成测试.light 覆盖所有 8 个用例）
# --------------------------------------------------------------------
EXPECTED_CASE_PATTERNS = {
    '#1 只持有 tools 依赖':   ['native', 'inject', 'tools'],
    '#2 作用域隔离':         ['scope', '作用域', '隔离'],
    '#3 both 模式':          ['both', '两者'],
    '#4 HMR 卸载恢复':       ['注销', 'dispose', '恢复'],
    '#5 无 codeRuntime pending': ['pending', '待代码运行时', '无 codeRuntime'],
    '#6 codeRuntime 到达后应用': ['等待代码运行时', '运行时到达', '应用'],
    '#7 mode 必填':          ['mode', '必填', '必须'],
    '#8 disposer 返回':      ['注销工具展示', 'disposer', '句柄'],
}


def test_8契约映射全部覆盖():
    """上游 8 契约用例在 test_R38_集成测试.light 里全部能找到对应关键词。"""
    text = open(IT_TEST, encoding='utf-8').read()
    missing = []
    for case, kws in EXPECTED_CASE_PATTERNS.items():
        if not any(k in text for k in kws):
            missing.append(case)
    assert not missing, f'以下契约在集成测试中未覆盖：{missing}'


def test_集成测试_rc_零通过():
    """集成测试 .light rc=0，且用例数充足（>= 25 个 断言，覆盖 8 契约的具体判据）。"""
    text = open(IT_TEST, encoding='utf-8').read()
    assert_count = text.count('断言')
    assert assert_count >= 25, (
        f'集成测试 断言 语句应 >= 25（8 契约 x 3+ 具体判据 + 自检等），实际 {assert_count}'
    )
    assert '判据通过' in text, '集成测试文件应在末尾有 判据通过 汇总'
    # 直接跑 .light 确认 rc=0
    import subprocess
    r = subprocess.run([sys.executable, '运行.py', 'examples/test_R38_集成测试.light'],
                       cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, f'集成测试 .light rc!=0\nSTDOUT: {r.stdout[-600:]}\nSTDERR: {r.stderr[-300:]}'


# --------------------------------------------------------------------
# 6) 注册表代理类存在且覆写正确方法
# --------------------------------------------------------------------
def test_注册表代理类存在且覆盖描述表():
    """工具展示注册表代理 类应覆写 描述表() 为按作用域过滤（调用 获取可见工具），
    而其他所有方法都透传给 己.包装.X（零侵入消费者）。"""
    text = open(CORE, encoding='utf-8').read()
    assert '类 工具展示注册表代理' in text, '代理类应存在'
    # 覆写点：描述表() 内部调用 获取可见工具(己.作用域ID, 己.包装)
    assert '获取可见工具(己.作用域ID, 己.包装)' in text, '代理.描述表 应调 获取可见工具 过滤'
    # 透传点：至少 5 处 己.包装.X（执行/执行策略/名单/有无/查找/注册/注销/统计/汇总统计/批量执行）
    proxy_delegates = text.count('己.包装.')
    assert proxy_delegates >= 10, (
        f'代理类应至少委托 10 个方法给 己.包装.X，实际 {proxy_delegates} 处'
    )
    # 关键：描述表() 是覆写（不是透传己.包装.描述表）——代理模式的核心
    assert '己.包装.描述表' not in text, (
        '代理.描述表() 是覆写点（调 获取可见工具 过滤），不应再透传给原注册表'
    )
    # 工厂段落存在
    assert '段落 造代理工具展示' in text


# --------------------------------------------------------------------
# 7) 模块命名无冲突（src/ 下唯一）
# --------------------------------------------------------------------
def test_模块名在src下唯一():
    all_src = [os.path.basename(p) for p in glob.glob(os.path.join(SRC, '*.light'))]
    assert all_src.count('工具展示.light') == 1, f'src/ 下 工具展示.light 应唯一，实际出现 {all_src.count("工具展示.light")} 次'
    if os.path.isdir(STDLIB):
        std_names = glob.glob(os.path.join(STDLIB, '工具展示.light'))
        assert not std_names, 'stdlib/ 不应存在同名模块（命名预检查失败）'

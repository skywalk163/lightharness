# -*- coding: utf-8 -*-
"""第46轮：L-166 告警的**注释抑制**验收。

为什么要有抑制
--------------
第45轮把检查器接到真实编译入口后，全语料（791 个 .light）命中 45 条。审定发现其中
一多半是**合法**的同名局部变量（局部夹具、纯函数里的累加器、局部快照）——告警若
每次都报，很快就会淹没真正的 L-165 类缺陷。于是支持：

* 行级  ：赋值行行尾 `# 抑制L166`
* 段落级：段落定义行的**上一行** `# 抑制L166`

本测试守住五件事：
1. 行级抑制生效；
2. 段落级抑制生效；
3. 未加标记的真缺陷**仍然报警**（否则抑制等于把检查器关掉）；
4. **不传 source 时抑制失效** —— 这是最容易踩的坑：AST 不保留注释，调用方不传源码
   抑制就静默失效，表现为「明明写了标记却还在告警」。用测试把这个契约钉死；
5. 端到端：examples/test_R46_抑制标记.light 编译后 stderr 上**恰好 1 条**告警（指向
   『真缺陷』），且声明了 `全局` 的写回真的改到模块级变量。
"""
import os
import subprocess
import sys

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
LIGHT_MERGE = os.environ.get("LIGHT_MERGE", os.path.join(ROOT, "light-merge"))
sys.path.insert(0, os.path.join(LIGHT_MERGE, "src"))
sys.path.insert(0, LIGHT_MERGE)

# 三个段落：行级抑制 / 段落级抑制 / 无标记的真缺陷
SRC = '''设 计数器 为 0

段落 遮蔽_行级:
  设 计数器 为 99。  # 抑制L166
  返回。

# 抑制L166
段落 遮蔽_段落级:
  设 计数器 为 0。
  返回。

段落 真缺陷:
  设 计数器 为 5。
  返回。
'''


def _warns(src, with_source=True):
    from light_parser_v3 import LightParser
    from scope_shadow_check import check_global_shadow
    mod = LightParser().parse(src)
    return check_global_shadow(mod, 't', source=(src if with_source else None))


def test_行级抑制生效():
    ws = _warns(SRC)
    assert not any('遮蔽_行级' in w for w in ws), (
        f"行尾带 `# 抑制L166` 的赋值不应告警\n{ws}")


def test_段落级抑制生效():
    ws = _warns(SRC)
    assert not any('遮蔽_段落级' in w for w in ws), (
        f"段落定义行上一行带 `# 抑制L166` 的整个段落不应告警\n{ws}")


def test_真缺陷仍报警():
    ws = _warns(SRC)
    assert any('真缺陷' in w for w in ws), (
        "未加抑制标记的真缺陷必须仍然告警——否则抑制就是把检查器关了")


def test_抑制条数精确_只报真缺陷():
    assert len(_warns(SRC)) == 1, f"3 个段落里应只报『真缺陷』1 条，实际 {len(_warns(SRC))} 条"


def test_不传source时抑制失效_契约钉死():
    """AST 不保留注释 → 调用方不传源码，抑制就**静默失效**。

    这条测试不是要改变行为，而是把这个易踩的契约固定下来：谁要是把调用点的
    source 参数弄丢了，这里立刻红。
    """
    assert len(_warns(SRC, with_source=False)) == 3, (
        "不传 source 时抑制不生效（3 条全报），这是既定契约；"
        "若此处变化，说明检查器行为变了，需同步更新所有调用点")


def _run_example(env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, os.path.join(BASE, '运行.py'),
         os.path.join(BASE, 'examples', 'test_R46_抑制标记.light')],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=300, cwd=BASE, env=env,
    )


def test_端到端_恰好一条告警且指向真缺陷():
    p = _run_example()
    assert p.returncode == 0, f"用例应绿，实际 rc={p.returncode}\n{p.stderr[-800:]}"
    n = p.stderr.count('L-166')
    assert n == 1, f"预期恰好 1 条 L-166 告警（指向『真缺陷』），实际 {n} 条\n{p.stderr}"
    assert '真缺陷' in p.stderr, f"剩下的这条必须指向『真缺陷』\n{p.stderr}"
    assert 'PASS' in p.stdout and 'L-166' not in p.stdout, "stdout 不能被告警污染"


def test_端到端_环境变量关闭后零告警():
    p = _run_example({'LIGHT_WARN_GLOBAL_SHADOW': '0'})
    assert p.returncode == 0
    assert 'L-166' not in p.stderr, "LIGHT_WARN_GLOBAL_SHADOW=0 时必须静默"

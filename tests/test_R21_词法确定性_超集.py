# -*- coding: utf-8 -*-
"""test_R21_词法确定性_超集.py —— 第21轮 任务4：预扫描 definitions 超集验证（pytest）

验证第21轮任务1（预扫描重构）的核心兼容性要求：**definitions 只增不减**——
对全量 lightharness/examples/*.light，工作区版 `_scan_user_definitions` 的结果
必须是 git d2857dd5 版（第20轮，预扫描重构前）（重构前，=第20轮d2857dd5）结果的超集。

旧版加载方式：git archive d2857dd5 src 提取到临时目录（保证 keywords/tokens 等依赖
模块齐备），子进程内加载并输出 JSON。
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(BASE)
LM = os.environ.get("LIGHT_MERGE", os.path.join(ROOT, "light-merge"))
LM_SRC = os.path.join(LM, "src")

SCAN_CODE = (
    "import sys, json, io, os\n"
    "sys.path.insert(0, %r)\n"
    "from lexer import Lexer\n"
    "files = json.load(open(sys.argv[1], encoding='utf-8'))\n"
    "out = {}\n"
    "for fp in files:\n"
    "    try:\n"
    "        lx = Lexer()\n"
    "        out[fp] = sorted(lx._scan_user_definitions(io.open(fp, encoding='utf-8').read()))\n"
    "    except Exception as exc:\n"
    "        out[fp] = ['<ERROR> ' + str(exc)[:120]]\n"
    "print(json.dumps(out, ensure_ascii=False))\n"
)


def _scan_all(src_dir, files):
    listfile = os.path.join(tempfile.gettempdir(), "r21_defs_%d.json" % os.getpid())
    with open(listfile, "w", encoding="utf-8") as f:
        json.dump(files, f, ensure_ascii=False)
    r = subprocess.run([sys.executable, "-c", SCAN_CODE % src_dir, listfile],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=300)
    os.remove(listfile)
    assert r.returncode == 0, "扫描子进程失败: %s" % r.stderr[-300:]
    return json.loads(r.stdout)


@pytest.fixture(scope="module")
def scan_result():
    files = sorted(
        os.path.join(BASE, "examples", fn)
        for fn in os.listdir(os.path.join(BASE, "examples")) if fn.endswith(".light")
    )
    tmp = tempfile.mkdtemp(prefix="r21_superset_")
    try:
        ar = subprocess.run(["git", "archive", "d2857dd5", "src"], cwd=LM, capture_output=True)
        if ar.returncode != 0:
            pytest.skip("git archive HEAD 不可用")
        tar = os.path.join(tmp, "src.tar")
        with open(tar, "wb") as f:
            f.write(ar.stdout)
        # 用相对名 + cwd 解包：绝对路径（C:\...）传给 GNU tar 会被当成远程主机
        # 规格（`tar: Cannot connect to C: resolve failed`），Git-Bash 下必炸；
        # Windows bsdtar 虽可接受绝对路径，但相对名对两者都成立，故统一用相对名。
        subprocess.run(["tar", "-xf", "src.tar"], check=True, cwd=tmp)
        old = _scan_all(os.path.join(tmp, "src"), files)
        new = _scan_all(LM_SRC, files)
        return files, old, new
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_definitions_superset(scan_result):
    """definitions 只增不减：新版 ⊇ 旧版（逐文件）。

    预期残片收敛豁免：旧版预扫描对嵌套段落的截断残片名（L-152 根因链第3步：
    段名 `内层返回` 被截成 `内层`），新版按层级收集完整名后不再含残片。
    判定：丢失名若为新版任一名字的真前缀（残片收敛）则不计违规，
    其余丢失名才算 definitions 回归。

    R86-A 注释误报豁免（已证良性，非真定义丢失）：
      · test_L020.light / 无法正确注册 —— 仅出现于 L4 注释文本
        「函数名（均含"接收"子串）无法正确注册」；旧版预扫描把注释中的
        「接收」子串误判为形参登记，产生幽灵名。新版忽略注释，正确。
      · test_宿主工具.light / 执行上下文 —— 仅出现于 L32 注释
        「（接收执行上下文）」；同上为注释误报。真名 造执行上下文（L7 导入）
        新旧两版均正确登记，且非「执行上下文」的真前缀豁免能覆盖的形态。
    （归因：R86 路 A 步骤3，实测注释行外零出现 → 断言口径问题，非 lexer 缺陷。）
    """
    files, old, new = scan_result
    # (文件名, 丢失名) → 注释文本误报（旧版把注释中「接收」子串登记为定义名）
    known_comment_false_positives = {
        ('test_L020.light', '无法正确注册'),
        ('test_宿主工具.light', '执行上下文'),
    }
    violations = []
    expected_shrink = []
    for fp in files:
        o, n = set(old.get(fp, [])), set(new.get(fp, []))
        missing = o - n
        if not missing:
            continue
        for m in sorted(missing):
            if (os.path.basename(fp), m) in known_comment_false_positives:
                expected_shrink.append((os.path.basename(fp), m))
            elif any(x != m and x.startswith(m) for x in n):
                expected_shrink.append((os.path.basename(fp), m))
            else:
                violations.append((os.path.basename(fp), m))
    assert not violations, "definitions 出现非残片丢失（%d）: %s" % (
        len(violations), violations[:5])


def test_definitions_growth_on_l152_file(scan_result):
    """L-152 家族文件：新版 definitions 应新增嵌套段落相关名（内层/函数值 等）。"""
    files, old, new = scan_result
    target = [f for f in files if "R21" in os.path.basename(f)]
    assert target, "未找到 R21 系列用例"
    grew = []
    for fp in target:
        o, n = set(old.get(fp, [])), set(new.get(fp, []))
        if n - o:
            grew.append(os.path.basename(fp))
    assert grew, "R21 用例 definitions 未增长（任务1 预扫描重构未生效？）"

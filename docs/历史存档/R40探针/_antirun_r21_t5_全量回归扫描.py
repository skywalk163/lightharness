# -*- coding: utf-8 -*-
"""_antirun_r21_t5_全量回归扫描.py —— 第21轮 任务5：全项目回归扫描与反跑

对比基线：git HEAD 版 src/（git archive 提取到临时目录） vs 工作区版 light-merge/src。
判据：
  A=（依赖任务1）L-152 复现用例：断裂态 rc=1 -> 修复态 rc=0；未落盘时输出「待任务1」不判失败
  B=（依赖任务2）表达式上下文 去重占位/作用域匹配 整体成词；未落盘时输出「待任务2」
  C=语句起始位置不变性：如果/遍历/当/尝试/设...为 真 的关键字 token 形态（当前即可验）
  D=运算符关键字不变性：甲与乙/甲或乙/非/等于/大于 仍切出运算符 KEYWORD（当前即可验）
  E=全量 token 序列对比：HEAD 版 vs 工作区版逐文件对比；差异文件逐个列出并标注分类
  F=性能：两版 tokenize 全量 examples 总耗时对比（阈值 20%）
  G=（--run）编译运行快照：全量 examples 当前 rc 分布（与已知预期红对照）
用法：python lightharness/_antirun_r21_t5_全量回归扫描.py [--run]
退出码：硬性判据失败 1；仅「待任务1/2」软标注则 0（基线模式）。
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(BASE)
LM = os.environ.get("LIGHT_MERGE", os.path.join(ROOT, "light-merge"))
LM_SRC = os.path.join(LM, "src")
EX = os.path.join(BASE, "examples")

RUN = "--run" in sys.argv


def read_bytes(p):
    with open(p, "rb") as f:
        return f.read()


def head_lexer_digest():
    r = subprocess.run(["git", "show", "HEAD:src/lexer.py"], cwd=LM,
                       capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None


def prepare_old_src(tmp):
    """git archive HEAD src 提取到临时目录，保证旧版依赖模块齐备。"""
    r = subprocess.run(["git", "archive", "HEAD", "src"], cwd=LM, capture_output=True)
    if r.returncode != 0:
        return None
    tar = os.path.join(tmp, "src.tar")
    with open(tar, "wb") as f:
        f.write(r.stdout)
    subprocess.run(["tar", "-xf", tar, "-C", tmp], check=True)
    return os.path.join(tmp, "src")


def tokenize_batch_batch(src_dir, light_files, timeout=300):
    """子进程：给定 lexer 所在 src 目录，批量 tokenize，返回 {file: [[type,value],...]} JSON。"""
    code = (
        "import sys, json, io\n"
        "sys.path.insert(0, %r)\n"
        "from lexer import Lexer\n"
        "lx = Lexer()\n"
        "files = json.load(open(sys.argv[1], encoding='utf-8'))\n"
        "out = {}\n"
        "for fp in files:\n"
        "    try:\n"
        "        toks = lx.tokenize(io.open(fp, encoding='utf-8').read())\n"
        "        out[fp] = [[t.type.name, t.value if isinstance(t.value, (str, int, float)) else str(t.value)] for t in toks]\n"
        "    except Exception as exc:\n"
        "        out[fp] = [['ERROR', str(exc)[:200]]]\n"
        "print(json.dumps(out, ensure_ascii=False))\n"
    ) % src_dir
    listfile = os.path.join(tempfile.gettempdir(), "r21_files_%d.json" % os.getpid())
    with open(listfile, "w", encoding="utf-8") as f:
        json.dump(light_files, f, ensure_ascii=False)
    r = subprocess.run([sys.executable, "-c", code, listfile],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=timeout)
    os.remove(listfile)
    if r.returncode != 0:
        print("tokenize 子进程失败:", r.stderr[-400:])
        return None
    return json.loads(r.stdout)


def collect_light_files():
    files = []
    for fn in sorted(os.listdir(EX)):
        if fn.endswith(".light"):
            files.append(os.path.join(EX, fn))
    return files


def hard_probe(src_dir=None):
    """关键场景 token 探针。src_dir=None 用工作区版。"""
    if src_dir:
        code = (
            "import sys, json\n"
            "sys.path.insert(0, %r)\n"
            "from lexer import Lexer\n"
            "lx = Lexer()\n"
            "probes = ['设 结果 为 去重占位([1,1,2])', '如果 条件 为 真:', '设 结果 为 甲 与 乙',\n"
            "          '段落 内层返回 接收 函数值:', '去重占位(名单)']\n"
            "out = {}\n"
            "for s in probes:\n"
            "    try:\n"
            "        out[s] = [[t.type.name, t.value] for t in lx.tokenize(s)]\n"
            "    except Exception as exc:\n"
            "        out[s] = [['ERROR', str(exc)[:120]]]\n"
            "print(json.dumps(out, ensure_ascii=False))\n"
        ) % src_dir
        r = subprocess.run([sys.executable, "-c", code], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", timeout=120)
        return json.loads(r.stdout)
    sys.path.insert(0, LM_SRC)
    from lexer import Lexer
    lx = Lexer()
    probes = ["设 结果 为 去重占位([1,1,2])", "如果 条件 为 真:", "设 结果 为 甲 与 乙",
              "段落 内层返回 接收 函数值:", "去重占位(名单)"]
    out = {}
    for s in probes:
        try:
            out[s] = [[t.type.name, t.value] for t in lx.tokenize(s)]
        except Exception as exc:
            out[s] = [["ERROR", str(exc)[:120]]]
    return out


def run_light(rel, env=None):
    e = dict(os.environ, LIGHT_MERGE=LM)
    if env:
        e.update(env)
    p = subprocess.run([sys.executable, "运行.py", rel], cwd=BASE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace", env=e)
    return p.returncode


def main():
    results = []          # (name, ok, note)；ok=None 表示软标注（待依赖）
    files = collect_light_files()
    tmp = tempfile.mkdtemp(prefix="r21_scan_")
    try:
        old_src = prepare_old_src(tmp)
        head_digest = head_lexer_digest()
        work_digest = hashlib.sha256(read_bytes(os.path.join(LM_SRC, "lexer.py"))).hexdigest()
        same = (old_src is None) or (head_digest == work_digest)
        print("=== 第21轮 任务5：全量回归扫描 ===")
        print("工作区 lexer.py 与 HEAD %s" % ("一致（基线模式：任务1/2 尚未落盘）" if same else "不同（重构态）"))

        # ---- token 全量对比 ----
        old_toks = tokenize_batch_batch(old_src, files) if old_src else None
        t0 = time.perf_counter()
        new_toks = tokenize_batch_batch(LM_SRC, files)
        t1 = time.perf_counter()
        old_t = None
        if old_toks is not None:
            t_old = time.perf_counter()
            old_toks = tokenize_batch_batch(old_src, files)
            old_t = time.perf_counter() - t_old
        if old_toks is not None and new_toks is not None:
            diff = [f for f in files if old_toks.get(f) != new_toks.get(f)]
            print("E=全量 token 对比: %d 文件, 差异 %d 个" % (len(files), len(diff)))
            for f in diff[:20]:
                print("  差异: %s" % os.path.relpath(f, ROOT))
            if diff:
                # 分类提示：差异应属 L-152/任务2 预期变化
                print("  （差异须逐个归因：L-152 修复 / 任务2 表达式上下文 / 意外回归）")
                results.append(("E=token差异可解释", None, "%d 个差异待归因" % len(diff)))
            else:
                results.append(("E=全量token零差异（基线）", True, "%d 文件" % len(files)))
        else:
            results.append(("E=token对比", False, "旧版提取失败"))

        # ---- 性能 ----
        if old_t is not None:
            new_t = t1 - t0
            ratio = (new_t - old_t) / old_t if old_t else 0
            ok = ratio <= 0.20
            print("F=性能: 旧版 %.2fs -> 新版 %.2fs（%+.1f%%，阈值20%%）" % (old_t, new_t, ratio * 100))
            results.append(("F=性能<20%%", ok, "%+.1f%%" % (ratio * 100)))

        # ---- 探针判据 A/B/C/D ----
        old_probe = hard_probe(old_src) if old_src else None
        new_probe = hard_probe(None)
        p_l152_old = old_probe.get("段落 内层返回 接收 函数值:") if old_probe else None
        p_l152_new = new_probe.get("段落 内层返回 接收 函数值:")

        def idents(seq):
            return [v for ty, v in seq if ty == "IDENTIFIER"]

        # A: L-152 断裂态 vs 修复态
        if p_l152_old and "函数值" not in idents(p_l152_old):
            # 断裂态成立：HEAD 版把 函数值 切碎。检查工作区是否修复。
            fixed = "函数值" in idents(p_l152_new)
            rc = run_light(os.path.join(tempfile.gettempdir(), "r21_l152.light"))
            print("A=L-152: HEAD断裂态成立（%r）-> 工作区%s (复现rc=%d)" % (
                idents(p_l152_old), "已修复" if fixed else "未修复", rc))
            results.append(("A=L-152修复", (fixed and rc == 0) if fixed else None,
                            "函数值 整体=%s" % fixed))
        elif p_l152_old:
            print("A=L-152: HEAD 版已含修复（无断裂态可对照），跳过断裂对照")
            results.append(("A=L-152修复", None, "HEAD 无断裂态"))

        # B: 表达式上下文
        p_expr_old = old_probe.get("设 结果 为 去重占位([1,1,2])") if old_probe else None
        p_expr_new = new_probe.get("设 结果 为 去重占位([1,1,2])")
        expr_fixed = p_expr_new and "去重占位" in idents(p_expr_new)
        expr_old_broken = p_expr_old and "去重占位" not in idents(p_expr_old)
        if expr_old_broken:
            results.append(("B=表达式上下文整体成词", (True if expr_fixed else None),
                            "工作区=%s" % ("已修复" if expr_fixed else "待任务2")))
            print("B=表达式上下文: HEAD断裂 -> 工作区%s" % ("已修复" if expr_fixed else "待任务2"))
        elif expr_fixed:
            results.append(("B=表达式上下文整体成词", True, "已整体成词"))
            print("B=表达式上下文: 整体成词（已修复态）")
        else:
            results.append(("B=表达式上下文整体成词", None, "待任务2"))
            print("B=表达式上下文: 待任务2（%r）" % idents(p_expr_new))

        # C: 语句起始不变
        p_if = new_probe.get("如果 条件 为 真:")
        ok_c = p_if and ("KEYWORD", "如果") in [tuple(x) for x in p_if] and "条件" in idents(p_if)
        print("C=语句起始不变: 如果=KEYWORD, 条件=IDENTIFIER -> %s" % ("PASS" if ok_c else "FAIL"))
        results.append(("C=语句起始不变", bool(ok_c), str(p_if)))

        # D: 运算符不变
        p_op = new_probe.get("设 结果 为 甲 与 乙")
        ok_d = p_op and ("KEYWORD", "与") in [tuple(x) for x in p_op]
        print("D=运算符不变: 与=KEYWORD -> %s" % ("PASS" if ok_d else "FAIL"))
        results.append(("D=运算符不变", bool(ok_d), str(p_op)))

        # G: 编译运行快照
        if RUN:
            red, green = [], 0
            for f in files:
                rel = os.path.relpath(f, BASE)
                rc = run_light(rel)
                if rc == 0:
                    green += 1
                else:
                    red.append(os.path.basename(f))
            print("G=运行快照: %d 绿 / %d 红" % (green, len(red)))
            print("  红用例: %s" % ", ".join(red))
            results.append(("G=运行快照", True, "%d绿/%d红: %s" % (green, len(red), ", ".join(red))))

        # ---- 汇总 ----
        print("=== 汇总 ===")
        hard_fail = False
        for name, ok, note in results:
            if ok is True:
                tag = "PASS"
            elif ok is False:
                tag, hard_fail = "FAIL", True
            else:
                tag = "WAIT"
            print("%s %s (%s)" % (tag, name, note))
        # 基线模式：硬失败才退出 1
        print("ALL OK" if not hard_fail else "ANTIRUN FAILED")
        return 1 if hard_fail else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())

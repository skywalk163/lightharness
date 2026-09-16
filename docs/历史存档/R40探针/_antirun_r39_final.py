# -*- coding: utf-8 -*-
"""R39 任务5 最终反跑 + 回归验证。

R39 新增 2 个核心模块 + 5 个测试文件：
  src/作用域.light
  src/系统提示.light
  examples/test_R39_{作用域,作用域存储,系统提示,系统提示工具排序变量插值,集成测试}.light

本脚本覆盖：
  阶段0  全量基准（5 个测试文件全部 rc=0）
  阶段1  集成测试值反变异（§7 联动断链 → 必须红）
  阶段2  系统提示多 complete 冲突（负向）
  阶段3  作用域循环检测反向断链
  阶段4  新模块 tokenize 回归（词法 + 语法）
  阶段5  导入路径检查（作用域/系统提示/代理默认模型 三环联通）
  阶段6  还原基准复跑（确保反跑过程未污染 src/）

纪律：
  - 临时变异文件仅写仓库根目录 _red_tmp_r39_*.light
  - 只读 src/ 与 examples/
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
PY = r"G:\dswork\duan-light-merge\light-merge\.venv\Scripts\python.exe"

TESTS = [
    os.path.join(ROOT, "examples", "test_R39_作用域.light"),
    os.path.join(ROOT, "examples", "test_R39_作用域存储.light"),
    os.path.join(ROOT, "examples", "test_R39_系统提示.light"),
    os.path.join(ROOT, "examples", "test_R39_系统提示工具排序变量插值.light"),
    os.path.join(ROOT, "examples", "test_R39_集成测试.light"),
]

NEW_MODULES = [
    os.path.join(ROOT, "src", "作用域.light"),
    os.path.join(ROOT, "src", "系统提示.light"),
]

# (临时文件名, 基准文件, [(原名, 变异后)], 期望 rc!=0, 期望输出关键词, 判据名)
CASES = [
    # ---- 阶段1：集成测试 §7 联动断链（改期望值 → 红）----
    (
        "_red_tmp_r39_i7_noA.light",
        TESTS[-1],
        [('  必等(提示A.查找("仅 A 可见") >= 0, 真, "7.1b")',
          '  必等(提示A.查找("仅 A 可见") >= 0, 假, "7.1b")')],
        ["断言失败"],
        "集成 §7.1b 域A专属期望值改反 → 必须红",
    ),
    (
        "_red_tmp_r39_i7_noGlobal.light",
        TESTS[-1],
        [('  必等(提示A.查找("你是光明 Agent") >= 0, 真, "7.1")',
          '  必等(提示A.查找("你是光明 Agent") >= 0, 假, "7.1")')],
        ["断言失败"],
        "集成 §7.1 全局身份期望值改反 → 必须红",
    ),
    (
        "_red_tmp_r39_i7_noB_on_B.light",
        TESTS[-1],
        [('  必等(提示B.查找("仅 B 可见") >= 0, 真, "7.2b")',
          '  必等(提示B.查找("仅 B 可见") >= 0, 假, "7.2b")')],
        ["断言失败"],
        "集成 §7.2b 域B专属期望值改反 → 必须红",
    ),
    # ---- 阶段2：多 complete 冲突（改 complete 标记 → 冲突消失 → 原测试的 1→0 红）----
    (
        "_red_tmp_r39_s5_noCompleteConflict.light",
        TESTS[-1],
        [('  注册节(reg2, "另完整", 600, "另一完整", 真)',
          '  注册节(reg2, "另完整", 600, "另一完整", 假)')],
        ["断言失败"],
        "集成 §5.2 去掉第二个 complete → 本应抛错却没抛 → 必须红",
    ),
    # ---- 阶段3：循环检测反向断链 ----
    (
        "_red_tmp_r39_s1_noCycle.light",
        TESTS[-1],
        [('    绑定父作用域(k1, k3)',
          '    绑定父作用域(k1, 建作用域键("新"))')],
        ["断言失败"],
        "集成 §1.3 循环键换成新键 → 不抛 → 必须红",
    ),
    # ---- 阶段3b：变量插值断链（把 {{who}} 换成不存在的 {{xxxwho}}）----
    (
        "_red_tmp_r39_s6_noVar.light",
        TESTS[-1],
        [('  必等(提示.查找("你好 光明") >= 0, 真, "6.5")',
          '  必等(提示.查找("你好 {{xxxwho}}") >= 0, 真, "6.5")')],
        ["断言失败"],
        "集成 §6.5 变量插值断链 → 必须红",
    ),
]


def run_light(path):
    p = subprocess.run([PY, "运行.py", path], cwd=ROOT,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def run_tokenize(path):
    """独立词法+语法回归：用 run_light 的 parser 跑一遍."""
    # 直接复用 运行.py 的 loader 做 dry-run：tokenize + parse
    # 执行 运行.py 只要不 RuntimeError 就算通过
    return run_light(path)


def main():
    ok = True

    # ============ 阶段0：全量基准 ============
    print("=" * 60)
    print("阶段0：全量基准（必须全部 rc=0）")
    print("=" * 60)
    for f in TESTS:
        rc, out = run_light(f)
        tag = "GREEN" if rc == 0 else "RED"
        print("[%s] rc=%d  %s" % (tag, rc, os.path.basename(f)))
        if rc != 0:
            ok = False
            print(out[:1000])

    # ============ 阶段1-3：逐条变异 → 必须 rc!=0 且命中关键词 ============
    print("\n" + "=" * 60)
    print("阶段1-3：变异反跑（必须全部红）")
    print("=" * 60)
    for name, base, subs, want_kw, label in CASES:
        src = open(base, encoding="utf-8").read()
        mutated = src
        hit_anchor = True
        for old, new in subs:
            if old not in mutated:
                print("[MUTATE-MISS] %s" % label)
                print("    未找到锚点：%r" % old[:80])
                hit_anchor = False
                ok = False
                break
            mutated = mutated.replace(old, new, 1)
        if not hit_anchor:
            continue
        tmp = os.path.join(ROOT, name)
        try:
            with open(tmp, "w", encoding="utf-8", newline="") as fh:
                fh.write(mutated)
            rc, out = run_light(tmp)
            hit_kw = any(k in out for k in want_kw)
            good = (rc != 0) and hit_kw
            print("[%s] rc=%d kw=%s  %s" % ("PASS" if good else "FAIL", rc, hit_kw, label))
            if not good:
                ok = False
                print(out[:800])
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    # ============ 阶段4：新模块词法+语法回归 ============
    print("\n" + "=" * 60)
    print("阶段4：新模块 tokenize/parse 回归")
    print("=" * 60)
    for f in NEW_MODULES:
        rc, out = run_tokenize(f)
        # 模块本身没有顶层执行，rc!=0 表示解析失败
        tag = "PARSE-OK" if rc == 0 else "PARSE-FAIL"
        print("[%s] rc=%d  %s" % (tag, rc, os.path.basename(f)))
        if rc != 0:
            ok = False
            print(out[:800])

    # ============ 阶段5：导入路径三环检查 ============
    print("\n" + "=" * 60)
    print("阶段5：导入路径三环检查")
    print("=" * 60)
    # 动态生成一个临时 light 程序来串联三个模块
    glue = (
        "# _tmp_r39_glue.light —— 作用域 / 系统提示 / 代理默认模型 三环联通检查\n"
        "从 作用域 导入 建作用域键, 建上下文, 扩展作用域上下文, 作用域层组, 造作用域层组\n"
        "从 系统提示 导入 建系统提示注册表, 注册节, 注册变量, 组装系统提示, 渲染提示\n"
        "从 代理默认模型 导入 建默认模型配置, 取当前选择\n"
        "段落 动作 接收 层:\n"
        "  层.命名.插入('身份', '你是 light agent')\n"
        "  返回 空\n"
        "段落 主:\n"
        "  设 组 为 造作用域层组()\n"
        "  设 根 为 建上下文(空)\n"
        "  设 域键 为 建作用域键('域')\n"
        "  设 域上下文 为 扩展作用域上下文(根, 域键)\n"
        "  组.附着(域上下文, 动作)\n"
        "  设 reg 为 建系统提示注册表()\n"
        "  设 选择 为 取当前选择(建默认模型配置('p', 'm'))\n"
        "  注册变量(reg, 'provider', 选择['提供者'])\n"
        "  注册变量(reg, 'model', 选择['模型'])\n"
        "  注册节(reg, 'greet', 50, 'hello {{provider}}/{{model}}')\n"
        "  设 提示 为 渲染提示(组装系统提示(reg))\n"
        "  如果 提示.查找('p/m') < 0:\n"
        "    抛出 新建 错误('三环联通失败：变量插值未生效')\n"
        "  打印('三环联通 OK')\n"
        "主()\n"
    )
    glue_path = os.path.join(ROOT, "_red_tmp_r39_glue.light")
    try:
        with open(glue_path, "w", encoding="utf-8", newline="") as fh:
            fh.write(glue)
        rc, out = run_light(glue_path)
        good = (rc == 0) and ("三环联通 OK" in out)
        print("[%s] rc=%d  三环联通（作用域→系统提示→默认模型）" %
              ("PASS" if good else "FAIL", rc))
        if not good:
            ok = False
            print(out[:1200])
    finally:
        if os.path.exists(glue_path):
            os.remove(glue_path)

    # ============ 阶段6：还原基准复跑 ============
    print("\n" + "=" * 60)
    print("阶段6：还原基准复跑（确保反跑未污染 src/）")
    print("=" * 60)
    for f in TESTS:
        rc, _ = run_light(f)
        tag = "RESTORE-GREEN" if rc == 0 else "RESTORE-RED"
        print("[%s] rc=%d  %s" % (tag, rc, os.path.basename(f)))
        if rc != 0:
            ok = False

    # ============ 汇总 ============
    print("\n" + "=" * 60)
    print("R39 任务5 反跑 + 回归验证：%s" % ("ALL PASS" if ok else "FAIL"))
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

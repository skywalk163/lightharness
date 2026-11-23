# -*- coding: utf-8 -*-
"""T-0442：lightharness 工具层 5 处缺陷的回归门禁。

每条缺陷一组用例，全部自成场景（临时目录 + 本地解释器子命令），
不依赖外网、真实凭证、git 远端或仓库残留：

  缺陷 1  search_files 内容模式「匹配行」恒空        → test_缺陷1_*
  缺陷 2  bash 执行失败时退出码误报 0                → test_缺陷2_*
  缺陷 3  超时被杀后无任何说明、部分输出丢失         → test_缺陷3_*
  缺陷 4  交互式命令静默挂起、超时不可配             → test_缺陷4_*
  缺陷 5  同一条 bash 调用疑似执行两次、输出被吞      → test_缺陷5_*

判据走 .light 侧真实工具（子进程 python 运行.py + 驱动脚本），
另加一条 Python 侧断言锁住 stdlib/外部命令 的 stdin=DEVNULL 机制。
驱动里的子命令一律用 `$T0442_PY`（由测试注入 sys.executable），
不写死 python/python3，Windows 与 FreeBSD/Linux 同一份脚本都能跑。
"""
import importlib.util
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
STDLIB = os.path.join(ROOT, 'stdlib')
TIMEOUT_SEC = 180

# 所有驱动共用的「解释器取用」前导：子命令一律走 $T0442_PY，躲开 python/python3 差异
_PY = '''  设 解释器 为 环境变量("T0442_PY", "python")
'''


def _run_driver(tmp_path, name, source, harness_root=None):
    """把驱动脚本写到临时目录 → 子进程跑 运行.py → 返回 CompletedProcess。"""
    path = tmp_path / name
    path.write_text(source, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['T0442_PY'] = sys.executable
    if harness_root is not None:
        env['HARNESS_ROOT'] = str(harness_root)
    return subprocess.run(
        [sys.executable, RUNNER, str(path)],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
        errors='replace', timeout=TIMEOUT_SEC, env=env,
    )


def _kv(stdout):
    """把驱动打印的 KEY=<JSON> 收成字典。"""
    out = {}
    for line in stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def _json(kv, key):
    assert key in kv, f'驱动没有打印 {key}，实际输出：{list(kv)}'
    return json.loads(kv[key])


def _ok(proc, what):
    assert proc.returncode == 0, (
        f'{what} 驱动应 rc=0，实际 {proc.returncode}\n'
        f'--- stdout ---\n{proc.stdout[-1500:]}\n--- stderr ---\n{proc.stderr[-1500:]}')


# ---------------------------------------------------------------------------
# 缺陷 1：内容搜索「匹配行」必须带行号与命中文本；文件名模式仍为空串
# ---------------------------------------------------------------------------
def test_缺陷1_内容搜索匹配行带行号且非空(tmp_path):
    root = tmp_path / 'root'
    (root / 'sub').mkdir(parents=True)
    (root / 'sub' / 'hit.txt').write_text(
        'first line\nsecond line\n  needle-alpha 这里是命中行\nlast line\n',
        encoding='utf-8')
    (root / 'other.txt').write_text('nothing here\n', encoding='utf-8')

    driver = '''
从 工具_搜索文件 导入 搜索文件处理

段落 主程():
  设 内容 为 搜索文件处理(["模式": "内容", "查询": "needle-alpha", "路径": "."])
  打印("内容=" + 序列化JSON(内容))
  设 名 为 搜索文件处理(["模式": "文件名", "查询": "hit.txt", "路径": "."])
  打印("文件名=" + 序列化JSON(名))
  设 无 为 搜索文件处理(["模式": "内容", "查询": "zzz-绝对不存在的词", "路径": "."])
  打印("无命中=" + 序列化JSON(无))
主程()
'''
    proc = _run_driver(tmp_path, '_d1.light', driver, harness_root=root)
    _ok(proc, '缺陷1')
    kv = _kv(proc.stdout)

    内容 = _json(kv, '内容')
    结果 = 内容['结果']
    assert len(结果) == 1, f'应只命中 hit.txt，实际 {结果}'
    assert 结果[0]['路径'].replace('\\', '/').endswith('sub/hit.txt')
    匹配行 = 结果[0]['匹配行']
    assert 匹配行 != '', '内容模式命中时「匹配行」不得为空（T-0442 缺陷 1）'
    assert 匹配行.startswith('3: '), f'匹配行需带 1 基行号，实际 {匹配行!r}'
    assert 'needle-alpha' in 匹配行

    # 文件名模式语义不变：匹配行仍是空串
    名 = _json(kv, '文件名')
    assert len(名['结果']) == 1
    assert 名['结果'][0]['匹配行'] == ''

    # 无命中：结果为空表
    assert _json(kv, '无命中')['结果'] == []


# ---------------------------------------------------------------------------
# 缺陷 2：退出码如实透传；stderr 有 shell 层错误而 rc=0 时按失败上报
# ---------------------------------------------------------------------------
def test_缺陷2_退出码透传且shell层错误不报喜(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()

    driver = '''
从 工具_bash 导入 bash处理, 造bash工具定义

段落 主程():
''' + _PY + '''  设 正常 为 bash处理(["命令": "\\"" + 解释器 + "\\" -c \\"import sys; sys.exit(7)\\""])
  打印("正常=" + 序列化JSON(正常))
  设 假成功 为 bash处理(["命令": "\\"" + 解释器 + "\\" -c \\"import sys; sys.stderr.write('sh: cannot create /tmp/probe.light: Permission denied')\\""])
  打印("假成功=" + 序列化JSON(假成功))
  设 告警 为 bash处理(["命令": "\\"" + 解释器 + "\\" -c \\"import sys; sys.stderr.write('warning: deprecated api')\\""])
  打印("告警=" + 序列化JSON(告警))
  设 模式 为 造bash工具定义()["parameters"]
  打印("模式=" + 序列化JSON(模式))
主程()
'''
    proc = _run_driver(tmp_path, '_d2.light', driver, harness_root=root)
    _ok(proc, '缺陷2')
    kv = _kv(proc.stdout)

    正常 = _json(kv, '正常')
    assert 正常['退出码'] == 7, f'退出码应如实透传 7，实际 {正常}'

    假成功 = _json(kv, '假成功')
    assert 假成功['退出码'] != 0, (
        f'stderr 有 shell 层错误但退出码报 0（缺陷 2），实际 {假成功}')
    assert '工具层判定' in 假成功['错误']
    assert 'cannot create' in 假成功['错误'], '原始 stderr 必须保留给代理'

    告警 = _json(kv, '告警')
    assert 告警['退出码'] == 0, 'stderr 只有普通告警、退出码 0 时不得误判失败'
    assert 'warning: deprecated api' in 告警['错误']

    # 缺陷 4：超时上限可由调用方指定 → schema 必须暴露「超时」参数
    assert '超时' in _json(kv, '模式')['properties']


# ---------------------------------------------------------------------------
# 缺陷 3：超时被杀必须说明原因 + 带上被杀前的部分输出
# ---------------------------------------------------------------------------
def test_缺陷3_超时明确说明且保留部分输出(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    driver = '''
从 工具_bash 导入 bash处理

段落 主程():
''' + _PY + '''  设 超时 为 bash处理(["命令": "\\"" + 解释器 + "\\" -c \\"import sys,time; sys.stdout.write('partial-out'); sys.stdout.flush(); time.sleep(8)\\"", "超时": 2])
  打印("超时=" + 序列化JSON(超时))
主程()
'''
    t0 = time.time()
    proc = _run_driver(tmp_path, '_d3.light', driver, harness_root=root)
    elapsed = time.time() - t0
    _ok(proc, '缺陷3')
    kv = _kv(proc.stdout)

    被超时 = _json(kv, '超时')
    assert 被超时['退出码'] != 0, f'超时应返回非 0 退出码，实际 {被超时}'
    assert '超时' in 被超时['错误'] and '终止' in 被超时['错误'], (
        f'超时说明缺失「超时被终止」字样，实际 {被超时["错误"]!r}')
    assert '2' in 被超时['错误'], '错误说明里应写明实际超时秒数'
    assert 被超时['输出'] == 'partial-out', (
        f'被杀前已产生的 stdout 不得丢失，实际 {被超时["输出"]!r}')
    # 编译/启动开销之外，2 秒超时必须真的在 2 秒左右生效（旧实现要等 8 秒 sleep 结束）
    assert elapsed < 12, f'超时应按调用方给的 2 秒生效，实际耗时 {elapsed:.1f}s'


# ---------------------------------------------------------------------------
# 缺陷 4：交互式命令不挂死，且错误里给出「等待终端输入」提示
# ---------------------------------------------------------------------------
def test_缺陷4_交互式命令立即失败并给出等待输入提示(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    driver = '''
从 工具_bash 导入 bash处理

段落 主程():
''' + _PY + '''  设 交互 为 bash处理(["命令": "\\"" + 解释器 + "\\" -c \\"import sys; sys.stderr.write('Username for repro: '); input()\\""])
  打印("交互=" + 序列化JSON(交互))
主程()
'''
    t0 = time.time()
    proc = _run_driver(tmp_path, '_d4.light', driver, harness_root=root)
    elapsed = time.time() - t0
    _ok(proc, '缺陷4')
    kv = _kv(proc.stdout)

    交互 = _json(kv, '交互')
    assert 交互['退出码'] != 0, f'等 stdin 的命令应立刻失败而不是成功，实际 {交互}'
    assert '等待终端输入' in 交互['错误'], (
        f'错误字段必须提示「等待终端输入」，实际 {交互["错误"]!r}')
    assert 'EOF when reading a line' in 交互['错误'], '原始 stderr 必须保留'
    assert elapsed < 30, f'交互式命令不得挂到 30 秒超时，实际耗时 {elapsed:.1f}s'


def test_缺陷4_外部命令用DEVNULL关闭子进程stdin():
    """机制层断言：stdlib/外部命令 起子进程必须显式传 stdin=DEVNULL（不继承父进程 stdin）。"""
    spec = importlib.util.spec_from_file_location(
        '_t0442_外部命令', os.path.join(STDLIB, '外部命令.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    实际 = {}
    原始 = mod.subprocess.Popen

    def 记录(*args, **kwargs):
        实际.clear()
        实际.update(kwargs)
        return 原始(*args, **kwargs)

    mod.subprocess.Popen = 记录
    try:
        r = mod.执行命令([sys.executable, '-c', 'print(1)'], True, None, None, 10)
    finally:
        mod.subprocess.Popen = 原始

    assert 实际.get('stdin') == mod.subprocess.DEVNULL, (
        f'执行命令 必须传 stdin=subprocess.DEVNULL，禁止继承父进程 stdin'
        f'（缺陷 4）；实际 kwargs={实际}')
    assert r.返回码 == 0 and r.标准输出.strip() == '1'


# ---------------------------------------------------------------------------
# 缺陷 5：同一条 bash 调用只执行一次，每次返回自己的输出与副作用
# ---------------------------------------------------------------------------
def test_缺陷5_连续调用单次执行无重复副作用(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    driver = '''
从 工具_bash 导入 bash处理

段落 主程():
''' + _PY + '''  设 序号 为 0
  当 序号 < 10:
    设 结果 为 bash处理(["命令": "\\"" + 解释器 + "\\" -c \\"open('count.txt','a').write('x'); print('call-" + 转字符串(序号) + "')\\""])
    打印("调用_" + 转字符串(序号) + "=" + 序列化JSON(结果))
    设 序号 为 序号 + 1
  设 首 为 bash处理(["命令": "\\"" + 解释器 + "\\" -c \\"import os; os.mkdir('once_dir')\\""])
  打印("mkdir1=" + 序列化JSON(首))
  设 次 为 bash处理(["命令": "\\"" + 解释器 + "\\" -c \\"import os; os.mkdir('once_dir')\\""])
  打印("mkdir2=" + 序列化JSON(次))
主程()
'''
    proc = _run_driver(tmp_path, '_d5.light', driver, harness_root=root)
    _ok(proc, '缺陷5')
    kv = _kv(proc.stdout)

    for i in range(10):
        结果 = _json(kv, f'调用_{i}')
        assert 结果['退出码'] == 0, f'第 {i} 次调用应成功，实际 {结果}'
        assert f'call-{i}' in 结果['输出'], (
            f'第 {i} 次调用必须返回这一次自己的输出（缺陷 5：成功输出被吞），实际 {结果}')

    # 每次调用只能追加 1 个字符：多于 10 说明同一调用被执行了多次
    文本 = (root / 'count.txt').read_text(encoding='utf-8')
    assert len(文本) == 10, (
        f'10 次调用应只产生 10 个副作用字符，实际 {len(文本)}（疑似重复执行）')

    mkdir1 = _json(kv, 'mkdir1')
    mkdir2 = _json(kv, 'mkdir2')
    assert mkdir1['退出码'] == 0, f'首次 mkdir 应成功，实际 {mkdir1}'
    assert (root / 'once_dir').is_dir()
    assert mkdir2['退出码'] != 0, (
        f'第二次 mkdir 必须失败（非幂等命令不得被工具层重试），实际 {mkdir2}')

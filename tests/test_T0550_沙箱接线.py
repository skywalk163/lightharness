# -*- coding: utf-8 -*-
"""T-0550：把「沙箱统一」接进 bash 工具生产路径。

本卡第一原则是 fail-closed：沙箱不可用就报错，绝不允许降级直跑。
所以这里的用例全部是**行为级红线**，不是「看起来接上了」的结构快照：

  1) 接线断言：mock 沙箱统一.运行，bash 必须真的调它（命令数组/策略/超时/工作目录齐全）；
     若有人把执行改回 外部命令/裸建进程树，mock 不会被调用 → 本用例立红。
  2) fail-closed：mock 后端探测「无可用」，bash 必须返回错误且**底层 shell 未执行**
     （用重定向探针文件证明命令真没跑）。反跑锚点：catch 后裸跑 → 探针文件出现 → 立红。
  3) 逃生口：danger-full-access 下命令真执行，且约束 argv 为原始命令（无包装）。
  4) 策略来源：会话级 sandboxMode > 全局默认 > 默认 read-only；
     会话读取器（T-0551 事件投影）优先于会话表。
  5) 杀树并存：有调用上下文时树句柄回绑，预停止 → 命令被强杀且 [命令已被用户停止]。

驱动一律走 运行.py 子进程（与本仓既有 Light 行为测试同口径），
命令只用 echo / sleep / ping 这类无空格路径的写法，Windows 与 FreeBSD 共用一份脚本。
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
BASH_LIGHT = os.path.join(ROOT, 'src', '工具_bash.light')
TIMEOUT_SEC = 240

BOOT = '''
从 工具_bash 导入 bash处理, 取会话沙箱策略, 设沙箱运行器, 设全局沙箱模式, 设会话沙箱模式, 设会话沙箱读取器, 取bash沙箱日志
从 任务控制 导入 开运行, 关运行, 设置调用上下文, 登记工具, 请求停止, 取工具, 清调用上下文
从 沙箱统一 导入 设探测提供者, 取沙箱执行日志, 约束
从 沙箱探测 导入 沙箱不可用错误
从 进程树 导入 执行结果
从 内置核心字典 导入 字典获取
从 内置核心列表 导入 列表追加
从 JSON 导入 序列化JSON
'''


def _drive(tmp_path, name, body, pre='', harness_root=None):
    """BOOT + 模块级前置 + 段落 主 + 主()，子进程跑 运行.py。"""
    src = BOOT + pre + '\n段落 主:\n' + body + '\n主()\n'
    path = tmp_path / name
    path.write_text(src, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    # 策略来源用例必须从「无任何设置」起步：清掉可能影响默认模式的调试/配置变量
    env.pop('HARNESS_SANDBOX_MODE', None)
    env.pop('HARNESS_DEBUG', None)
    env.pop('HARNESS_SANDBOX_DEBUG', None)
    if harness_root is not None:
        env['HARNESS_ROOT'] = str(harness_root)
    return subprocess.run(
        [sys.executable, RUNNER, str(path)],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8',
        errors='replace', timeout=TIMEOUT_SEC, env=env,
    )


def _kv(stdout):
    out = {}
    for line in stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            out[k.strip()] = v.strip()
    return out


def _ok(proc, what):
    assert proc.returncode == 0, (
        f'{what} 驱动应 rc=0，实际 {proc.returncode}\n'
        f'--- stdout ---\n{proc.stdout[-2000:]}\n--- stderr ---\n{proc.stderr[-2000:]}')


def _json(kv, key):
    assert key in kv, f'驱动没有打印 {key}，实际输出键：{list(kv)}'
    return json.loads(kv[key])


# --------------------------------------------------------------------------- #
# 1. 接线断言：bash 必须调 沙箱统一.运行（mock 的入参即契约）
# --------------------------------------------------------------------------- #
FAKE_RUNNER = '''
设 捕获 为 []

段落 假运行(命令数组, 策略, 超时毫秒, 选项):
  设 条目 为 ["命令数组": 命令数组, "模式": 策略["模式"],
               "超时": 超时毫秒, "工作目录": 字典获取(选项, "工作目录", "")]
  列表追加(捕获, 条目)
  设 执行 为 新建 执行结果()
  设 执行.退出码 为 0
  设 执行.标准输出 为 "MOCK-STDOUT"
  设 执行.标准错误 为 ""
  设 执行.是否超时 为 假
  返回 ["执行结果": 执行, "分类": "success", "详情": "",
         "约束": ["后端": "fake", "执行强度": "full", "是逃生口": 假]]
'''


def test_接线_bash确实经沙箱统一运行(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    body = '''
  设 忽略0 为 设沙箱运行器(假运行)
  设 结 为 bash处理(["命令": "echo T0550_WIRED"])
  打印("输出=" + 结["输出"])
  打印("码=" + 转字符串(结["退出码"]))
  打印("捕获=" + 序列化JSON(捕获))
  打印("日志=" + 序列化JSON(取bash沙箱日志()))
'''
    proc = _drive(tmp_path, '_wire.light', body, pre=FAKE_RUNNER, harness_root=root)
    _ok(proc, '接线')
    kv = _kv(proc.stdout)

    assert kv['输出'] == 'MOCK-STDOUT', f'bash 输出应来自 mock 运行器，实际 {kv["输出"]!r}'
    assert kv['码'] == '0'

    捕获 = _json(kv, '捕获')
    assert len(捕获) == 1, f'沙箱统一.运行 应被恰好调用 1 次，实际 {捕获}'
    条目 = 捕获[0]
    期望_argv = ['cmd', '/c', 'echo T0550_WIRED'] if os.name == 'nt' else ['sh', '-c', 'echo T0550_WIRED']
    assert 条目['命令数组'] == 期望_argv, f'命令数组口径不对：{条目["命令数组"]}'
    assert 条目['模式'] == 'read-only', f'无任何设置时必须落到 read-only，实际 {条目["模式"]}'
    assert 条目['超时'] == 30000, f'超时秒→毫秒应透传（默认 30s），实际 {条目["超时"]}'
    assert os.path.normcase(条目['工作目录']) == os.path.normcase(str(root)), (
        f'工作目录必须是 bash 已解析的 根，实际 {条目["工作目录"]}')

    日志 = _json(kv, '日志')
    assert 日志 and 日志[-1] == 'sandbox: backend=fake mode=read-only strength=full', (
        f'debug 日志行格式不对：{日志}')

    # 反向锚点（源码静态面）：接线若被改回直跑，上面 mock 断言与这两条同时失效
    src = open(BASH_LIGHT, encoding='utf-8').read()
    assert '沙箱统一.运行' in src, 'bash 工具必须经 沙箱统一.运行（不得直连 外部命令/裸进程树）'
    assert '取会话沙箱策略(会话id, 根)' in src, '策略必须由 取会话沙箱策略 产出（根来自 取调用根）'
    assert '外部命令.执行命令(命令, 真, 根, 空, 超时)' not in src, '旧的裸跑兜底必须已移除'


# --------------------------------------------------------------------------- #
# 2. fail-closed：无可用后端 → 工具错误 + 命令没执行（探针文件证明）
# --------------------------------------------------------------------------- #
NO_BACKEND = '''
段落 无可用后端():
  抛出 新建 沙箱不可用错误("平台 test 无可用沙箱后端（fail-closed）。探测详情: 无")
'''


def test_fail_closed_无可用后端时命令不执行(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    marker = 't0550_no_backend_marker.txt'
    body = '''
  设 忽略0 为 设探测提供者(无可用后端)
  设 结 为 bash处理(["命令": "echo SHOULD_NOT_RUN>''' + marker + '''"])
  打印("码=" + 转字符串(结["退出码"]))
  打印("错误=" + 结["错误"])
  打印("沙箱=" + 序列化JSON(结["sandbox"]))
'''
    proc = _drive(tmp_path, '_failclosed.light', body, pre=NO_BACKEND, harness_root=root)
    _ok(proc, 'fail-closed')
    kv = _kv(proc.stdout)

    assert kv['码'] == '-1', f'无可用后端必须返回失败，实际 {kv["码"]}'
    assert '执行失败：沙箱不可用' in kv['错误'], f'错误文案必须点名沙箱不可用：{kv["错误"]}'
    assert 'fail-closed' in kv['错误'], f'错误里应保留 fail-closed 依据：{kv["错误"]}'
    沙箱 = _json(kv, '沙箱')
    assert 沙箱['runnerFailed'] is True and 沙箱['mode'] == 'read-only'
    # 关键：命令真的没跑（不是「跑了以后报错」）
    assert not (root / marker).exists(), 'fail-closed 下底层 shell 不得执行（探针文件不该出现）'


# --------------------------------------------------------------------------- #
# 3. 逃生口：danger-full-access 真执行，且 argv 无包装
# --------------------------------------------------------------------------- #
def test_逃生口_danger_full_access_真执行且无包装(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    marker = 't0550_danger_marker.txt'
    body = '''
  设 根 为 环境变量("HARNESS_ROOT", ".")
  设 忽略0 为 设全局沙箱模式("danger-full-access")
  设 策 为 取会话沙箱策略("", 根)
  打印("策=" + 序列化JSON(策))
  设 约 为 约束(["cmd", "/c", "echo X"], 策)
  打印("约=" + 序列化JSON(约))
  设 结 为 bash处理(["命令": "echo DANGER>''' + marker + '''"])
  打印("码=" + 转字符串(结["退出码"]))
  打印("沙箱=" + 序列化JSON(结["sandbox"]))
  打印("统一日志=" + 序列化JSON(取沙箱执行日志()))
'''
    proc = _drive(tmp_path, '_danger.light', body, harness_root=root)
    _ok(proc, '逃生口')
    kv = _kv(proc.stdout)

    assert (root / marker).exists(), 'danger-full-access 下命令必须真执行'
    assert kv['码'] == '0', f'逃生口命令应成功，实际 {kv["码"]}'

    策 = _json(kv, '策')
    assert 策['模式'] == 'danger-full-access'
    约 = _json(kv, '约')
    assert 约['是逃生口'] is True and 约['后端'] == 'none'
    assert 约['argv'] == ['cmd', '/c', 'echo X'], f'逃生口 argv 必须原样，不得包装：{约["argv"]}'

    沙箱 = _json(kv, '沙箱')
    assert 沙箱['backend'] == 'none' and 沙箱['mode'] == 'danger-full-access'
    日志 = _json(kv, '统一日志')
    assert any('backend=none mode=danger-full-access strength=none' in x for x in 日志), 日志


# --------------------------------------------------------------------------- #
# 4. 策略来源：会话级 > 全局默认 > read-only；读取器优先于会话表
# --------------------------------------------------------------------------- #
SESSION_READER = '''
段落 读会话(会话id):
  如果 会话id == "s2":
    返回 "workspace-write"
  返回 ""
'''


def test_策略来源_优先级链(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    body = '''
  设 忽略0 为 设沙箱运行器(假运行)
  设 无设置 为 取会话沙箱策略("", ".")["模式"]
  打印("无设置=" + 无设置)

  设 忽略1 为 设全局沙箱模式("workspace-write")
  设 全局生效 为 取会话沙箱策略("any", ".")["模式"]
  打印("全局生效=" + 全局生效)

  设 忽略2 为 设会话沙箱模式("s1", "danger-full-access")
  设 会话生效 为 取会话沙箱策略("s1", ".")["模式"]
  设 全局仍生效 为 取会话沙箱策略("other", ".")["模式"]
  打印("会话生效=" + 会话生效)
  打印("全局仍生效=" + 全局仍生效)

  设 忽略3 为 设会话沙箱模式("s2", "read-only")
  设 忽略4 为 设会话沙箱读取器(读会话)
  设 读取器生效 为 取会话沙箱策略("s2", ".")["模式"]
  打印("读取器生效=" + 读取器生效)

  设 忽略5 为 设会话沙箱模式("s1", "")
  设 清后 为 取会话沙箱策略("s1", ".")["模式"]
  打印("清后=" + 清后)

  # bash 侧消费：会话 id 经任务控制上下文进入，策略随会话切换
  设 忽略6 为 设会话沙箱模式("s3", "workspace-write")
  设置调用上下文("s3", "c-policy")
  设 结 为 bash处理(["命令": "echo POLICY"])
  设 捕获模式 为 ""
  如果 长度(捕获) > 0:
    设 捕获模式 为 捕获[0]["模式"]
  打印("bash会话模式=" + 捕获模式)
  清调用上下文()
'''
    # 复用假运行器抓策略
    proc = _drive(tmp_path, '_policy.light', body, pre=FAKE_RUNNER + SESSION_READER, harness_root=root)
    _ok(proc, '策略来源')
    kv = _kv(proc.stdout)

    assert kv['无设置'] == 'read-only', '无任何设置必须落到 read-only'
    assert kv['全局生效'] == 'workspace-write', '全局默认应生效'
    assert kv['会话生效'] == 'danger-full-access', '会话级必须覆盖全局'
    assert kv['全局仍生效'] == 'workspace-write', '未设置会话的会话应继续吃全局'
    assert kv['读取器生效'] == 'workspace-write', '会话读取器（T-0551 事件投影）必须优先于会话表'
    assert kv['清后'] == 'workspace-write', '清空会话设置应回落全局'
    assert kv['bash会话模式'] == 'workspace-write', 'bash 必须按会话 id 取策略（而不是恒定 read-only）'


# --------------------------------------------------------------------------- #
# 5. 杀树并存：沙箱执行中停止 → 整棵树被杀 + [命令已被用户停止]
# --------------------------------------------------------------------------- #
def test_杀树并存_预停止立即杀树(tmp_path):
    root = tmp_path / 'root'
    root.mkdir()
    body = '''
  设 忽略0 为 设全局沙箱模式("danger-full-access")
  开运行("甲")
  设置调用上下文("甲", "c-kill")
  登记工具("甲", "c-kill", "bash", "slow")
  设 慢命令 为 "sleep 30"
  如果 环境变量("OS", "") == "Windows_NT":
    设 慢命令 为 "ping -n 30 127.0.0.1"
  设 停前 为 请求停止("甲")
  打印("停前=" + 转字符串(停前["ok"]))
  设 结 为 bash处理(["命令": 慢命令, "超时": 60])
  打印("码=" + 转字符串(结["退出码"]))
  打印("含停止=" + 转字符串(结["错误"].包含("命令已被用户停止")))
  设 项 为 取工具("c-kill")
  打印("已杀=" + 转字符串(字典获取(项, "已杀", 假)))
  清调用上下文()
  关运行("甲")
'''
    proc = _drive(tmp_path, '_kill.light', body, harness_root=root)
    _ok(proc, '杀树')
    kv = _kv(proc.stdout)

    assert kv['停前'] == 'True'
    assert kv['码'] == '-1', f'被停止的命令必须退出码 -1，实际 {kv["码"]}'
    assert kv['含停止'] == 'True', f'必须标注 [命令已被用户停止]：{kv["已杀"]}'
    assert kv['已杀'] == 'True', '工具项必须置 已杀（证明树句柄回绑生效）'

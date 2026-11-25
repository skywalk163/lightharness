# -*- coding: utf-8 -*-
"""T-0472：lightharness 运行中任务控制（停止/暂停/插入 + 工具卡片级控制 + 可杀进程树）。

从 stash（历史改动-运行中任务控制功能-20261125完整备份）手工迁移到当前 main 新基线，
本文件锁住三类判据：

A. 行为级（Light 驱动，走 运行.py 子进程，与 tests/test_任务控制.py 同一套驱动口径）：
   1) 工具级 stop 真杀进程树（树.等待到死 为真），另一个未停的树仍存活——只杀对应调用；
   2) 会话级 请求停止 联动杀掉该会话挂的全部子进程（已杀子进程 ≥ 1）；
   3) bash 处理 在有调用上下文时走进程树路径：正常命令退出码 0、输出透传；
   4) 会话已请求停止时，bash 新调用被 绑定进程树 立刻补杀 → [命令已被用户停止] + 退出码 -1；
   5) bash 进程树路径保留 T-0442 超时契约：超时被杀 + 错误注明「超时」+ 退出码非 0；
   6) 无调用上下文时 bash 走原同步路径（CLI/测试零行为变化）；
   7) 暂停/继续状态机 + 插入（steer）FIFO 消费。

B. 接线契约（源码文本断言，与 tests/test_流式推流接线契约.py 同风格）：
   web服务器 的 /api/task/* 八条路由与六个 handler、流式 开运行/收控制帧/关运行、
   代理 的 设置调用上下文/登记工具/清调用上下文、webui 的 running-bar/taskControl/
   applyToolState——任何一处接线被改断，测试立即变红。

Light 约束备忘：不写 bytes 字面量；变量名避开关键字子串；顶层逻辑包进 段落 主。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 180


def _find_sibling(name):
    """运行时依赖的兄弟仓定位（与 运行.py 的探测口径一致）。"""
    repo = 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'
    candidates = [
        os.environ.get(name, ''),
        os.path.join(ROOT, '..', repo),
        os.path.join(ROOT, '..', '..', repo),
        '/home/skywalk/dswork/' + repo,
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _run(src: str, tmp_path, name='driver.light'):
    f = tmp_path / name
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_TOOL_ROOTS')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
    env['PYTHONIOENCODING'] = 'utf-8'
    p = subprocess.run(
        [sys.executable, RUNNER, str(f)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
        timeout=TIMEOUT_SEC, cwd=str(tmp_path), env=env,
    )
    kv = {}
    for line in p.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    combined = p.stdout + p.stderr
    try:
        debug = os.path.join(ROOT, '.hive', 'verify-debug')
        os.makedirs(debug, exist_ok=True)
        with open(os.path.join(debug, 'T0472-' + name), 'w', encoding='utf-8') as fh:
            fh.write('rc=' + str(p.returncode) + '\n' + combined)
    except OSError:
        pass
    return p.returncode, combined, kv


def _ok(kv, out, *keys):
    missing = [k for k in keys if k not in kv]
    assert not missing, f'驱动输出缺键 {missing}\n{out}'


# 平台分支：Windows 用 ping 慢命令，POSIX 用 sleep
PLAT = '''
设 是win 为 (环境变量("OS", "") == "Windows_NT")
设 慢命令 为 "sleep 30"
如果 是win:
  设 慢命令 为 "ping -n 30 127.0.0.1"
'''

BOOT_TASK = '''
从 任务控制 导入 开运行, 关运行, 取运行, 运行是否存在, 置代理
从 任务控制 导入 请求停止, 是已请求停止, 请求暂停, 请求继续, 是已暂停, 等继续
从 任务控制 导入 登记工具, 取工具, 绑定进程树, 完成工具, 停工具, 暂停工具, 继续工具, 列工具
从 任务控制 导入 插入提示, 取插入, 插入深度, 发工具状态
从 任务控制 导入 设置调用上下文, 取调用上下文, 清调用上下文
从 进程树 导入 进程树
'''

MAIN = '''
段落 主:
%s

主()
'''


def _drive(body: str, tmp_path, name='driver.light', boot=BOOT_TASK):
    src = BOOT_TASK + PLAT + boot + MAIN % body
    return _run(src, tmp_path, name)


# --------------------------------------------------------------------------- #
# A1. 工具级 stop：只杀对应调用，另一个未停的树仍存活
# --------------------------------------------------------------------------- #
def test_工具级停止只杀对应进程树(tmp_path):
    body = '''
  开运行("甲")
  设置调用上下文("甲", "c1")
  设 工一 为 登记工具("甲", "c1", "bash", "慢命令一")
  设 工二 为 登记工具("甲", "c2", "bash", "慢命令二")
  设 树甲 为 新建 进程树(慢命令数组, {})
  设 树乙 为 新建 进程树(慢命令数组, {})
  设 启甲 为 树甲.启动()
  设 启乙 为 树乙.启动()
  打印("启一=" + 转字符串(启甲))
  打印("启二=" + 转字符串(启乙))
  设 绑一 为 绑定进程树("c1", 树甲)
  设 绑二 为 绑定进程树("c2", 树乙)
  打印("绑一=" + 转字符串(绑一))
  打印("绑二=" + 转字符串(绑二))
  打印("一初活=" + 转字符串(树甲.是否存活()))
  打印("二初活=" + 转字符串(树乙.是否存活()))
  设 停一 为 停工具("c1")
  打印("停一=" + 转字符串(停一))
  打印("一死透=" + 转字符串(树甲.等待到死(5000)))
  打印("一后活=" + 转字符串(树甲.是否存活()))
  打印("二仍活=" + 转字符串(树乙.是否存活()))
  设 态一 为 取工具("c1")
  设 态二 为 取工具("c2")
  打印("态一=" + 态一["状态"])
  打印("已杀标=" + 转字符串(态一["已杀"]))
  打印("态二=" + 态二["状态"])
  设 收尾停 为 停工具("c2")
  打印("收尾死=" + 转字符串(树乙.等待到死(5000)))
'''
    boot = '''
设 慢命令数组 为 ["sh", "-c", 慢命令]
如果 是win:
  设 慢命令数组 为 ["cmd", "/c", 慢命令]
'''
    rc, out, kv = _drive(body, tmp_path, 't0472_tool_stop.light', boot)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    _ok(kv, out, '启一', '启二', '绑一', '绑二', '一初活', '二初活', '停一',
        '一死透', '一后活', '二仍活', '态一', '已杀标', '态二', '收尾死')
    assert kv['启一'] == 'True' and kv['启二'] == 'True', f'两个进程都应启动成功\n{out}'
    assert kv['绑一'] == 'True' and kv['绑二'] == 'True', f'两个进程树都应绑定成功\n{out}'
    assert kv['一初活'] == 'True' and kv['二初活'] == 'True', f'启动后都应存活\n{out}'
    assert kv['停一'] == 'True', f'停工具应返回真\n{out}'
    assert kv['一死透'] == 'True' and kv['一后活'] == 'False', f'停掉的树必须真死\n{out}'
    assert kv['二仍活'] == 'True', f'未停的工具树必须仍然存活（工具级 stop 只杀对应调用）\n{out}'
    assert kv['态一'] == 'stopped' and kv['已杀标'] == 'True', f'停工具应置 stopped/已杀\n{out}'
    assert kv['态二'] == 'running', f'未停工具应保持 running\n{out}'
    assert kv['收尾死'] == 'True', f'清理停止后树二也应死掉\n{out}'


# --------------------------------------------------------------------------- #
# A2. 会话级 请求停止：联动杀掉该会话挂的全部子进程
# --------------------------------------------------------------------------- #
def test_会话级停止联动杀树(tmp_path):
    body = '''
  开运行("甲")
  设置调用上下文("甲", "c1")
  登记工具("甲", "c1", "bash", "慢命令")
  设 树甲 为 新建 进程树(慢命令数组, {})
  设 启一 为 树甲.启动()
  打印("启一=" + 转字符串(启一))
  设 绑一 为 绑定进程树("c1", 树甲)
  打印("初活=" + 转字符串(树甲.是否存活()))
  设 停一 为 请求停止("甲")
  打印("停ok=" + 转字符串(停一["ok"]))
  打印("已杀数=" + 转字符串(停一["已杀子进程"]))
  打印("停标志=" + 转字符串(是已请求停止("甲")))
  打印("死透=" + 转字符串(树甲.等待到死(5000)))
  打印("后活=" + 转字符串(树甲.是否存活()))
'''
    boot = '''
设 慢命令数组 为 ["sh", "-c", 慢命令]
如果 是win:
  设 慢命令数组 为 ["cmd", "/c", 慢命令]
'''
    rc, out, kv = _drive(body, tmp_path, 't0472_session_stop.light', boot)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    _ok(kv, out, '启一', '初活', '停ok', '已杀数', '停标志', '死透', '后活')
    assert kv['启一'] == 'True' and kv['初活'] == 'True', f'进程应启动并存活\n{out}'
    assert kv['停ok'] == 'True', f'请求停止应 ok\n{out}'
    assert kv['已杀数'] == '1', f'请求停止应联动杀掉 1 个子进程（实际 {kv["已杀数"]}）\n{out}'
    assert kv['停标志'] == 'True', f'停止标志应置位\n{out}'
    assert kv['死透'] == 'True' and kv['后活'] == 'False', f'停止任务必须真杀子进程，不是只关 UI 流\n{out}'


# --------------------------------------------------------------------------- #
# A3. bash 进程树路径：有调用上下文 → 正常命令退出码 0、输出透传、完成后 done
# --------------------------------------------------------------------------- #
def test_带上下文bash走进程树路径(tmp_path):
    body = '''
  开运行("甲")
  设置调用上下文("甲", "call-x")
  设 登 为 登记工具("甲", "call-x", "bash", "echo")
  设 结 为 bash处理(["命令": "echo T0472_OK"])
  打印("输出=" + 结["输出"].去除空白())
  打印("码=" + 转字符串(结["退出码"]))
  设 态 为 取工具("call-x")
  打印("态=" + 态["状态"])
  清调用上下文()
'''
    boot = '''
从 工具_bash 导入 bash处理
'''
    rc, out, kv = _drive(body, tmp_path, 't0472_bash_tree.light', boot)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    _ok(kv, out, '输出', '码', '态')
    assert kv['输出'] == 'T0472_OK', f'进程树路径输出应透传（实际 {kv["输出"]!r}）\n{out}'
    assert kv['码'] == '0', f'正常命令退出码应为 0（实际 {kv["码"]}）\n{out}'
    assert kv['态'] == 'done', f'bash 结束后工具应置 done（实际 {kv["态"]}）\n{out}'


# --------------------------------------------------------------------------- #
# A4. 会话已请求停止：bash 新调用被 绑定进程树 立刻补杀 → [命令已被用户停止]
# --------------------------------------------------------------------------- #
def test_已停止会话的bash被立即补杀(tmp_path):
    body = '''
  开运行("甲")
  设置调用上下文("甲", "call-s")
  登记工具("甲", "call-s", "bash", "慢命令")
  设 停 为 请求停止("甲")
  打印("停ok=" + 转字符串(停["ok"]))
  设 结 为 bash处理(["命令": 慢命令, "超时": 60])
  打印("码=" + 转字符串(结["退出码"]))
  打印("标=" + 转字符串(结["错误"].包含("已被用户停止")))
'''
    boot = '''
从 工具_bash 导入 bash处理
'''
    rc, out, kv = _drive(body, tmp_path, 't0472_bash_kill_on_bind.light', boot)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    _ok(kv, out, '停ok', '码', '标')
    assert kv['停ok'] == 'True', f'停止应 ok\n{out}'
    assert kv['码'] == '-1', f'被停止的命令退出码应为 -1（实际 {kv["码"]}）\n{out}'
    assert kv['标'] == 'True', f'错误里必须标注 [命令已被用户停止]，别让代理误以为成功\n{out}'


# --------------------------------------------------------------------------- #
# A5. bash 进程树路径保留 T-0442 超时契约：超时被杀 + 说明 + 非 0 退出码
# --------------------------------------------------------------------------- #
def test_进程树路径超时契约(tmp_path):
    body = '''
  开运行("甲")
  设置调用上下文("甲", "call-t")
  登记工具("甲", "call-t", "bash", "慢命令")
  设 结 为 bash处理(["命令": 慢命令, "超时": 2])
  打印("码=" + 转字符串(结["退出码"]))
  打印("超时词=" + 转字符串(结["错误"].包含("超时")))
  打印("终止词=" + 转字符串(结["错误"].包含("终止")))
  清调用上下文()
'''
    boot = '''
从 工具_bash 导入 bash处理
'''
    rc, out, kv = _drive(body, tmp_path, 't0472_bash_timeout.light', boot)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    _ok(kv, out, '码', '超时词', '终止词')
    assert kv['码'] == '-1', f'超时应返回非 0 退出码（实际 {kv["码"]}）\n{out}'
    assert kv['超时词'] == 'True' and kv['终止词'] == 'True', \
        f'超时说明缺失「超时被终止」字样，实际 {kv["超时词"]}/{kv["终止词"]}\n{out}'


# --------------------------------------------------------------------------- #
# A6. 无调用上下文：bash 走原同步路径，行为不变（CLI/测试零回退）
# --------------------------------------------------------------------------- #
def test_无上下文bash走原同步路径(tmp_path):
    body = '''
  设 结 为 bash处理(["命令": "echo NOCTX_OK"])
  打印("输出=" + 结["输出"].去除空白())
  打印("码=" + 转字符串(结["退出码"]))
  设 二 为 bash处理(["命令": "echo 第二条"])
  打印("二出=" + 二["输出"].去除空白())
  打印("二码=" + 转字符串(二["退出码"]))
  打印("工数=" + 转字符串(长(列工具())))
'''
    boot = '''
从 工具_bash 导入 bash处理
'''
    rc, out, kv = _drive(body, tmp_path, 't0472_bash_noctx.light', boot)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    _ok(kv, out, '输出', '码', '二出', '二码', '工数')
    assert kv['输出'] == 'NOCTX_OK' and kv['码'] == '0', f'无上下文 bash 行为应保持不变\n{out}'
    assert kv['二出'] == '第二条' and kv['二码'] == '0', f'第二条也应正常\n{out}'
    assert kv['工数'] == '0', f'无上下文路径不应登记工具（实际 {kv["工数"]}）\n{out}'


# --------------------------------------------------------------------------- #
# A7. 暂停/继续状态机 + 插入（steer）FIFO：运行中的下一步之前消费
# --------------------------------------------------------------------------- #
def test_暂停继续与插入消费(tmp_path):
    body = '''
  开运行("甲")
  # 插入：两条按序进队，FIFO 取出——跑轮循环每步开头取一条作为当轮提示词
  设 插一 为 插入提示("甲", "先改成靛蓝色")
  设 插二 为 插入提示("甲", "然后跑测试")
  打印("插一ok=" + 转字符串(插一["ok"]))
  打印("插二ok=" + 转字符串(插二["ok"]))
  打印("深=" + 转字符串(插入深度("甲")))
  打印("出一=" + 取插入("甲"))
  打印("出二=" + 取插入("甲"))
  打印("出空=[" + 取插入("甲") + "]")
  # 暂停/继续：跑轮循环开头 等继续（暂停时最多等 400 次 × 0.05s）
  设 暂一 为 请求暂停("甲")
  打印("暂停ok=" + 转字符串(暂一["ok"]))
  打印("已暂停=" + 转字符串(是已暂停("甲")))
  设 等一 为 等继续("甲", 1)
  打印("暂停中等=" + 转字符串(等一))
  设 继一 为 请求继续("甲")
  打印("继续ok=" + 转字符串(继一["ok"]))
  打印("续后暂=" + 转字符串(是已暂停("甲")))
  设 等二 为 等继续("甲", 2)
  打印("续后等=" + 转字符串(等二))
  # 停止优先于暂停：停止置位后 等继续 立即放行（不再阻塞）
  设 暂二 为 请求暂停("甲")
  设 停一 为 请求停止("甲")
  设 等三 为 等继续("甲", 100)
  打印("停止放行=" + 转字符串(等三))
'''
    rc, out, kv = _drive(body, tmp_path, 't0472_pause_steer.light')
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    _ok(kv, out, '插一ok', '插二ok', '深', '出一', '出二', '出空',
        '暂停ok', '已暂停', '暂停中等', '继续ok', '续后暂', '续后等', '停止放行')
    assert kv['插一ok'] == 'True' and kv['插二ok'] == 'True', f'插入应 ok\n{out}'
    assert kv['深'] == '2', f'插入深度应为 2\n{out}'
    assert kv['出一'] == '先改成靛蓝色' and kv['出二'] == '然后跑测试', \
        f'插入必须 FIFO 消费（{kv["出一"]}/{kv["出二"]}）\n{out}'
    assert kv['出空'] == '[]', f'空队列应返回空串\n{out}'
    assert kv['暂停ok'] == 'True' and kv['已暂停'] == 'True', f'暂停应置位\n{out}'
    assert kv['暂停中等'] == 'False', f'暂停中等继续应在上限内返回假\n{out}'
    assert kv['继续ok'] == 'True' and kv['续后暂'] == 'False', f'继续应清暂停位\n{out}'
    assert kv['续后等'] == 'True', f'继续后等继续应立即返回真\n{out}'
    assert kv['停止放行'] == 'True', f'停止置位后 等继续 必须立即放行（停止优先于暂停）\n{out}'


# --------------------------------------------------------------------------- #
# B. 接线契约（源码文本断言）
# --------------------------------------------------------------------------- #
def _read(rel):
    with open(os.path.join(ROOT, rel), encoding='utf-8') as f:
        return f.read()


WEB = _read(os.path.join('src', 'web服务器.light'))
PROXY = _read(os.path.join('src', '代理.light'))
BASH = _read(os.path.join('src', '工具_bash.light'))
INDEX = _read(os.path.join('webui', 'index.html'))
APP = _read(os.path.join('webui', 'app.js'))
TOOLCARD = _read(os.path.join('webui', 'tool-card.js'))
STYLE = _read(os.path.join('webui', 'style.css'))


def test_web路由八条与handler齐全():
    routes = ['/api/task/stop', '/api/task/pause', '/api/task/resume', '/api/task/steer',
              '/api/task/tools', '/api/task/tool/stop', '/api/task/tool/pause', '/api/task/tool/resume']
    for r in routes:
        assert r in WEB, f'web服务器 缺路由 {r}'
    for fn in ('处理停止任务', '处理暂停任务', '处理继续任务', '处理工具控制', '处理插入提示', '处理工具清单'):
        assert f'段落 {fn}(' in WEB, f'web服务器 缺 handler {fn}'
    # 控制接口必须挂在 chat 之前（先于既有路由分派被匹配）
    assert WEB.index('/api/task/stop') < WEB.index('路径 == "/health"'), '/api/task/* 应先于 /health 分派'
    # 停止任务必须真的动进程树：请求停止 里杀子进程计数进响应
    assert '已杀子进程' in WEB, '处理停止任务 响应应带 已杀子进程'


def test_web流式运行项登记与收口():
    # 客户端连接侧开运行项（/api/task/* 立刻可见），SSE 推控制帧
    assert '段落 收控制帧(帧)' in WEB, '流式路径缺 收控制帧'
    assert '开运行(排队键, 收控制帧)' in WEB, '流式路径必须在连接侧 开运行'
    # 跑轮循环：停止跳出 / 暂停等继续 / 插入成为当轮文本
    body_start = WEB.index('段落 后台跑一轮(')
    body = WEB[body_start:WEB.index('# 推流实现：HTTP 协程侧边取边发', body_start)]
    assert '是已请求停止(排队键)' in body, '流式循环必须响应停止标志'
    assert '等继续(排队键, 400)' in body, '流式循环每轮开头必须 等继续（暂停）'
    assert '取插入(排队键)' in body, '流式循环必须消费插入（steer）'
    # 收口：最终块 关运行
    assert '关运行(排队键)' in WEB, '后台跑一轮 收尾必须 关运行'


def test_代理接线调用上下文():
    assert '从 任务控制 导入' in PROXY, '代理 必须导入 任务控制'
    assert '设置调用上下文(会话键, 块["id"])' in PROXY, '工具执行前必须设置调用上下文'
    assert '登记工具(会话键, 块["id"], 块["name"]' in PROXY, '工具执行前必须登记工具'
    assert '清调用上下文()' in PROXY, '工具执行后必须清调用上下文'
    # 顺序：登记在 执行 之前，清在 执行 之后
    assert PROXY.index('登记工具(会话键') < PROXY.index('己.注册表.执行(块["name"]'), '登记必须先于执行'
    assert PROXY.index('己.注册表.执行(块["name"]') < PROXY.index('清调用上下文()'), '清上下文必须后于执行'


def test_bash进程树分支与修复共存():
    assert '段落 bash处理进程树(' in BASH, 'bash 必须有进程树分支'
    assert '绑定进程树(调用id, 树)' in BASH, '进程树必须绑定到 任务控制（可被 /api/task/* 杀）'
    assert '已被用户停止' in BASH, '被停止的命令必须标注'
    # T-0442 修复不回退：超时可配、stdin 关闭说明、shell 层错误判定仍在
    assert '段落 取超时秒(' in BASH, 'T-0442 取超时秒 不许被回退'
    assert '"超时": ["type": "integer"' in BASH, 'T-0442 超时参数 schema 不许被回退'
    assert '段落 是等待输入(' in BASH, 'T-0442 等待输入提示不许被回退'
    assert '段落 是shell层错误(' in BASH, 'T-0442 shell 层错误判定不许被回退'
    # T-0470 cd 守卫不回退
    assert '段落 检查cd越界(' in BASH, 'T-0470 cd 守卫不许被回退'
    # 上下文为空走原同步路径
    assert '外部命令.执行命令(命令, 真, 根, 空, 超时)' in BASH, '无上下文同步路径必须保留'


def test_webui任务条与工具控制条齐全():
    # index.html：运行中任务条
    assert 'id="running-bar"' in INDEX and 'id="steer-btn"' in INDEX and 'id="task-stop-btn"' in INDEX, \
        'index.html 缺运行中任务条'
    # style.css：控制条与任务条样式
    for cls in ('.tool-controls', '.tool-ctrl', '.running-bar', '.steer-btn', '.task-stop-btn'):
        assert cls in STYLE, f'style.css 缺样式 {cls}'
    # tool-card.js：控制条创建 + 状态应用 + 回调注入
    assert 'data-action="pause"' in TOOLCARD and 'data-action="stop"' in TOOLCARD, \
        'tool-card.js 缺控制按钮'
    assert 'function applyToolState' in TOOLCARD, 'tool-card.js 缺 applyToolState'
    assert 'setControlHandler' in TOOLCARD, 'tool-card.js 缺 setControlHandler'
    assert 'ctrlEl.hidden = true' in TOOLCARD, '工具结束后必须隐藏控制条'
    # app.js：任务控制请求 + 帧处理 + 事件绑定
    assert 'function taskControl' in APP, 'app.js 缺 taskControl'
    assert '"/api/task/" + action' in APP, 'app.js 必须请求 /api/task/*'
    assert 'json.种类 === "工具状态"' in APP, 'app.js 必须处理 工具状态 帧'
    assert 'setStreaming' in APP and 'runningBarEl.hidden = !on' in APP, \
        'app.js 必须随流状态切换运行中任务条'
    assert 'window.ToolCard.setControlHandler(controlTool)' in APP, 'app.js 必须注入控制回调'
    assert 'taskControl("stop")' in APP, '停止按钮必须同步请求服务端杀进程'

# -*- coding: utf-8 -*-
"""T-0401 目标续跑（goal round driver 接线前置）判据。

每个用例起一个独立 Light 子进程，直接跑 src/目标续跑.light 与 src/目标工具.light 的纯逻辑面。
本卡交付「决策函数 + 工具规格」，不接线，所以判据全部落在函数返回值上：

  1. completed 未完成 → 续跑，提示文本复用 目标轮驱动.渲染目标轮文本（含 <goal_round> 与三段指令）
  2. 连续 2 轮 completed 且 revision 未变 → 停止/no-progress（第 1 轮必须仍是续跑）
  3. max-tokens → 停止（栅栏口径 disarm）
  4. aborted（原因 user_abort）→ 停止
  5. 轮次到上限 → 停止/round-limit
  6. goal 工具 complete → 折叠折出 phase=complete，下一轮决策 完成
  7. error / max-steps 理由可区分
  8. 工具规格 + 注册进工具注册表（name=目标 / alias=goal / additionalProperties=false）
  9. 合并目标变更推进 revision 且重置无进展计数

反证（写进 .hive/summary.md）：把 src/目标续跑.light 的 续默认无进展阈值 由 2 改成 1，
用例 2（第 1 轮必须续跑）立红；改回 2 复绿。
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 120


def _find_sibling(name):
    """运行时依赖的兄弟仓定位（与 运行.py 的探测口径一致，但不依赖宿主环境）。"""
    candidates = [
        os.environ.get(name, ''),
        os.path.join(ROOT, '..', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
        os.path.join(ROOT, '..', '..', 'lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
        '/home/skywalk/dswork/' + ('lightplugin' if name == 'LIGHTPLUGIN' else 'light'),
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _run(src: str, tmp_path):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    for key in ('LIGHTPLUGIN', 'LIGHT_MERGE'):
        found = _find_sibling(key)
        if found:
            env[key] = found
        else:
            env.pop(key, None)
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
        with open(os.path.join(debug, 'T0401-' + os.path.basename(str(f)) + '.log'),
                  'w', encoding='utf-8') as fh:
            fh.write('rc=' + str(p.returncode) + '\n' + combined)
    except OSError:
        pass
    return p.returncode, combined, kv


BOOT = '''
从 目标续跑 导入 续建续跑状态, 续记账, 续停止状态, 续续跑决策, 续合并目标变更, 续执行目标工具, 续目标工具规格
从 目标续跑 导入 续动作续跑, 续动作完成, 续动作停止, 续默认无进展阈值
从 目标折叠 导入 折叠目标, 造目标视图

段落 造视图(编号, 修订, 客观, 阶段, 上限, 已开, 激活):
  返回 {"id": 编号, "revision": 修订, "objective": 客观, "phase": 阶段, "maxGoalRounds": 上限, "roundsStarted": 已开, "createdAt": 0, "updatedAt": 0, "activation": 激活}

段落 主视图():
  返回 造视图("g1", 1, "把 T-0401 三个产物跑绿", "active", 5, 0, "armed")
'''


# --------------------------------------------------------------------------- #
# 1. completed 且未完成 → 续跑；提示文本逐字复用 渲染目标轮文本
# --------------------------------------------------------------------------- #
def test_完成一轮未标目标时自动续跑(tmp_path):
    src = BOOT + '''
段落 主:
  设 状态 为 续建续跑状态(主视图(), {})
  设 决策 为 续续跑决策(状态, {"种类": "completed"})
  打印("动作=" + 决策["动作"])
  打印("理由=" + 决策["理由"])
  设 提示 为 决策["提示文本"]
  打印("含头=" + 转字符串(字符串包含(提示, "<goal_round>")))
  打印("含尾=" + 转字符串(字符串包含(提示, "</goal_round>")))
  打印("含段一=" + 转字符串(字符串包含(提示, "Continue working toward the objective in this same session.")))
  打印("含段二=" + 转字符串(字符串包含(提示, "Make concrete progress and verify the result.")))
  打印("含段三=" + 转字符串(字符串包含(提示, "mark it complete")))
  打印("含轮号=" + 转字符串(字符串包含(提示, "Round: 1/5")))
  打印("轮次=" + 转字符串(字典获取(决策, "轮次", 空)))
  打印("阈值=" + 转字符串(字典获取(状态, "无进展阈值", 空)))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['动作'] == '续跑', f'一轮完成且目标未 complete 必须续跑\n{out}'
    assert kv['理由'] == 'round-advance', out
    assert kv['含头'] == 'True' and kv['含尾'] == 'True', f'提示缺 <goal_round> 包裹\n{out}'
    assert kv['含段一'] == 'True' and kv['含段二'] == 'True' and kv['含段三'] == 'True', \
        f'提示缺三段固定指令（应逐字复用 目标轮驱动.渲染目标轮文本）\n{out}'
    assert kv['含轮号'] == 'True', f'提示轮号未按 已开+1 渲染\n{out}'
    assert kv['轮次'] == '1', out
    assert kv['阈值'] == '2', f'无进展阈值默认应为 2（N 必须 > 1）\n{out}'


# --------------------------------------------------------------------------- #
# 2. 连续 2 轮 completed 且 revision 未变 → 停止/no-progress（第 1 轮必须仍续跑）
#    反证：阈值改成 1 → 第 1 轮即停止，本用例立红
# --------------------------------------------------------------------------- #
def test_连续两轮无进展才停(tmp_path):
    src = BOOT + '''
段落 主:
  设 状态 为 续建续跑状态(主视图(), {})
  设 状态1 为 续记账(状态, {"种类": "completed"})
  设 决策1 为 续续跑决策(状态1, {"种类": "completed"})
  打印("一轮动作=" + 决策1["动作"])
  打印("一轮连续=" + 转字符串(字典获取(状态1, "连续无进展", 空)))
  设 状态2 为 续记账(状态1, {"种类": "completed"})
  设 决策2 为 续续跑决策(状态2, {"种类": "completed"})
  打印("二轮动作=" + 决策2["动作"] + "/" + 决策2["理由"])
  打印("二轮连续=" + 转字符串(字典获取(状态2, "连续无进展", 空)))
  打印("二轮轮次=" + 转字符串(字典获取(状态2, "轮次", 空)))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['一轮连续'] == '1' and kv['二轮连续'] == '2', f'无进展计数不对\n{out}'
    assert kv['一轮动作'] == '续跑', \
        f'阈值=2 时第 1 轮必须仍续跑（反证点：阈值改 1 会在此红）\n{out}'
    assert kv['二轮动作'] == '停止/no-progress', f'连续 2 轮 revision 未变必须停\n{out}'
    assert kv['二轮轮次'] == '2', out


# --------------------------------------------------------------------------- #
# 3. max-tokens → 停止（轮次结束栅栏口径 disarm）
# --------------------------------------------------------------------------- #
def test_最大令牌截断受栅栏停止(tmp_path):
    src = BOOT + '''
段落 主:
  设 状态 为 续建续跑状态(主视图(), {})
  字典设置(状态, "预约", {"goalId": "g1", "revision": 1, "round": 1, "phase": "claimed", "cancelled": 假})
  设 决策 为 续续跑决策(状态, {"种类": "max-tokens"})
  打印("动作=" + 决策["动作"])
  打印("理由=" + 决策["理由"])
  打印("栅栏=" + 转字符串(字典获取(决策, "栅栏", 空)))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['动作'] == '停止' and kv['理由'] == 'max-tokens', f'max-tokens 必须停（不许续跑）\n{out}'
    assert kv['栅栏'] == 'disarm', f'max-tokens 栅栏口径应为 disarm\n{out}'


# --------------------------------------------------------------------------- #
# 4. aborted（原因 user_abort）→ 停止
# --------------------------------------------------------------------------- #
def test_用户中止不续跑(tmp_path):
    src = BOOT + '''
段落 主:
  设 状态 为 续建续跑状态(主视图(), {})
  设 决策 为 续续跑决策(状态, {"种类": "aborted", "原因": "user_abort"})
  打印("动作=" + 决策["动作"])
  打印("理由=" + 决策["理由"])
  打印("原因=" + 转字符串(字典获取(决策, "原因", 空)))
  打印("栅栏=" + 转字符串(字典获取(决策, "栅栏", 空)))
  # 已认领预约被中止 → 栅栏保留预约（keep-attempt）但决策仍是停
  设 状态2 为 续建续跑状态(主视图(), {})
  字典设置(状态2, "预约", {"goalId": "g1", "revision": 1, "round": 1, "phase": "claimed", "cancelled": 假})
  设 决策2 为 续续跑决策(状态2, {"种类": "aborted", "原因": "user_abort"})
  打印("二栅栏=" + 转字符串(字典获取(决策2, "栅栏", 空)))
  打印("二动作=" + 决策2["动作"])
  打印("取消标记=" + 转字符串(字典获取(字典获取(状态2, "预约", 空), "cancelled", 空)))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['动作'] == '停止' and kv['理由'] == 'aborted', f'aborted 必须停\n{out}'
    assert kv['原因'] == 'user_abort', out
    assert kv['栅栏'] == 'disarm', f'无预约时 aborted 栅栏应为 disarm\n{out}'
    assert kv['二栅栏'] == 'keep-attempt' and kv['二动作'] == '停止', \
        f'已认领预约应 keep-attempt，但决策仍停\n{out}'
    assert kv['取消标记'] == 'True', f'keep-attempt 应把预约标记 cancelled\n{out}'


# --------------------------------------------------------------------------- #
# 5. 轮次到上限 → 停止/round-limit
# --------------------------------------------------------------------------- #
def test_轮次预算耗尽停止(tmp_path):
    src = BOOT + '''
段落 主:
  设 视图 为 造视图("g1", 1, "跑到底", "active", 3, 2, "armed")
  设 状态 为 续建续跑状态(视图, {})
  打印("起轮=" + 转字符串(字典获取(状态, "轮次", 空)))
  设 决策前 为 续续跑决策(状态, {"种类": "completed"})
  打印("前动作=" + 决策前["动作"])
  设 状态末 为 续记账(状态, {"种类": "completed"})
  设 决策末 为 续续跑决策(状态末, {"种类": "completed"})
  打印("末动作=" + 决策末["动作"] + "/" + 决策末["理由"])
  打印("末轮次=" + 转字符串(字典获取(决策末, "轮次", 空)))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 {rc}\n{out}'
    assert kv['起轮'] == '2', out
    assert kv['前动作'] == '续跑', f'第 3 轮尚在预算内应续跑\n{out}'
    assert kv['末动作'] == '停止/round-limit', f'轮次到上限必须 round-limit\n{out}'
    assert kv['末轮次'] == '3', out


# --------------------------------------------------------------------------- #
# 6. goal 工具 complete → 折叠折出 phase=complete，下一轮决策 完成
# --------------------------------------------------------------------------- #
def test_目标工具标记完成后决策收工(tmp_path):
    src = BOOT + '''
段落 主:
  设 创建 为 {"kind": "goal/change", "version": 1, "operation": "create", "goal": {"id": "g1", "objective": "跑到底", "phase": "active", "revision": 1, "maxGoalRounds": 5}, "roundsStarted": 0, "createdAt": 0, "updatedAt": 0}
  设 折叠甲 为 折叠目标([{"type": "goal/change", "data": 创建, "seq": 1}])
  设 状态 为 续建续跑状态(造目标视图(折叠甲, "armed"), {})
  设 结果 为 续执行目标工具({"动作": "complete", "现在": 5}, 状态)
  打印("工具ok=" + 转字符串(结果["ok"]))
  打印("操作=" + 转字符串(字典获取(结果["变更"], "operation", 空)))
  打印("快照阶段=" + 转字符串(字典获取(字典获取(结果["变更"], "goal", 空), "phase", 空)))
  打印("快照修订=" + 转字符串(字典获取(字典获取(结果["变更"], "goal", 空), "revision", 空)))
  打印("已开=" + 转字符串(字典获取(结果["变更"], "roundsStarted", 空)))
  设 折叠乙 为 折叠目标([{"type": "goal/change", "data": 创建, "seq": 1}, {"type": "goal/change", "data": 结果["变更"], "seq": 2}])
  设 视图乙 为 造目标视图(折叠乙, "armed")
  打印("折叠阶段=" + 转字符串(字典获取(视图乙, "phase", 空)))
  设 状态乙 为 字典获取(结果, "新状态", 空)
  字典设置(状态乙, "目标", 视图乙)
  设 决策 为 续续跑决策(状态乙, {"种类": "completed"})
  打印("决策=" + 决策["动作"] + "/" + 决策["理由"])
  打印("提示空=" + 转字符串(字符串长度(决策["提示文本"])))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['工具ok'] == 'True', f'complete 动作应成功\n{out}'
    assert kv['操作'] == 'complete', out
    assert kv['快照阶段'] == 'complete' and kv['快照修订'] == '2', f'快照未推进 revision\n{out}'
    assert kv['已开'] == '0', f'complete 不得改 roundsStarted（折叠会拒）\n{out}'
    assert kv['折叠阶段'] == 'complete', f'变更载荷没有通过 目标折叠 的解码/折叠（fail-loud）\n{out}'
    assert kv['决策'] == '完成/goal-complete', f'目标已 complete 仍想续跑\n{out}'
    assert kv['提示空'] == '0', f'完成分支不应给续跑提示\n{out}'


# --------------------------------------------------------------------------- #
# 7. error / max-steps 理由可区分
# --------------------------------------------------------------------------- #
def test_错误与步数耗尽理由可区分(tmp_path):
    src = BOOT + '''
段落 主:
  设 状态 为 续建续跑状态(主视图(), {})
  设 决策错 为 续续跑决策(状态, {"种类": "error", "原因": "provider 500"})
  设 决策步 为 续续跑决策(状态, {"种类": "max-steps"})
  设 决策怪 为 续续跑决策(状态, {"种类": "whatever"})
  打印("错=" + 决策错["动作"] + "/" + 决策错["理由"])
  打印("步=" + 决策步["动作"] + "/" + 决策步["理由"])
  打印("怪=" + 决策怪["动作"] + "/" + 决策怪["理由"])
  打印("错因=" + 转字符串(字典获取(决策错, "原因", 空)))
  # 已停状态不再续跑
  设 停状态 为 续停止状态(状态)
  设 决策停 为 续续跑决策(停状态, {"种类": "completed"})
  打印("停=" + 决策停["动作"] + "/" + 决策停["理由"])
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['错'] == '停止/error' and kv['步'] == '停止/max-steps', f'错误类理由未区分\n{out}'
    assert kv['怪'] == '停止/unknown-kind', out
    assert kv['错因'] == 'provider 500', out
    assert kv['停'] == '停止/stopped', f'已停目标不应被判续跑\n{out}'


# --------------------------------------------------------------------------- #
# 8. 工具规格 + 注册（name=目标 / alias=goal / schema 硬约束 / 注册后进名单）
# --------------------------------------------------------------------------- #
def test_目标工具规格与注册(tmp_path):
    src = '''
从 目标续跑 导入 续建续跑状态, 续目标工具规格, 续执行目标工具
从 目标工具 导入 注册目标工具, 挂目标台账, 取目标台账, 目标工具处理
从 工具 导入 工具注册表

段落 造视图():
  返回 {"id": "g9", "revision": 1, "objective": "跑绿三条验收", "phase": "active", "maxGoalRounds": 4, "roundsStarted": 0, "createdAt": 0, "updatedAt": 0, "activation": "armed"}

段落 主:
  设 规格 为 续目标工具规格()
  打印("名=" + 规格["name"])
  打印("别名=" + 规格["别名"])
  打印("有描述=" + 转字符串(字符串长度(规格["description"]) > 0))
  设 模式 为 规格["parameters"]
  打印("必填=" + 转字符串(字典获取(模式, "required", 空)))
  打印("附加属性=" + 转字符串(字典获取(模式, "additionalProperties", 空)))
  设 动作项 为 字典获取(字典获取(模式, "properties", 空), "动作", 空)
  打印("枚举=" + 转字符串(字典获取(动作项, "enum", 空)))
  设 表 为 新建 工具注册表()
  注册目标工具(表)
  打印("名单=" + 连接字符串(表.名单(), ","))
  打印("描述数=" + 转字符串(列表长度(表.描述表())))
  设 状态 为 续建续跑状态(造视图(), {})
  挂目标台账(状态)
  打印("挂台账=" + 转字符串(取目标台账() != 空))
  设 处理结果 为 目标工具处理({"动作": "pause", "现在": 9})
  打印("处理ok=" + 转字符串(字典获取(处理结果, "ok", 空)))
  打印("处理说明=" + 转字符串(字符串包含(转字符串(字典获取(处理结果, "content", 空)), "pause")))
  打印("处理操作=" + 转字符串(字典获取(字典获取(处理结果, "变更", 空), "operation", 空)))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['名'] == '目标' and kv['别名'] == 'goal', f'工具名/别名不对\n{out}'
    assert kv['有描述'] == 'True', out
    assert kv['必填'] == "['动作']", f'required 必须是 [动作]\n{out}'
    assert kv['附加属性'] == 'False', f'additionalProperties 必须显式 false（对齐上游 schema）\n{out}'
    assert kv['枚举'] == "['update', 'complete', 'pause']", f'三个动作枚举不对\n{out}'
    assert kv['名单'] == '目标', f'注册后名单应含 目标\n{out}'
    assert kv['描述数'] == '1', out
    assert kv['挂台账'] == 'True', out
    assert kv['处理ok'] == 'True' and kv['处理操作'] == 'pause', f'处理器未走通 pause\n{out}'
    assert kv['处理说明'] == 'True', f'工具结果 content 应含人话说明\n{out}'


# --------------------------------------------------------------------------- #
# 9. 合并目标变更：revision 推进且重置无进展计数
# --------------------------------------------------------------------------- #
def test_合并目标变更重置无进展(tmp_path):
    src = BOOT + '''
段落 主:
  设 状态 为 续建续跑状态(主视图(), {})
  设 状态2 为 续记账(续记账(状态, {"种类": "completed"}), {"种类": "completed"})
  打印("前连续=" + 转字符串(字典获取(状态2, "连续无进展", 空)))
  设 合并后 为 续合并目标变更(状态2, {"revision": 2, "phase": "active", "objective": "改过描述"})
  打印("后连续=" + 转字符串(字典获取(合并后, "连续无进展", 空)))
  打印("后修订=" + 转字符串(字典获取(合并后, "上次修订", 空)))
  打印("后客观=" + 转字符串(字典获取(字典获取(合并后, "目标", 空), "objective", 空)))
  设 决策 为 续续跑决策(合并后, {"种类": "completed"})
  打印("决策=" + 决策["动作"] + "/" + 决策["理由"])
  设 合并2 为 续合并目标变更(合并后, {"revision": 2, "phase": "active"})
  打印("同修订连续=" + 转字符串(字典获取(合并2, "连续无进展", 空)))
主()
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['前连续'] == '2', out
    assert kv['后连续'] == '0' and kv['后修订'] == '2', f'revision 推进应重置无进展\n{out}'
    assert kv['后客观'] == '改过描述', f'变更字段未合并进视图\n{out}'
    assert kv['决策'] == '续跑/round-advance', f'无进展清零后应恢复续跑\n{out}'
    assert kv['同修订连续'] == '0', f'同 revision 合并不应误加无进展\n{out}'

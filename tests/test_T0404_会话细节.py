# -*- coding: utf-8 -*-
"""T-0404 会话细节数据面（纯逻辑）判据。

覆盖：
  - 时算速率：正常 / 耗时 0 / 耗时 < 0 / 输出 0
  - 时格式化时刻：固定浮点秒 → HH:MM:SS（本地时区）
  - 时造细节行：完整 / 缺完成时刻 / 缺速率
  - 时补统计字段：原 6 键不丢 + 新增 4 键 + 纯函数不改入参
  - 时从轮次结果取细节：照 代理.light:503 的真实形状
  - 记完成时间 / 取完成时间：写后能读、旧索引无键返回 "" 不报错
  - 计时器：开始 / 结束

测试写法照抄 tests/test_T0395_会话工作目录.py 的 _run：把光明驱动脚本写进
tmp_path/driver.light，子进程运行，按 k=v 解析 打印() 输出后逐项断言。
"""
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
TIMEOUT_SEC = 120

# 本卡需要的外部兄弟仓（worktree 里没有 ../light、../lightplugin，必须显式给）
_LIGHT_CANDIDATES = [
    os.environ.get('LIGHT_MERGE', ''),
    os.path.join(ROOT, '..', 'light'),
    os.path.expanduser('~/dswork/light'),
    '/home/skywalk/dswork/light',
]
_PLUGIN_CANDIDATES = [
    os.environ.get('LIGHTPLUGIN', ''),
    os.path.join(ROOT, '..', 'lightplugin'),
    os.path.expanduser('~/dswork/lightplugin'),
    '/home/skywalk/dswork/lightplugin',
]


def _first_dir(candidates):
    for c in candidates:
        if c and os.path.isdir(os.path.join(c, 'src')):
            return os.path.normpath(c)
    # lightplugin 的判定不用 src/
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.normpath(c)
    return ''


def _lp(p) -> str:
    return str(p).replace('\\', '/')


def _run(src: str, tmp_path):
    f = tmp_path / 'driver.light'
    f.write_text(src, encoding='utf-8')
    env = {k: v for k, v in os.environ.items() if k not in ('HARNESS_ROOT', 'HARNESS_CWD')}
    light = _first_dir(_LIGHT_CANDIDATES)
    plugin = _first_dir(_PLUGIN_CANDIDATES)
    if light:
        env['LIGHT_MERGE'] = light
    else:
        env.pop('LIGHT_MERGE', None)
    if plugin:
        env['LIGHTPLUGIN'] = plugin
    else:
        env.pop('LIGHTPLUGIN', None)
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
        with open(os.path.join(debug, 'T0404-' + os.path.basename(str(f)) + '.log'),
                  'w', encoding='utf-8') as fh:
            fh.write('rc=' + str(p.returncode) + '\n' + combined)
    except OSError:
        pass
    return p.returncode, combined, kv


BOOT = '''
从 会话细节 导入 时算速率, 时格式化时刻, 时造细节行, 时补统计字段, 时从轮次结果取细节
从 会话细节 导入 时造计时器, 时开始计时, 时结束计时
从 JSON 导入 序列化JSON
'''


# --------------------------------------------------------------------------- #
# 1-4. 时算速率：正常 / 0 / 负 / 输出 0
# --------------------------------------------------------------------------- #
def test_时算速率正常值(tmp_path):
    src = BOOT + '''
设 速率 为 时算速率(128, 3.53)
打印("速率=" + 转字符串(速率))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert abs(float(kv['速率']) - (128 / 3.53)) < 1e-9, out


def test_时算速率耗时为0返回0(tmp_path):
    src = BOOT + '''
打印("值=" + 转字符串(时算速率(128, 0)))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert float(kv['值']) == 0, f'除零保护失效（耗时 0 应返回 0）\n{out}'


def test_时算速率耗时为负返回0(tmp_path):
    src = BOOT + '''
打印("值=" + 转字符串(时算速率(128, -2.5)))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert float(kv['值']) == 0, f'负耗时未归零\n{out}'


def test_时算速率输出为0返回0(tmp_path):
    src = BOOT + '''
打印("值=" + 转字符串(时算速率(0, 2.0)))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert float(kv['值']) == 0, out


# --------------------------------------------------------------------------- #
# 5. 时格式化时刻：固定浮点秒（不用 现在）
# --------------------------------------------------------------------------- #
def test_时格式化时刻固定值(tmp_path):
    src = BOOT + '''
打印("时刻=" + 时格式化时刻(1700000000.0))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    expected = time.strftime('%H:%M:%S', time.localtime(1700000000.0))
    assert kv['时刻'] == expected, f'期望 {expected}，实际 {kv["时刻"]}\n{out}'


# --------------------------------------------------------------------------- #
# 6. 时造细节行：完整 / 缺完成时刻 / 缺速率
# --------------------------------------------------------------------------- #
def test_时造细节行三种形态(tmp_path):
    src = BOOT + '''
设 完整 为 ["开始时刻": 1700000000.0, "完成时刻": 1700000003.53, "耗时秒": 3.53, "速率": 36.26]
设 缺完成 为 ["开始时刻": 1700000000.0, "耗时秒": 3.53, "速率": 36.26]
设 缺速率 为 ["开始时刻": 1700000000.0, "完成时刻": 1700000003.53, "耗时秒": 3.53]
打印("完整=" + 时造细节行(完整))
打印("缺完成=" + 时造细节行(缺完成))
打印("缺速率=" + 时造细节行(缺速率))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    full = kv['完整']
    no_done = kv['缺完成']
    no_rate = kv['缺速率']
    # 完整：四段，顺序固定
    assert full.startswith('开始 20'), f'开头不是「开始 YYYY-MM-DD」：{full}\n{out}'
    assert ' · 完成 ' in full and ' · 3.5s' in full and ' · 36 tok/s' in full, out
    assert full.count(' · ') == 3, f'完整行应有 3 个分隔符：{full}\n{out}'
    # 缺完成：没有「完成」段，其余仍在
    assert '完成 ' not in no_done, f'缺完成时刻仍输出完成段：{no_done}\n{out}'
    assert ' · 3.5s' in no_done and ' · 36 tok/s' in no_done, out
    assert no_done.count(' · ') == 2, out
    # 缺速率：没有 tok/s 段，完成段仍在
    assert 'tok/s' not in no_rate, f'缺速率仍输出 tok/s：{no_rate}\n{out}'
    assert ' · 完成 ' in no_rate and ' · 3.5s' in no_rate, out
    assert no_rate.count(' · ') == 2, out


# --------------------------------------------------------------------------- #
# 7. 时补统计字段：6 键不丢 + 4 键新增 + 纯函数
# --------------------------------------------------------------------------- #
def test_时补统计字段纯函数(tmp_path):
    src = BOOT + '''
设 统计 为 ["种类": "统计", "本轮输入": 900, "本轮输出": 128, "累计总": 1200, "花费": 0.0, "上下文使用率": 0.12]
设 细节 为 ["开始时刻": 1700000000.0, "完成时刻": 1700000003.53, "耗时秒": 3.53, "速率": 36.26]
设 前 为 序列化JSON(统计)
设 补 为 时补统计字段(统计, 细节)
设 后 为 序列化JSON(统计)
设 键表 为 ["种类", "本轮输入", "本轮输出", "累计总", "花费", "上下文使用率"]
设 原键全在 为 真
遍历 键 之 键表:
  如果 字典包含键(补, 键) == 假:
    设 原键全在 为 假
设 新键表 为 ["开始时刻", "完成时刻", "耗时秒", "速率"]
设 新键全在 为 真
遍历 键 之 新键表:
  如果 字典包含键(补, 键) == 假:
    设 新键全在 为 假
打印("前=" + 前)
打印("后=" + 后)
打印("补=" + 序列化JSON(补))
打印("原键全在=" + 转字符串(原键全在))
打印("新键全在=" + 转字符串(新键全在))
打印("键数=" + 转字符串(长(补)))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['原键全在'] == 'True', f'原统计键被丢\n{out}'
    assert kv['新键全在'] == 'True', f'新增键不全\n{out}'
    assert int(kv['键数']) == 10, f'应为 6+4=10 键，实际 {kv["键数"]}\n{out}'
    assert kv['前'] == kv['后'], f'入参字典被修改：前={kv["前"]} 后={kv["后"]}\n{out}'
    filled = json.loads(kv['补'])
    assert filled['种类'] == '统计' and filled['本轮输入'] == 900, out
    assert filled['完成时刻'] == 1700000003.53, out
    assert filled['耗时秒'] == 3.53, out
    assert abs(filled['速率'] - 36.26) < 1e-9, out


# --------------------------------------------------------------------------- #
# 8. 时从轮次结果取细节：照 代理.light:503 的真实形状
# --------------------------------------------------------------------------- #
def test_时从轮次结果取细节(tmp_path):
    src = BOOT + '''
设 轮次结果 为 ["种类": "completed", "步骤数": 2, "输入token": 900, "输出token": 128, "耗时秒": 3.53]
设 细节 为 时从轮次结果取细节(轮次结果, 1700000000.0)
打印("细节=" + 序列化JSON(细节))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    detail = json.loads(kv['细节'])
    assert detail['耗时秒'] == 3.53, f'未复用代理的 耗时秒：{detail}\n{out}'
    assert detail['开始时刻'] == 1700000000.0, out
    assert abs(detail['完成时刻'] - 1700000003.53) < 1e-9, out
    assert abs(detail['速率'] - (128 / 3.53)) < 1e-9, out


# --------------------------------------------------------------------------- #
# 9. 记完成时间 / 取完成时间：写后能读、旧索引无键返回 "" 不报错
# --------------------------------------------------------------------------- #
def test_记完成时间写入与重载(tmp_path):
    src = '''从 会话存储 导入 会话存储, 记完成时间, 取完成时间
从 JSON 导入 序列化JSON
设 库 为 新建 会话存储("''' + _lp(tmp_path) + '''")
设 元 为 库.新建会话("测", "")
设 标识 为 元["id"]
设 旧读 为 取完成时间(库, 标识)
设 写后 为 记完成时间(库, 标识, "2026-11-19T23:01:41")
设 库2 为 新建 会话存储("''' + _lp(tmp_path) + '''")
设 重载 为 取完成时间(库2, 标识)
设 元2 为 库2.取元数据(标识)
打印("旧读=" + 旧读)
打印("写后=" + 取完成时间(库, 标识))
打印("重载=" + 重载)
打印("元=" + 序列化JSON(元2))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert kv['旧读'] == '', f'无「完成时间」键时应返回空串：{kv["旧读"]!r}\n{out}'
    assert kv['写后'] == '2026-11-19T23:01:41', out
    assert kv['重载'] == '2026-11-19T23:01:41', f'重载后丢失\n{out}'
    meta = json.loads(kv['元'])
    # 既有键一个都不能少、类型与值不变
    assert meta['消息数'] == 0, out
    assert meta['文件'] == meta['id'] + '.jsonl', out
    assert meta['创建时间'] and meta['最后更新'], out
    assert meta['标题'] == '测', out
    assert meta['完成时间'] == '2026-11-19T23:01:41', out


def test_旧索引无完成时间键读回是空串(tmp_path):
    sessions = tmp_path / 'sessions'
    sessions.mkdir()
    old_meta = {
        'id': 'old_session_1', '标题': '旧会话',
        '创建时间': '2026-01-01T00:00:00', '最后更新': '2026-01-01T00:00:01',
        '消息数': 0, '文件': 'old_session_1.jsonl',
    }
    (sessions / '_index.json').write_text(
        json.dumps({'会话': [old_meta]}, ensure_ascii=False), encoding='utf-8')
    (sessions / 'old_session_1.jsonl').write_text('', encoding='utf-8')

    src = '''从 会话存储 导入 会话存储, 取完成时间
从 JSON 导入 序列化JSON
设 库 为 新建 会话存储("''' + _lp(tmp_path) + '''")
打印("值=" + 取完成时间(库, "old_session_1"))
打印("元=" + 序列化JSON(库.取元数据("old_session_1")))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'旧索引读回报错 rc={rc}\n{out}'
    assert kv['值'] == '', f'旧索引缺键应返回 ""：{kv["值"]!r}\n{out}'
    assert json.loads(kv['元']) == old_meta, f'旧索引被改动\n{out}'


# --------------------------------------------------------------------------- #
# 10. 计时器：开始 → 结束
# --------------------------------------------------------------------------- #
def test_计时器开始结束(tmp_path):
    src = BOOT + '''
设 计时 为 时造计时器()
打印("初耗时=" + 转字符串(计时["耗时秒"]))
时开始计时(计时)
打印("已开始=" + 转字符串(计时["开始时刻"] > 0))
打印("开始时结束空=" + 转字符串(计时["结束时刻"] == 空))
时结束计时(计时)
设 结束值 为 计时["结束时刻"]
设 开始值 为 计时["开始时刻"]
打印("结束不小于开始=" + 转字符串(结束值 >= 开始值))
打印("耗时非负=" + 转字符串(计时["耗时秒"] >= 0))
打印("耗时等于差=" + 转字符串(计时["耗时秒"] == 结束值 - 开始值))
'''
    rc, out, kv = _run(src, tmp_path)
    assert rc == 0, f'驱动脚本失败 rc={rc}\n{out}'
    assert float(kv['初耗时']) == 0, out
    assert kv['已开始'] == 'True', out
    assert kv['开始时结束空'] == 'True', out
    assert kv['结束不小于开始'] == 'True', out
    assert kv['耗时非负'] == 'True', out
    assert kv['耗时等于差'] == 'True', f'耗时口径不是 结束-开始\n{out}'

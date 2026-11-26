# -*- coding: utf-8 -*-
"""T-0508：工具注册表可逆性（reversibility）风险分级元数据判据。

覆盖四层：
  1. 回填完整性：真实注册表（160 工具）每个工具都有显式档位，
     `未分级` 必须为 0（走了 fail-closed 兜底的就是漏网）；表内档位只许是四级之一；
  2. 查询语义：按档位查询保持登记序、四档并集 = 全集；未知/非字符串/空串/MCP
     的缺省行为明确（MCP 与未知一律 irreversible，fail-closed）；
  3. 注册接口：`附可逆性` / `补可逆性` 在 `建注册表` / `具注册工具` 的同一个工具表
     条目上补 "可逆性" 字段，幂等，不动 级别 / 域 / 处理，执行照常；
  4. 规范文档：docs/风险分级规范.light.md 存在，四级定义与动态判定归属（T-0509/T-0510）
     写得出来——分级规范是可复核的判据，不是口头约定。

只有两条 Light 子进程调用（真实注册表 + 注册接口），避免 xdist 下多个 运行.py
同时编译 .light 触发 worker crash（pytest.ini --timeout=60）。

运行方式：python -m pytest -q tests/test_T0508_可逆性分级.py
Windows 本机若子进程输出触发 GBK 解码错误，加 PYTHONUTF8=1 再跑（不是产物问题）。
平台说明：本判据只跑 python -m pytest，不含 head/grep/awk/!/$() 等 POSIX 语法；
真跑不动再换 192.168.0.88（FreeBSD 15.1），不要因为 exit 255 怀疑产物。
"""
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
DOC = os.path.join(ROOT, 'docs', '风险分级规范.light.md')
TIMEOUT_SEC = 180

# 四级字面值（与 src/工具面装配.light §10.1 对齐）
只读, 可逆, 半可逆, 不可逆 = 'read_only', 'reversible', 'semi', 'irreversible'


def _run(driver, tmp_path, name):
    path = tmp_path / name
    path.write_text(driver, encoding='utf-8')
    env = dict(os.environ)
    env['PYTHONIOENCODING'] = 'utf-8'
    env['PYTHONUTF8'] = '1'
    proc = subprocess.run([sys.executable, RUNNER, str(path)], cwd=ROOT,
                          capture_output=True, text=True, timeout=TIMEOUT_SEC,
                          env=env, encoding='utf-8', errors='replace')
    kv = {}
    for line in proc.stdout.splitlines():
        if '=' in line:
            k, v = line.split('=', 1)
            kv[k.strip()] = v.strip()
    return proc.returncode, proc.stdout + proc.stderr, kv


# ---- Light driver：真实注册表 → 逐名档位 + 统计 + 查询语义 + 缺省行为 ----
REAL_DRIVER = '''
从 总入口 导入 组装注册表
从 工具面装配 导入 工具可逆性, 可逆性统计, 未分级工具, 按可逆性取工具
从 工具面装配 导入 可逆性表, 可逆性级别名表, 是合法可逆性, 是否显式分级, 默认可逆性
从 工具面装配 导入 级只读, 级可逆, 级半可逆, 级不可逆
从 内置核心列表 导入 列表追加, 列表包含
从 内置核心字典 导入 字典键列表

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 首项(表):
  如果 长度(表) == 0:
    返回 ""
  返回 表[0]

段落 主程():
  设 注册表 为 组装注册表()
  设 名表 为 注册表.名单()
  打印 "总数=" + 转字符串(长度(名表))
  打印 "表条数=" + 转字符串(长度(字典键列表(可逆性表)))
  设 统 为 可逆性统计(名表)
  打印 "只读=" + 转字符串(统["read_only"])
  打印 "可逆=" + 转字符串(统["reversible"])
  打印 "半可逆=" + 转字符串(统["semi"])
  打印 "不可逆=" + 转字符串(统["irreversible"])
  打印 "未分级=" + 转字符串(统["未分级"])
  打印 "未分级名=" + 逗号连接(未分级工具(名表))
  # 逐名档位（判据按名取样，不靠整表字符串比对）
  遍历 名 之 名表:
    打印 "档:" + 名 + "=" + 工具可逆性(名)
  # 四档并集 = 全集（不重不漏）
  设 并集 为 []
  遍历 档 之 可逆性级别名表:
    遍历 名 之 按可逆性取工具(名表, 档):
      如果 列表包含(并集, 名) == 假:
        列表追加(并集, 名)
  打印 "并集数=" + 转字符串(长度(并集))
  # 档位合法性：每个工具落在四级之一
  设 非法 为 0
  遍历 名 之 名表:
    如果 是合法可逆性(工具可逆性(名)) == 假:
      设 非法 为 非法 + 1
  打印 "非法档位数=" + 转字符串(非法)
  # 查询语义：保持登记序、未知档空表
  打印 "只读首项=" + 首项(按可逆性取工具(名表, 级只读))
  打印 "不可逆首项=" + 首项(按可逆性取工具(名表, 级不可逆))
  打印 "未知档列表=" + 逗号连接(按可逆性取工具(名表, "danger"))
  # 缺省行为（fail-closed）
  打印 "未知工具档=" + 工具可逆性("完全不存在的工具NNN")
  打印 "非字符串档=" + 工具可逆性(123)
  打印 "空串档=" + 工具可逆性("")
  打印 "MCP档=" + 工具可逆性("mcp__github__list_issues")
  打印 "MCP显式=" + 转字符串(是否显式分级("mcp__github__list_issues"))
  打印 "已登记显式=" + 转字符串(是否显式分级("读文件"))
  打印 "未知显式=" + 转字符串(是否显式分级("完全不存在的工具NNN"))
  打印 "默认可逆性=" + 默认可逆性
  打印 "合法semi=" + 转字符串(是合法可逆性("semi"))
  打印 "非法danger=" + 转字符串(是合法可逆性("danger"))
  打印 "非法空串=" + 转字符串(是合法可逆性(""))
  打印 "非法数字=" + 转字符串(是合法可逆性(123))
主程()
'''


# ---- Light driver：注册接口回填 "可逆性" 字段 + 不动执行路径 ----
REG_DRIVER = '''
从 工具执行 导入 建注册表, 具注册工具, 级公开, 执行工具, 建执行器, 策略滑动窗, 工具之域
从 工具面装配 导入 附可逆性, 补可逆性, 工具之可逆性
从 内置核心字典 导入 字典包含键

段落 回显(参数, 令牌):
  返回 "ok"

段落 主程():
  设 注册 为 建注册表()
  具注册工具(注册, "读文件", 级公开, 回显)
  具注册工具(注册, "甲工具", 级公开, 回显, 空, "shell")
  设 补数 为 补可逆性(注册)
  打印 "补数=" + 转字符串(补数)
  打印 "补数二次=" + 转字符串(补可逆性(注册))
  打印 "读文件档=" + 附可逆性(注册, "读文件")
  打印 "甲档=" + 工具之可逆性(注册, "甲工具")
  打印 "读文件之档=" + 工具之可逆性(注册, "读文件")
  打印 "读文件域=" + 工具之域(注册, "读文件")
  打印 "甲域=" + 工具之域(注册, "甲工具")
  打印 "读文件级别=" + 转字符串(注册["工具表"]["读文件"]["级别"])
  打印 "读文件有处理=" + 转字符串(注册["工具表"]["读文件"]["处理"] != 空)
  打印 "条目有可逆性键=" + 转字符串(字典包含键(注册["工具表"]["读文件"], "可逆性"))
  打印 "未知附=" + 转字符串(附可逆性(注册, "不存在的工具"))
  打印 "非字典附=" + 转字符串(附可逆性(123, "读文件"))
  设 执行器 为 建执行器(10, 1000, 0, 策略滑动窗, 注册)
  设 结果 为 执行工具(执行器, "读文件", 级公开, "tester", 空)
  打印 "调用状态=" + 结果["状态"]
  打印 "调用结果=" + 转字符串(结果["结果"])
主程()
'''


@pytest.fixture(scope='module')
def 真实注册表(tmp_path_factory):
    d = tmp_path_factory.mktemp('t0508_real')
    return _run(REAL_DRIVER, d, 't0508_real.light')


def test_分级回填完整且可复核(真实注册表):
    rc, out, kv = 真实注册表
    assert rc == 0, out
    total = int(kv.get('总数', '0'))
    assert total >= 150, ('注册表规模异常（任务卡实测 160）', total, out)
    # 1) 回填完整性：没人在走 fail-closed 兜底
    assert kv.get('未分级') == '0', ('有工具没落档位：' + kv.get('未分级名', ''), out)
    assert kv.get('未分级名') == '', out
    assert int(kv.get('非法档位数', '1')) == 0, ('档位不是四级之一', out)
    # 2) 四档并集 = 全集
    assert kv.get('并集数') == kv.get('总数'), ('按档查询漏了工具', out)
    # 3) 计数基线（真实注册表 160 工具；新增工具要同时落表并更新本基线）
    assert kv.get('只读') == '72', out
    assert kv.get('可逆') == '36', out
    assert kv.get('半可逆') == '5', out
    assert kv.get('不可逆') == '47', out
    assert (int(kv['只读']) + int(kv['可逆']) + int(kv['半可逆']) +
            int(kv['不可逆'])) == total, out
    assert int(kv.get('表条数', '0')) >= 150, out


def test_关键工具档位与不可逆风险面(真实注册表):
    rc, out, kv = 真实注册表
    assert rc == 0, out
    期望 = {
        # 只读：读盘/查询/纯计算
        '读文件': 只读, '搜索文件': 只读, '待办列出': 只读,
        '获取环境变量': 只读, '预设列出': 只读, '风险判定': 只读,
        # 可逆：新增/登记/会话态
        '切换会话': 可逆, '待办添加': 可逆, '提醒注册': 可逆,
        '登记产物': 可逆, '附件上传': 可逆, '图片生成': 可逆,
        # 半可逆：恢复要额外步骤
        '压缩摘要': 半可逆, '附件下载': 半可逆, '录音控制': 半可逆,
        # 不可逆：覆盖/删除/外发/进程动作
        '写文件': 不可逆, '编辑文件': 不可逆, 'todo_write': 不可逆,
        '待办删除': 不可逆, '待办完成': 不可逆, '预设保存': 不可逆,
        '预设删除': 不可逆, 'Webhook删除': 不可逆, 'Webhook触发': 不可逆,
        'bash': 不可逆, 'SSH执行': 不可逆, '执行Python脚本': 不可逆,
        '屏幕操作': 不可逆, '目标推进': 不可逆,
    }
    for 名, 档 in 期望.items():
        assert kv.get('档:' + 名) == 档, (名, kv.get('档:' + 名), 档, out)


def test_查询语义与fail_closed兜底(真实注册表):
    rc, out, kv = 真实注册表
    assert rc == 0, out
    # 保持登记序：只读子集首项是注册表里的第一个只读工具
    assert kv.get('只读首项') == '读文件', out
    assert kv.get('不可逆首项') == 'bash', out
    # 未知档位返回空表（不抛错）
    assert kv.get('未知档列表') == '', out
    # 未知/非字符串/空串/MCP 一律按 fail-closed 兜底
    assert kv.get('未知工具档') == 不可逆, out
    assert kv.get('非字符串档') == 不可逆, out
    assert kv.get('空串档') == 不可逆, out
    assert kv.get('MCP档') == 不可逆, out
    assert kv.get('默认可逆性') == 不可逆, out
    # 显式分级口径：表内与 MCP 算显式；未知不算
    assert kv.get('已登记显式') in ('True', '真'), out
    assert kv.get('MCP显式') in ('True', '真'), out
    assert kv.get('未知显式') in ('False', '假'), out
    # 档位合法性判定
    assert kv.get('合法semi') in ('True', '真'), out
    for 键 in ('非法danger', '非法空串', '非法数字'):
        assert kv.get(键) in ('False', '假'), (键, kv.get(键), out)


def test_注册接口回填不改变执行(tmp_path):
    rc, out, kv = _run(REG_DRIVER, tmp_path, 't0508_reg.light')
    assert rc == 0, out
    # 回填幂等：同一注册表补两遍，条数不变
    assert kv.get('补数') == '2', out
    assert kv.get('补数二次') == '2', out
    # 档位挂在同一个工具表条目上（字段 "可逆性"），可读写
    assert kv.get('条目有可逆性键') in ('True', '真'), out
    assert kv.get('读文件档') == 只读, out
    assert kv.get('读文件之档') == 只读, out
    assert kv.get('甲档') == 不可逆, out
    # 分级是纯元数据：级别 / 域 / 处理 一字不动
    assert kv.get('读文件级别') == 'public', out
    assert kv.get('读文件域') == '其他', out
    assert kv.get('甲域') == 'shell', out
    assert kv.get('读文件有处理') in ('True', '真'), out
    # 未登记工具 / 非字典注册 返回空，不抛错
    assert kv.get('未知附') in ('None', '空', ''), out
    assert kv.get('非字典附') in ('None', '空', ''), out
    # 执行路径不变：权限 → 限流 → 取消 → 执行 → 审计
    assert kv.get('调用状态') == 'ok', out
    assert kv.get('调用结果') == 'ok', out


def test_分级规范文档可复核():
    assert os.path.exists(DOC), '缺 docs/风险分级规范.light.md'
    文 = open(DOC, encoding='utf-8').read()
    assert len(文.splitlines()) >= 40, '规范文档过薄，判不出标准'
    for 档 in (只读, 可逆, 半可逆, 不可逆):
        assert 档 in 文, ('规范缺档位定义：' + 档)
    # 判定标准与边界案例要写得出，而不是只列名字
    for 词 in ('回滚', '影响面', '确认', 'fail-closed', '未分级'):
        assert 词 in 文, ('规范缺判定维度：' + 词)
    # 动态判定归属必须写明：本卡只定静态分级
    assert 'T-0509' in 文 and 'T-0510' in 文, '规范没写动态判定归属'
    assert '可逆性表' in 文 and '附可逆性' in 文, '规范没写注册接口落点'

# -*- coding: utf-8 -*-
"""R175（T-0175）B3 路：工作区成员判定单测。

上游：packages/workspace/workspace/src/entity.ts（dsh-v0.2.1-rc.3）——
`sessionPath(id) === record.path` 改为 `candidateMatches(id, path)`：
已记账的子会话即使完整 cwd 解析不出（路径分量缺失），也保留归属。
被测模块：src/工作区成员.light。
"""
from test_support import (
    run_light_source, assert_success, assert_failure, out_contains,
)

_导入 = '从 工作区成员 导入 成员_候选匹配, 成员_名单, 成员_裁决'


def test_候选匹配_同名保留_异名剔除_解析不出保留归属():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 家 为 "/home/u/proj"
  打印("同名=" + 转字符串(成员_候选匹配({"标识": "S1", "规范路径": "/home/u/proj", "可解析": 真}, 家)))
  打印("异名=" + 转字符串(成员_候选匹配({"标识": "S2", "规范路径": "/home/u/other", "可解析": 真}, 家)))
  打印("缺失=" + 转字符串(成员_候选匹配({"标识": "S3", "规范路径": "/home/u/gone", "可解析": 假}, 家)))
''')
    assert_success(r)
    out_contains(r, "同名=True")
    out_contains(r, "异名=False")
    out_contains(r, "缺失=True")


def test_名单_按候选匹配过滤():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 录 为 {"路径": "/home/u/proj", "成员": [{"标识": "S1", "规范路径": "/home/u/proj", "可解析": 真}, {"标识": "S2", "规范路径": "/home/u/other", "可解析": 真}, {"标识": "S3", "规范路径": "/home/u/gone", "可解析": 假}]}
  打印("名单=" + 连接字符串(成员_名单(录), ","))
''')
    assert_success(r)
    out_contains(r, "名单=S1,S3")


def test_裁决_过滤掉成员即非未变_以及变更后重算():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 录 为 {"路径": "/home/u/proj", "成员": [{"标识": "S1", "规范路径": "/home/u/proj", "可解析": 真}, {"标识": "S2", "规范路径": "/home/u/other", "可解析": 真}]}
  设 判 为 成员_裁决(录, 空)
  打印("未变=" + 转字符串(判["未变"]) + " 成员=" + 连接字符串(判["成员"], ","))
  设 变更 为 {"路径": "/home/u/alg", "成员": [{"标识": "S1", "规范路径": "/home/u/proj", "可解析": 真}, {"标识": "S9", "规范路径": "/home/u/alg", "可解析": 真}]}
  设 判2 为 成员_裁决(录, 变更)
  打印("判2未变=" + 转字符串(判2["未变"]) + " 成员=" + 连接字符串(判2["成员"], ","))
''')
    assert_success(r)
    # 同对象但过滤掉 1 个成员 → 长度变了，上游不抛 unchanged 哨兵
    out_contains(r, "未变=False 成员=S1")
    out_contains(r, "判2未变=False 成员=S9")


def test_裁决_同对象且长度不变才算未变():
    r = run_light_source(_导入 + '''
段落 主程序():
  设 录 为 {"路径": "/home/u/proj", "成员": [{"标识": "S1", "规范路径": "/home/u/proj", "可解析": 真}, {"标识": "S3", "规范路径": "/home/u/gone", "可解析": 假}]}
  打印("未变=" + 转字符串(成员_裁决(录, 空)["未变"]))
  设 录二 为 {"路径": "/home/u/proj", "成员": [{"标识": "S1", "规范路径": "/home/u/proj", "可解析": 真}]}
  打印("短未变=" + 转字符串(成员_裁决(录, 录二)["未变"]))
''')
    assert_success(r)
    out_contains(r, "未变=True")
    out_contains(r, "短未变=False")


def test_成员_缺字段直抛名称错误():
    # 光明是动态语言：项缺 可解析 键时按既定约定直抛（非静默当 真）
    r = run_light_source(_导入 + '''
段落 主程序():
  成员_候选匹配({"标识": "S1", "规范路径": "/a"}, "/a")
''')
    assert_failure(r)
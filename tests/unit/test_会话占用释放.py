# -*- coding: utf-8 -*-
"""T-0531：直调处理器且不消费流时，会话占用必须在 ≤5s 内释放。

判据（走 运行.py 子进程，按仓库既有单例 import 口径）：
  1. 发一条 stream=true 请求，返回体里的「流响应」完全不迭代；
  2. 按 10ms 轮询 src/会话队列.light 的 队是否忙，要求 5s 内翻回不忙；
  3. 同会话再发一条 stream=false，要求 200（不是 202）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_support import run_light_source, assert_success, out_contains  # noqa: E402

SOURCE = '''
从 web服务器 导入 全局服务, 路由处理器
从 总入口 导入 组装注册表
从 会话存储 导入 会话存储
从 会话队列 导入 队是否忙, 队排队深度
从 文件系统 导入 创建目录, 目录存在, 路径连接
从 字符串处理 导入 编码
从 JSON 导入 解析JSON
从 流 导入 造块开始, 造文本增量, 造块结束, 造结束, 造停止原因
从 线程 导入 线程休眠
从 os 导入 _exit

类 模拟客户端:
  属性 模型名 等于 "deepseek-chat"
  属性 应答序号 等于 0
  段落 构造:
    设 己.模型名 为 "deepseek-chat"
    设 己.应答序号 为 0
  段落 对话响应(消息表, 选项表, 工具表):
    设 回应文本 为 "会话占用释放 mock 回复"
    返回 [造块开始(0, "text"), 造文本增量(0, 回应文本), 造块结束(0, ["type": "text", "text": 回应文本]), 造结束(造停止原因())]

段落 造请求(方法, 路径, 体):
  返回 ["方法": 方法, "路径": 路径, "头": {}, "体": 体]

段落 聊天体(会话标识, 流式):
  设 对象 为 "{\\"model\\":\\"buddy/hy3\\",\\"messages\\":[{\\"role\\":\\"user\\",\\"content\\":\\"hi\\"}],\\"stream\\":" + 流式
  如果 会话标识 != "":
    设 对象 为 对象 + ",\\"session_id\\":\\"" + 会话标识 + "\\""
  返回 编码(对象 + "}")

异步 段落 主测试:
  设 基 为 当前目录()
  设 根 为 路径连接(基, "_orr_sess")
  设 界面库 为 路径连接(基, "_orr_webui")
  设 数据根 为 路径连接(基, "_orr_data")
  如果 目录存在(根) == 假: 创建目录(根)
  如果 目录存在(界面库) == 假: 创建目录(界面库)
  如果 目录存在(数据根) == 假: 创建目录(数据根)
  设 元数据 为 ["configured": 1, "mock": 1, "model": "deepseek-flash", "endpoint": "http://127.0.0.1:9/v1/chat/completions", "has_key": 0]
  全局服务.配置(新建 模拟客户端(), 组装注册表(), 根, 30.0, 界面库, 元数据, 路径连接(基, "_orr.env"))
  全局服务.设置会话库(新建 会话存储(数据根))
  设 建会话 为 等待 路由处理器(造请求("POST", "/api/sessions", 编码("{}")))
  设 会话标识 为 解析JSON(建会话["体"])["id"]

  # ① 流式直调：拿到 200 即止，绝不迭代「流响应」
  设 首轮 为 等待 路由处理器(造请求("POST", "/v1/chat/completions", 聊天体(会话标识, "true")))
  打印("STATUS1=" + 转字符串(首轮["状态"]))

  # ② 轮询会话队列的真实忙标志，不等固定秒数
  设 闸门 为 全局服务.取队列闸门()
  设 开始 为 时间戳()
  设 已释放 为 假
  遍历 序号 之 范围(500):
    如果 队是否忙(闸门, 会话标识) == 假:
      设 已释放 为 真
      跳出
    线程休眠(0.01)
  设 耗时 为 时间戳() - 开始
  打印("FREE=" + 转字符串(已释放))
  打印("ELAPSED=" + 转字符串(耗时))
  打印("DEPTH=" + 转字符串(队排队深度(闸门, 会话标识)))
  如果 已释放 == 假:
    抛出 新建 错误("断言失败[5s 内会话仍忙]")
  如果 耗时 > 5:
    抛出 新建 错误("断言失败[释放超过 5s]")

  # ③ 同一会话再发非流式请求：必须直接 200，不能 202 入队
  设 次轮 为 等待 路由处理器(造请求("POST", "/v1/chat/completions", 聊天体(会话标识, "false")))
  打印("STATUS2=" + 转字符串(次轮["状态"]))
  打印("BODY2=" + 转字符串(次轮["体"]))
  如果 次轮["状态"] != 200:
    抛出 新建 错误("断言失败[后续请求被判忙]：实际=" + 转字符串(次轮["状态"]) + " 期望=200")

  全局服务.停止()
  打印("SESSION_RELEASE_PASS")
  # T-0526 的兜底唤醒线程退出修复属另一张卡；本子进程只验会话占用，
  # 断言全部打完后主动收口，避免非守护线程把解释器钉在 threading._shutdown。
  _exit(0)

异步 运行 主测试()
'''


def test_直调不消费流_占用释放后同会话可继续():
    # web服务器 的 .light 模块图编译在本机约需 25~35s；这里给子进程留出编译余量，
    # pytest 自身的 60s 硬超时（pytest.ini）不动。
    r = run_light_source(SOURCE, timeout=50, env={'PYTHONUNBUFFERED': '1'})
    assert_success(r)
    out_contains(r, 'STATUS1=200')
    out_contains(r, 'FREE=True')
    out_contains(r, 'STATUS2=200')
    out_contains(r, 'SESSION_RELEASE_PASS')
    elapsed = float(next(line.split('=', 1)[1] for line in r.output.splitlines()
                         if line.startswith('ELAPSED=')))
    assert elapsed <= 5.0, f'占用释放耗时 {elapsed:.3f}s 超过 5s'

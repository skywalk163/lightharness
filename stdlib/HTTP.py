# -*- coding: utf-8 -*-
"""
光明标准库 - HTTP 请求封装模块

提供 HTTP 客户端请求功能，包括 GET/POST/PUT/DELETE 方法，
请求头设置、超时控制等。

R-流式改造：新增 HTTPPost流式 —— 逐帧读 SSE 并回调调用方，供 web chat
路径把模型增量实时推给浏览器。非流式 HTTPPost 行为零改动。
"""

import urllib.request
import urllib.parse
import urllib.error
import json
from typing import Optional, Dict, Any, Union, Callable


def HTTP获取(url: str, 超时: int = 30, 请求头: Dict[str, str] = None) -> Dict[str, Any]:
    """
    发送 HTTP GET 请求

    参数:
        url: 请求地址
        超时: 超时秒数（默认30）
        请求头: 自定义请求头字典

    返回:
        包含状态码、响应头和响应体的字典

    示例:
        HTTP获取('https://api.example.com/data')
    """
    try:
        req = urllib.request.Request(url, method='GET')
        if 请求头:
            for k, v in 请求头.items():
                req.add_header(k, v)
        with urllib.request.urlopen(req, timeout=超时) as resp:
            响应体 = resp.read().decode('utf-8')
            return {
                '状态码': resp.status,
                '响应头': dict(resp.headers),
                '响应体': 响应体,
            }
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP 请求失败 [{e.code}]: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL 错误: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"HTTP GET 请求异常: {e}")


def HTTP获取JSON(url: str, 超时: int = 30, 请求头: Dict[str, str] = None) -> Any:
    """
    发送 HTTP GET 请求并解析 JSON 响应

    参数:
        url: 请求地址
        超时: 超时秒数（默认30）
        请求头: 自定义请求头字典

    返回:
        解析后的 JSON 数据
    """
    结果 = HTTP获取(url, 超时, 请求头)
    try:
        return json.loads(结果['响应体'])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败: {e}")


def HTTP发送(url: str, 方法: str = 'POST', 数据: Any = None,
             编码: str = 'utf-8', 超时: int = 30,
             请求头: Dict[str, str] = None,
             JSON模式: bool = True) -> Dict[str, Any]:
    """
    发送 HTTP 请求（支持 POST/PUT/DELETE）

    参数:
        url: 请求地址
        方法: 请求方法（POST/PUT/DELETE）
        数据: 请求体数据（字典或字符串）
        编码: 编码方式（默认 utf-8）
        超时: 超时秒数（默认30）
        请求头: 自定义请求头字典
        JSON模式: 是否自动将数据序列化为 JSON

    返回:
        包含状态码、响应头和响应体的字典
    """
    try:
        if 数据 is not None:
            if JSON模式 and isinstance(数据, (dict, list)):
                数据体 = json.dumps(数据, ensure_ascii=False).encode(编码)
                if 请求头 is None:
                    请求头 = {}
                if 'Content-Type' not in 请求头:
                    请求头['Content-Type'] = 'application/json; charset=utf-8'
            elif isinstance(数据, str):
                数据体 = 数据.encode(编码)
            else:
                数据体 = str(数据).encode(编码)
        else:
            数据体 = None

        req = urllib.request.Request(url, data=数据体, method=方法)
        if 请求头:
            for k, v in 请求头.items():
                req.add_header(k, v)

        with urllib.request.urlopen(req, timeout=超时) as resp:
            响应体 = resp.read().decode('utf-8')
            return {
                '状态码': resp.status,
                '响应头': dict(resp.headers),
                '响应体': 响应体,
            }
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP 请求失败 [{e.code}]: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL 错误: {e.reason}")
    except Exception as e:
        raise RuntimeError(f"HTTP {方法} 请求异常: {e}")


def HTTP发送JSON(url: str, 方法: str = 'POST', 数据: Any = None,
                  超时: int = 30, 请求头: Dict[str, str] = None) -> Any:
    """
    发送 HTTP 请求并以 JSON 格式返回响应

    参数:
        url: 请求地址
        方法: 请求方法（POST/PUT/DELETE）
        数据: 请求体数据
        超时: 超时秒数（默认30）
        请求头: 自定义请求头字典

    返回:
        解析后的 JSON 数据
    """
    结果 = HTTP发送(url, 方法, 数据, 超时=超时, 请求头=请求头)
    try:
        return json.loads(结果['响应体'])
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败: {e}")


def HTTPPost(url: str, 数据: Any = None, 超时: int = 30,
             请求头: Dict[str, str] = None) -> Dict[str, Any]:
    """发送 HTTP POST 请求（快捷方式）"""
    return HTTP发送(url, 'POST', 数据, 超时=超时, 请求头=请求头)


def HTTPPost流式(url: str, 数据: Any = None, 超时: int = 30,
                 请求头: Dict[str, str] = None,
                 每帧回调: Callable = None) -> Dict[str, Any]:
    """发送 HTTP POST 请求并逐帧读取 SSE 响应。

    与 HTTPPost 的差别：本函数不一次性 read() 整个响应体，而是按行读取，
    遇到 SSE 帧边界（空行）就把该帧的 data 载荷交给 `每帧回调`。

    参数:
        每帧回调: 可调用对象，每帧调用一次，入参为 data 载荷字符串；
                  返回假值可提前中止读取（用于用户点"停止"）。
                  回调里抛出的异常会向上传递。

    返回:
        与 HTTPPost 同形状的字典，另外多一个 '帧数' 字段便于断言。
    """
    数据体 = json.dumps(数据, ensure_ascii=False).encode('utf-8') if isinstance(数据, (dict, list)) else (数据.encode('utf-8') if isinstance(数据, str) else str(数据).encode('utf-8'))
    req = urllib.request.Request(url, data=数据体, method='POST')
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    if 请求头:
        for k, v in 请求头.items():
            req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=超时) as resp:
            帧数 = 0
            数据行 = []
            with resp:
                while True:
                    原始行 = resp.readline()
                    if not 原始行:
                        break
                    行 = 原始行.decode('utf-8', errors='replace').rstrip('\r\n')
                    if 行 == '':
                        # 空行 = 帧边界
                        if 数据行 and 每帧回调 is not None:
                            载荷 = '\n'.join(数据行)
                            帧数 += 1
                            if 每帧回调(载荷) is False:
                                break
                        数据行 = []
                        continue
                    if 行.startswith(':'):
                        continue
                    if 行.startswith('data:'):
                        值 = 行[5:]
                        if 值.startswith(' '):
                            值 = 值[1:]
                        数据行.append(值)
            # 收尾：流结束前若还有未以空行收口的帧，也投递一次
            if 数据行 and 每帧回调 is not None:
                每帧回调('\n'.join(数据行))
                帧数 += 1
            return {
                '状态码': resp.status,
                '响应头': dict(resp.headers),
                '响应体': '',
                '帧数': 帧数,
            }
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP 请求失败 [{e.code}]: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL 错误: {e.reason}")


def HTTPPut(url: str, 数据: Any = None, 超时: int = 30,
            请求头: Dict[str, str] = None) -> Dict[str, Any]:
    """发送 HTTP PUT 请求（快捷方式）"""
    return HTTP发送(url, 'PUT', 数据, 超时=超时, 请求头=请求头)


def HTTPDelete(url: str, 超时: int = 30,
               请求头: Dict[str, str] = None) -> Dict[str, Any]:
    """发送 HTTP DELETE 请求（快捷方式）"""
    return HTTP发送(url, 'DELETE', 超时=超时, 请求头=请求头)


def HTTP下载文件(url: str, 保存路径: str, 超时: int = 60) -> str:
    """
    下载文件到本地

    参数:
        url: 文件 URL
        保存路径: 本地保存路径
        超时: 超时秒数（默认60）

    返回:
        保存路径
    """
    try:
        urllib.request.urlretrieve(url, 保存路径)
        return 保存路径
    except Exception as e:
        raise RuntimeError(f"文件下载失败: {e}")


def HTTP检查状态码(状态码: int) -> str:
    """
    返回 HTTP 状态码的文本描述

    参数:
        状态码: HTTP 状态码

    返回:
        状态码描述
    """
    状态码映射 = {
        200: '成功', 201: '已创建', 204: '无内容',
        301: '永久重定向', 302: '临时重定向', 304: '未修改',
        400: '错误请求', 401: '未授权', 403: '禁止访问',
        404: '未找到', 405: '方法不允许', 408: '请求超时',
        409: '冲突', 429: '请求过多',
        500: '服务器内部错误', 502: '网关错误',
        503: '服务不可用', 504: '网关超时',
    }
    return 状态码映射.get(状态码, f'未知状态码 ({状态码})')


def HTTP构建查询参数(参数: Dict[str, str]) -> str:
    """
    构建 URL 查询参数字符串

    参数:
        参数: 参数字典

    返回:
        查询字符串（不含前导 ?）
    """
    return urllib.parse.urlencode(参数)


def HTTP拼接URL(基础URL: str, 路径: str) -> str:
    """
    拼接基础 URL 和路径

    参数:
        基础URL: 基础 URL
        路径: 路径部分

    返回:
        完整 URL
    """
    return urllib.parse.urljoin(基础URL, 路径)


def HTTP解析URL(url: str) -> Dict[str, str]:
    """
    解析 URL 为各组成部分

    参数:
        url: 完整 URL

    返回:
        包含 scheme/netloc/path/params/query/fragment 的字典
    """
    解析结果 = urllib.parse.urlparse(url)
    return {
        '协议': 解析结果.scheme,
        '域名': 解析结果.netloc,
        '路径': 解析结果.path,
        '参数': 解析结果.params,
        '查询': 解析结果.query,
        '片段': 解析结果.fragment,
    }


def HTTP编码URL(字符串: str) -> str:
    """URL 编码"""
    return urllib.parse.quote(字符串)


def HTTP解码URL(字符串: str) -> str:
    """URL 解码"""
    return urllib.parse.unquote(字符串)


__all__ = [
    'HTTP获取', 'HTTP获取JSON', 'HTTP发送', 'HTTP发送JSON',
    'HTTPPost', 'HTTPPost流式', 'HTTPPut', 'HTTPDelete',
    'HTTP下载文件', 'HTTP检查状态码',
    'HTTP构建查询参数', 'HTTP拼接URL', 'HTTP解析URL',
    'HTTP编码URL', 'HTTP解码URL',
]
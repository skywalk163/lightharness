"""
高级文件模块 - 提供文件操作、目录分析、系统命令检查等高级功能
"""
import os
import shutil
import platform
from typing import Dict, Union


def 复制文件(源文件: str, 目标文件: str) -> None:
    """复制文件

    参数:
        源文件: 源文件路径
        目标文件: 目标文件路径
    """
    shutil.copy2(源文件, 目标文件)


def 磁盘使用情况(路径: str = '.') -> Dict[str, Union[int, str]]:
    """获取磁盘使用情况

    参数:
        路径: 要检查的路径，默认为当前目录

    返回:
        包含总空间、已用空间、可用空间的字典（字节）
    """
    if not os.path.exists(路径):
        raise FileNotFoundError(f"路径不存在: {路径}")
    统计 = shutil.disk_usage(路径)
    return {
        '总空间': 统计.total,
        '已用空间': 统计.used,
        '可用空间': 统计.free,
    }


def 目录大小(路径: str) -> int:
    """计算目录下所有文件的总大小（字节）

    参数:
        路径: 目录路径

    返回:
        总字节数
    """
    总大小 = 0
    for 根目录, 子目录, 文件列表 in os.walk(路径):
        for 文件名 in 文件列表:
            文件路径 = os.path.join(根目录, 文件名)
            try:
                总大小 += os.path.getsize(文件路径)
            except (OSError, FileNotFoundError):
                pass
    return 总大小


def 命令存在(命令: str) -> bool:
    """检查系统命令是否存在

    参数:
        命令: 要检查的命令名称

    返回:
        是否存在
    """
    return shutil.which(命令) is not None


def 文件树(路径: str, 显示大小: bool = False, 前缀: str = '', 是否最后: bool = True) -> str:
    """生成目录树结构文本

    参数:
        路径: 目录路径
        显示大小: 是否显示文件大小
        前缀: 行前缀（内部递归用）
        是否最后: 当前项是否为最后一项（内部递归用）

    返回:
        目录树字符串
    """
    if not os.path.exists(路径):
        return f'路径不存在: {路径}'
    if not os.path.isdir(路径):
        return f'不是目录: {路径}'

    结果 = []
    基本名 = os.path.basename(路径) or 路径
    结果.append(基本名)

    try:
        条目列表 = sorted(os.listdir(路径))
    except PermissionError:
        结果.append(f'{前缀}└── [权限不足]')
        return '\n'.join(结果)

    for i, 条目 in enumerate(条目列表):
        是否最后一项 = (i == len(条目列表) - 1)
        完整路径 = os.path.join(路径, 条目)
        连接线 = '└── ' if 是否最后一项 else '├── '
        子前缀 = '    ' if 是否最后一项 else '│   '

        if os.path.isdir(完整路径):
            结果.append(f'{前缀}{连接线}{条目}/')
            子树 = 文件树(完整路径, 显示大小, 前缀 + 子前缀, 是否最后一项)
            子树行 = 子树.split('\n')
            for 行 in 子树行[1:]:
                结果.append(行)
        else:
            if 显示大小:
                try:
                    大小 = os.path.getsize(完整路径)
                    结果.append(f'{前缀}{连接线}{条目} ({大小} 字节)')
                except OSError:
                    结果.append(f'{前缀}{连接线}{条目} (无法获取大小)')
            else:
                结果.append(f'{前缀}{连接线}{条目}')

    return '\n'.join(结果)
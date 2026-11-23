"""
光明标准库 - 外部命令模块

封装 subprocess 模块，提供执行外部命令的便捷接口。
"""

import subprocess
import sys
import os
import locale
from typing import List, Dict, Optional, Union, Tuple


class 命令结果:
    """命令执行结果"""
    
    def __init__(self, 返回码: int, 标准输出: str = "", 标准错误: str = ""):
        self.返回码 = 返回码
        self.标准输出 = 标准输出
        self.标准错误 = 标准错误
    
    @property
    def 是否成功(self) -> bool:
        """是否执行成功（返回码为0）"""
        return self.返回码 == 0

    
    def __bool__(self) -> bool:
        return self.是否成功
    
    def __repr__(self) -> str:
        return f"命令结果(返回码={self.返回码}, 成功={self.是否成功})"


def _智能解码(数据, 编码: str = None) -> str:
    """把子进程输出解码为文本，任何字节序列都不抛异常。

    Windows 上子进程输出常是 GBK（cp936），按 utf-8 严格解码会崩掉
    subprocess 的 reader 线程（UnicodeDecodeError，且输出静默丢失）。
    策略：显式给了编码就用它（坏字节替换）；否则先试 utf-8，再试本地
    编码，Windows 下再补一次 GBK（Python 3.14 起 UTF-8 模式默认开启，
    locale 也返回 utf-8，本地兜底必须显式列出 GBK），最后替换坏字节。
    """
    if 数据 is None:
        return ""
    if isinstance(数据, str):
        return 数据
    if 编码:
        try:
            return 数据.decode(编码)
        except (UnicodeDecodeError, LookupError):
            return 数据.decode(编码, errors='replace')
    尝试表 = ['utf-8', locale.getpreferredencoding(False)]
    if sys.platform == 'win32':
        尝试表 += ['gbk', 'mbcs']
    for 尝试 in 尝试表:
        try:
            return 数据.decode(尝试)
        except (UnicodeDecodeError, LookupError):
            continue
    return 数据.decode('utf-8', errors='replace')


def _终止进程树(进程) -> None:
    """超时终止：把**整棵进程树**停掉，而不是只 kill 宿主 shell。

    为什么必须收树（T-0442 缺陷 3 实测）：`python -c "...time.sleep(8)"` 配 2 秒
    超时，旧实现只 kill 掉 cmd.exe/sh，孙进程还活着并继续占着 stdout/stderr 管道，
    紧接着的 communicate() 就要一直等到孙进程自己退出 —— 超时形同虚设。

    手段：Windows 用 taskkill /F /T；POSIX 先 SIGTERM 整个进程组，留 1 秒宽限，
    仍活着再 SIGKILL。任何一步失败都不外抛（超时语义优先）。
    """
    import signal as _signal

    if os.name == "nt":
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(进程.pid)],
                           capture_output=True, timeout=5)
        except Exception:  # noqa: BLE001
            pass
    else:
        try:
            os.killpg(os.getpgid(进程.pid), _signal.SIGTERM)
        except Exception:  # noqa: BLE001
            pass
        # 轮询而不是 wait()：进程组还活着时 wait() 可能卡住，且会与随后的
        # communicate() 抢同一条管道（死锁）。这里只给 1 秒宽限。
        import time as _time
        宽限截止 = _time.time() + 1.0
        while _time.time() < 宽限截止:
            if 进程.poll() is not None:
                break
            _time.sleep(0.05)
        if 进程.poll() is None:
            try:
                os.killpg(os.getpgid(进程.pid), _signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass
    try:
        进程.kill()
    except Exception:  # noqa: BLE001
        pass


def 执行命令(
    命令: Union[str, List[str]],
    捕获输出: bool = True,
    工作目录: str = None,
    环境变量: Dict[str, str] = None,
    超时: float = None,
    编码: str = None,
) -> 命令结果:
    """
    执行外部命令

    参数:
        命令: 命令字符串或命令列表
        捕获输出: 是否捕获标准输出和标准错误
        工作目录: 工作目录
        环境变量: 环境变量字典（会合并到当前环境）
        超时: 超时时间（秒）
        编码: 输出编码；None（默认）表示自动识别（utf-8 → 本地编码）

    返回:
        命令结果对象
    """
    命令列表 = 命令 if isinstance(命令, list) else 命令
    shell = isinstance(命令, str)

    # R100 路 B：撤回 9/25 批次的 PowerShell 包装。
    # 该包装声称「兼容更多 bash 命令别名」，但实际破坏了两条既有契约：
    #   1. 精确退出码——`"py" -c "exit(3)"` 被 PS 当 ParserError，恒返回 1
    #      （PS -Command 不透传原生进程退出码）；
    #   2. cmd 语法——`echo a & echo b` 在 PS 里 `&` 非法。
    # test_子进程码 / test_子进程流式 的注释明写「POSIX sh 与 cmd.exe 双平台绿」，
    # shell=True 在 Windows 上本就走 cmd.exe。如未来确需 PS 能力，应显式让
    # 调用方写 powershell 命令（下方 startswith('powershell') 分支仍放行）。
    环境 = None
    if 环境变量:
        环境 = dict(os.environ)
        环境.update(环境变量)

    try:
        弹出参数 = {
            "shell": shell,
            # T-0442 缺陷 4：子进程 stdin 置 DEVNULL。此前不传即**继承父进程 stdin**，
            # git 的 `Username for 'http://...': ` 之类交互式提示会静默挂到超时。
            "stdin": subprocess.DEVNULL,
            "cwd": 工作目录,
            "env": 环境,
        }
        if 捕获输出:
            弹出参数["stdout"] = subprocess.PIPE
            弹出参数["stderr"] = subprocess.PIPE
        if os.name == "nt":
            # 新进程组：超时可用 taskkill /T 收整棵进程树（cmd.exe 不会 exec 子命令）
            弹出参数["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
        else:
            # 新会话/进程组：超时可 killpg 收整组，不留孤儿占着管道
            弹出参数["start_new_session"] = True
        进程 = subprocess.Popen(命令列表, **弹出参数)
    except FileNotFoundError:
        return 命令结果(
            返回码=-1,
            标准错误="命令未找到",
        )
    except Exception as e:
        return 命令结果(
            返回码=-1,
            标准错误=str(e),
        )

    try:
        标准输出, 标准错误 = 进程.communicate(timeout=超时)
        if not 捕获输出:
            return 命令结果(返回码=进程.returncode)
        return 命令结果(
            返回码=进程.returncode,
            标准输出=_智能解码(标准输出, 编码),
            标准错误=_智能解码(标准错误, 编码),
        )
    except subprocess.TimeoutExpired:
        # T-0442 缺陷 3：超时必须让调用方「看得懂」，且**真的把命令停下来**。
        #   旧行为：run() 的 timeout 只 kill 宿主 shell（Windows 上 cmd.exe 不 exec
        #   子命令），孙进程继续占着 stdout 管道，communicate() 要等它们自己结束
        #   —— 实测「2 秒超时 + sleep 8」实际耗了 8 秒以上；返回的又只有一句
        #   「命令超时（30秒）」、partial 输出全丢。
        #   现行为：先收整棵进程树，再回收管道拿回被杀前的部分输出，并在错误字段
        #   写明「命令超时被终止」+ 秒数 + 终止语义。
        _终止进程树(进程)
        try:
            部分输出, 部分错误 = 进程.communicate()
        except Exception:  # noqa: BLE001 —— 回收失败不影响超时语义
            部分输出, 部分错误 = None, None
        说明 = (f"命令超时被终止：执行超过 {超时} 秒仍未结束，已强制终止子进程"
                f"（退出码 -1，POSIX 下等价于收到 SIGTERM/SIGKILL 被杀）")
        错误文本 = 说明
        部分错误文本 = _智能解码(部分错误, 编码)
        if 部分错误文本:
            错误文本 = 错误文本 + "\n[超时前 stderr]\n" + 部分错误文本
        return 命令结果(
            返回码=-1,
            标准输出=_智能解码(部分输出, 编码),
            标准错误=错误文本,
        )
    except Exception as e:  # noqa: BLE001 —— 读取/回收异常不外抛，转成命令结果
        try:
            进程.kill()
        except Exception:  # noqa: BLE001
            pass
        return 命令结果(
            返回码=-1,
            标准错误=str(e),
        )


def 执行命令并获取输出(
    命令: Union[str, List[str]],
    工作目录: str = None,
    环境变量: Dict[str, str] = None,
    超时: float = None,
    编码: str = None,
) -> str:
    """
    执行命令并返回标准输出
    
    参数:
        命令: 命令字符串或列表
        工作目录: 工作目录
        环境变量: 环境变量
        超时: 超时时间
        编码: 输出编码
    
    返回:
        标准输出字符串
    """
    结果 = 执行命令(命令, 捕获输出=True, 工作目录=工作目录, 环境变量=环境变量, 超时=超时, 编码=编码)
    return 结果.标准输出.strip()


def 命令是否成功(
    命令: Union[str, List[str]],
    工作目录: str = None,
    超时: float = None,
) -> bool:
    """
    检查命令是否执行成功
    
    参数:
        命令: 命令字符串或列表
        工作目录: 工作目录
        超时: 超时时间
    
    返回:
        是否成功
    """
    结果 = 执行命令(命令, 捕获输出=False, 工作目录=工作目录, 超时=超时)
    return 结果.是否成功


def 管道执行(
    命令列表: List[Union[str, List[str]]],
    捕获输出: bool = True,
    工作目录: str = None,
    编码: str = None,
) -> 命令结果:
    """
    管道执行多个命令（前一个的输出是后一个的输入）
    
    参数:
        命令列表: 命令列表
        捕获输出: 是否捕获输出
        工作目录: 工作目录
        编码: 输出编码
    
    返回:
        最后一个命令的结果
    """
    if not 命令列表:
        return 命令结果(返回码=-1, 标准错误="命令列表为空")
    
    上一个输出 = None
    最后结果 = 命令结果(返回码=0)
    
    for i, 命令 in enumerate(命令列表):
        cmd = 命令 if isinstance(命令, list) else 命令
        shell = isinstance(命令, str)
        
        输入数据 = 上一个输出.encode(编码 or 'utf-8') if 上一个输出 is not None else None

        try:
            结果 = subprocess.run(
                cmd,
                shell=shell,
                input=输入数据,
                capture_output=捕获输出,
                cwd=工作目录,
            )

            if 捕获输出:
                上一个输出 = _智能解码(结果.stdout, 编码)
                最后结果 = 命令结果(
                    返回码=结果.returncode,
                    标准输出=上一个输出 or "",
                    标准错误=_智能解码(结果.stderr, 编码),
                )
            else:
                最后结果 = 命令结果(返回码=结果.returncode)
            
            if 结果.returncode != 0:
                break
        except Exception as e:
            最后结果 = 命令结果(返回码=-1, 标准错误=str(e))
            break
    
    return 最后结果


def 后台执行(
    命令: Union[str, List[str]],
    工作目录: str = None,
    环境变量: Dict[str, str] = None,
) -> subprocess.Popen:
    """
    后台执行命令（不等待完成）
    
    参数:
        命令: 命令字符串或列表
        工作目录: 工作目录
        环境变量: 环境变量
    
    返回:
        Popen对象
    """
    cmd = 命令 if isinstance(命令, list) else 命令
    shell = isinstance(命令, str)
    
    环境 = None
    if 环境变量:
        环境 = dict(os.environ)
        环境.update(环境变量)
    
    return subprocess.Popen(
        cmd,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=工作目录,
        env=环境,
    )


def 等待进程(进程: subprocess.Popen, 超时: float = None) -> 命令结果:
    """
    等待后台进程完成
    
    参数:
        进程: Popen对象
        超时: 超时时间
    
    返回:
        命令结果
    """
    try:
        标准输出, 标准错误 = 进程.communicate(timeout=超时)
        return 命令结果(
            返回码=进程.returncode,
            标准输出=_智能解码(标准输出),
            标准错误=_智能解码(标准错误),
        )
    except subprocess.TimeoutExpired:
        # 超时语义：kill + 返回 码=-1（用例按此判定「超时未成功」）。
        #
        # ⚠️ 只 kill() 不回收是不够的（第45轮实测 L-167）：
        #   kill 之后进程进入「已终止但未回收」状态——POSIX 上成为僵尸占着
        #   PID 表项，Windows 上管道读线程仍在跑且 Popen 析构时会抛
        #   ResourceWarning；全量回归连跑数百个用例时，这些残留会累积并
        #   抬高空闲系统负载，进而让**后续**用例的进程启动变慢——
        #   test_子进程后台 偶发红（等待 5s 超时）就是这条链上的表现。
        #   故 kill 后再 communicate() 一次：既回收僵尸，也排空管道。
        进程.kill()
        try:
            进程.communicate()
        except Exception:  # noqa: BLE001 —— 回收失败不影响超时语义
            pass
        return 命令结果(返回码=-1, 标准错误=f"进程超时（{超时}秒）")


def 命令存在(命令名: str) -> bool:
    """
    检查命令是否存在（在PATH中可找到）
    
    参数:
        命令名: 命令名称
    
    返回:
        是否存在
    """
    if os.name == 'nt':
        命令 = f"where {命令名}"
    else:
        命令 = f"which {命令名}"
    
    return 命令是否成功(命令)


__all__ = [
    '命令结果',
    '执行命令',
    '执行命令并获取输出',
    '命令是否成功',
    '管道执行',
    '后台执行',
    '等待进程',
    '命令存在',
]

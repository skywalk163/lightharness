# -*- coding: utf-8 -*-
"""T-0456 收口接线判据：把 T-0448~T-0455 的模块真正接进 5 个热点文件，并用「真起服务」钉住。

判据（对应任务卡）：
1. 装配面（进程内探针）：组装注册表("standard") 名单 ≥ 20 且含四件套 + 本批新增工具 + 既有族；
   minimal 恰为 ["bash"]；brainstorm 无 写文件、无 bash。
2. 真实请求面（E2E，真起服务 + mock LLM）：读 request/header 事件，
   工具模式条数 ≥ 20 且含编辑工具的线名，系统提示含临时工作目录 AGENTS.md 的哨兵串。
3. 向后兼容：无 AGENTS.md 的目录起服务，系统提示与 默认系统提示文本() 逐字相同。
4. 装配期单个工具挂载失败 → 只记日志 + 跳过，其余工具照常挂上（红线）。
5. 反跑锚点（静态）：工具名到叶子 必须「先查 叶子映射」、预设保留工具 必须调用
   未映射默认保留 —— 删掉任一处，判据 1 的对应断言与 5 的锚点立红（反跑记录见 .hive/summary.md）。

判据口径与任务卡的两处差异（已写进 .hive/summary.md，并给出反跑）：
- 卡面写「工具模式 含 编辑文件」：工具模式走 兼容注册表 的线名（DeepSeek 只收 ASCII），
  编辑文件 的线名是 edit_file，故断言 edit_file 在场 + 注册名 编辑文件 在场（两处合起来等价且更严）。
- 卡面写 todo_write / ask_user_question / 交付登记：本仓现状是 造待办工具 需要所属 agent 会话、
  造提问工具定义 需要宿主提问器、交付呈现 的证据在 lightplugin（生产挂载因同名撞车剔除）。
  本卡不造假工具，改为断言这些族**真实存在的注册名**（待办添加 / 提问提交 / present）并单列缺口。
"""
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNNER = os.path.join(ROOT, '运行.py')
SERVER_SCRIPT = os.path.join(ROOT, 'examples', '运行Web服务器.light')
TOKEN = 't0456-token'
BOOT_TIMEOUT = 180
SENTINEL = 'LH-SENTINEL-0454'


# --------------------------------------------------------------------------- #
# 进程内探针（照抄 tests/test_T0419_工具叶子拆分.py 的 driver 手法）
# --------------------------------------------------------------------------- #

_ASSEMBLY_DRIVER = '''
从 总入口 导入 组装注册表, 工具名到叶子
从 核心工具 导入 核心工具装配失败

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 主程():
  设 标 为 组装注册表("standard")
  打印 "STD_COUNT=" + 转字符串(长度(标.名单()))
  打印 "STD=" + 逗号连接(标.名单())
  设 小 为 组装注册表("minimal")
  打印 "MIN=" + 逗号连接(小.名单())
  设 脑 为 组装注册表("brainstorm")
  打印 "BRAIN=" + 逗号连接(脑.名单())
  设 扁 为 组装注册表("ptc")
  打印 "PTC_COUNT=" + 转字符串(长度(扁.名单()))
  打印 "MAP_EDIT=" + 逗号连接(工具名到叶子("编辑文件"))
  打印 "MAP_JOB=" + 逗号连接(工具名到叶子("job_start"))
  打印 "MAP_SKILL=" + 逗号连接(工具名到叶子("skill"))
  打印 "MAP_WEB=" + 逗号连接(工具名到叶子("web_search"))
  打印 "MAP_TODO=" + 逗号连接(工具名到叶子("待办添加"))
  打印 "MAP_ASK=" + 逗号连接(工具名到叶子("提问提交"))
  打印 "MAP_PRESENT=" + 逗号连接(工具名到叶子("present"))
  打印 "MAP_GOAL=" + 逗号连接(工具名到叶子("目标"))
  打印 "FAILS=" + 转字符串(长度(核心工具装配失败()))
  打印 "WIRE_EDIT=" + 转字符串(标.线名("编辑文件"))
  设 模式表 为 标.描述表()
  打印 "WIRE_COUNT=" + 转字符串(长度(模式表))
主程()
'''

# 装配期失败隔离：坏注册表在指定工具名上抛错，其余工具必须照常挂上
_FAIL_DRIVER = '''
从 核心工具 导入 注册全部核心工具, 核心工具装配失败

类 坏注册表:
  属性 表 等于 空
  属性 坏名 等于 ""

  段落 构造(坏名):
    设 己.表 为 []
    设 己.坏名 为 坏名

  段落 注册(条目):
    如果 条目["name"] == 己.坏名:
      抛出 "模拟挂载失败"
    己.表.追加(条目["name"])

  段落 名单():
    返回 己.表

段落 逗号连接(表):
  设 文本 为 ""
  设 序号 为 0
  遍历 项 之 表:
    如果 序号 > 0:
      设 文本 为 文本 + ","
    设 文本 为 文本 + 转字符串(项)
    设 序号 为 序号 + 1
  返回 文本

段落 主程():
  设 表 为 新建 坏注册表("skill")
  设 成 为 注册全部核心工具(表)
  打印 "RC=" + 转字符串(成)
  打印 "NAMES=" + 逗号连接(表.名单())
  打印 "FAILS=" + 逗号连接(核心工具装配失败())
主程()
'''

# 向后兼容对照组：无参 默认系统提示文本() 的输出（逐字）
_CONTRACT_DRIVER = '''
从 总入口 导入 默认系统提示文本

段落 主程():
  打印 "BEGIN"
  打印 默认系统提示文本()
  打印 "END"
主程()
'''


def _env(work=None):
    env = {k: v for k, v in os.environ.items()
           if k not in ('HARNESS_ROOT', 'HARNESS_CWD', 'HARNESS_PERMISSION_MODE',
                        'HARNESS_WEB_TOKEN', 'HARNESS_ENDPOINT', 'HARNESS_API_KEY',
                        'HARNESS_MODEL', 'HARNESS_MODEL_CONTEXT_WINDOW', 'HARNESS_HOME',
                        'DSH_HOME', 'AGENTS_HOME', 'HARNESS_PRESET')}
    here = ROOT
    for _ in range(6):
        here = os.path.dirname(here)
        if not here or here == os.path.dirname(here):
            break
        for key, repo in (('LIGHTPLUGIN', 'lightplugin'), ('LIGHT_MERGE', 'light-merge')):
            cand = os.path.join(here, repo)
            if os.path.isdir(cand) and key not in env:
                env[key] = cand
    env['PYTHONIOENCODING'] = 'utf-8'
    return env


def _run_light(source, tmp_path, name, cwd=None):
    path = tmp_path / (name + '.light')
    path.write_text(source, encoding='utf-8')
    proc = subprocess.run([sys.executable, RUNNER, str(path)],
                          cwd=str(cwd or ROOT), capture_output=True, text=True,
                          timeout=300, env=_env())
    kv = {}
    for line in (proc.stdout or '').splitlines():
        if '=' in line and not line.startswith('['):
            k, v = line.split('=', 1)
            kv.setdefault(k.strip(), v.strip())
    return proc.returncode, (proc.stdout or '') + (proc.stderr or ''), kv


def _missing_module(out):
    """只认「兄弟仓没放到位」这一种缺失（生产挂载 只在 lightplugin 仓里），别把真正的导入回归吞成 skip。"""
    return ('生产挂载' in out) and ('No module named' in out or 'ModuleNotFound' in out or '导入失败' in out)


@pytest.fixture(scope='module')
def work():
    p = pathlib.Path(tempfile.mkdtemp(prefix='t0456'))
    try:
        yield p
    finally:
        if os.environ.get('T0456_KEEP'):
            print('KEEP:', p)
        else:
            shutil.rmtree(p, ignore_errors=True)


# --------------------------------------------------------------------------- #
# 1. 装配面
# --------------------------------------------------------------------------- #

def test_标准预设工具面不再是四个(work):
    rc, out, kv = _run_light(_ASSEMBLY_DRIVER, work, 'assembly')
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓：装配层用例请在 192.168.0.88 上跑')
    assert rc == 0, out
    names = [x for x in kv.get('STD', '').split(',') if x]
    assert int(kv['STD_COUNT']) >= 20, ('standard 工具面仍少于 20', kv['STD_COUNT'], names)
    assert len(names) >= 20
    # 既有四件套
    for need in ('bash', '读文件', '写文件', '搜索文件'):
        assert need in names, ('standard 丢了既有工具 ' + need, out)
    # 本批 T-0449~T-0452 新增工具
    for need in ('编辑文件', 'job_start', 'job_output', 'job_kill', 'skill', 'web_search', 'web_fetch'):
        assert need in names, ('standard 缺本批新增工具 ' + need, out)
    # 既有族（卡面 todo_write / ask_user_question / 交付登记 在本仓的真实注册名，见模块头）
    for need in ('待办添加', '提问提交', 'present', '提醒注册', '派发子任务'):
        assert need in names, ('standard 缺既有族工具 ' + need, out)
    # 未映射默认保留（反跑 B）：没有叶子依据的真实工具必须活下来，否则又回到「148 砍成 4」
    assert 'SSH执行' in names, ('未映射工具被无条件注销（未映射默认保留 没接上）', out)


def test_叶子映射覆盖新工具(work):
    rc, out, kv = _run_light(_ASSEMBLY_DRIVER, work, 'assembly2')
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓')
    assert rc == 0, out
    assert kv.get('MAP_EDIT') == 'tool-fs-write', kv
    assert kv.get('MAP_JOB') == 'tool-jobs', kv
    assert kv.get('MAP_SKILL') == 'tool-skill', kv
    assert kv.get('MAP_WEB') == 'tool-web', kv
    assert kv.get('MAP_PRESENT') == 'present', kv
    # 既有口径未被接线改掉
    assert kv.get('MAP_TODO') == 'tool-todo', kv
    assert kv.get('MAP_ASK') == 'tool-ask-user', kv
    assert kv.get('MAP_GOAL') == 'tool-goal', kv
    # 线名：编辑文件 → edit_file（DeepSeek API 只收 ASCII，中文名会 400）
    assert kv.get('WIRE_EDIT') == 'edit_file', kv
    assert int(kv.get('WIRE_COUNT', '0')) >= 20, kv


def test_minimal与brainstorm仍然收紧(work):
    rc, out, kv = _run_light(_ASSEMBLY_DRIVER, work, 'assembly3')
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓')
    assert rc == 0, out
    assert [x for x in kv.get('MIN', '').split(',') if x] == ['bash'], out
    brain = [x for x in kv.get('BRAIN', '').split(',') if x]
    assert '写文件' not in brain, ('brainstorm 仍有写文件', out)
    assert 'bash' not in brain, ('brainstorm 仍有 bash', out)
    assert '读文件' in brain and '搜索文件' in brain, out


def test_装配期单工具失败不整体失败(work):
    rc, out, kv = _run_light(_FAIL_DRIVER, work, 'failiso')
    if rc != 0 and _missing_module(out):
        pytest.skip('本机缺 lightplugin 兄弟仓')
    assert rc == 0, ('单工具挂载失败不该让整个装配抛出去', out)
    assert kv.get('RC') == 'True', out
    names = [x for x in kv.get('NAMES', '').split(',') if x]
    assert 'skill' not in names, ('模拟失败的工具不该被挂上', out)
    for need in ('bash', '读文件', '写文件', '搜索文件', '编辑文件', 'job_start', 'web_search', 'present'):
        assert need in names, ('一个工具失败不该连累 ' + need, out)
    assert 'skill' in kv.get('FAILS', ''), ('失败必须留底（记日志 + 跳过），不许静默', out)


def test_反跑锚点_两条接线路径都在(work):
    src_in = (pathlib.Path(ROOT) / 'src' / '总入口.light').read_text(encoding='utf-8')
    body = src_in.split('段落 工具名到叶子(名字):', 1)[1].split('段落 ', 1)[0]
    assert '叶子映射(名字)' in body, ('工具名到叶子 必须先查 工具面装配.叶子映射（反跑锚点）', body[:400])
    keep = src_in.split('段落 预设保留工具(注册表, 预设标识):', 1)[1].split('段落 ', 1)[0]
    assert '未映射默认保留(预设标识)' in keep, ('预设保留工具 必须按 未映射默认保留 决定未映射工具去留（反跑锚点）', keep[:400])
    assert '装配日志行(' in keep, ('注销结果必须打 [装配] 日志（反跑锚点）', keep[:400])
    report = src_in.split('段落 装配日志行(', 1)[1].split('段落 ', 1)[0]
    assert '装配报告(' in report, ('日志的「未映射」口径必须来自 工具面装配.装配报告（反跑锚点）', report[:400])


# --------------------------------------------------------------------------- #
# 2/3. 真实请求面（E2E，真起服务 + 脚本化 mock LLM）
# --------------------------------------------------------------------------- #

_MOCK = r'''
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

计数 = {"n": 0}


def 文本块(t):
    return [{"choices": [{"index": 0, "delta": {"content": t}, "finish_reason": None}]},
            {"choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}]


class 处理器(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self.rfile.read(n or 0)
        计数["n"] += 1
        块 = 文本块("收到，我先读代码。")
        体 = "".join("data: " + json.dumps(c, ensure_ascii=False) + "\n\n" for c in 块)
        体 = (体 + "data: [DONE]\n\n").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Content-Length", str(len(体)))
        self.end_headers()
        self.wfile.write(体)


服务 = ThreadingHTTPServer(("127.0.0.1", 0), 处理器)
print(服务.server_address[1], flush=True)
服务.serve_forever()
'''


class _Mock:
    def __init__(self, work):
        self.script = work / 'mockllm_t0456.py'
        self.script.write_text(_MOCK, encoding='utf-8')
        self.proc = subprocess.Popen([sys.executable, '-u', str(self.script)],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True, encoding='utf-8', cwd=str(work))
        self.port = self._port()

    def _port(self, timeout=60):
        end = time.time() + timeout
        while time.time() < end:
            line = self.proc.stdout.readline()
            if line and line.strip().isdigit():
                return int(line.strip())
            if self.proc.poll() is not None:
                raise RuntimeError('mock 起不来：' + (self.proc.stderr.read() or '')[-500:])
        raise RuntimeError('mock 端口超时')

    @property
    def endpoint(self):
        return f'http://127.0.0.1:{self.port}/chat/completions'

    def stop(self):
        try:
            self.proc.kill(); self.proc.wait(timeout=10)
        except Exception:
            pass


class _Server:
    def __init__(self, home, cwd, llm):
        self.home = home
        self.cwd = cwd
        # 每个服务实例独占端口文件：本文件里 srv 与「向后兼容」用例先后各起一次服务，
        # 共用 home/port.txt 会让后起的那个 _port() 读到**仍在运行的前一个服务**的端口，
        # 于是请求打到旧服务（旧服务 cwd 带 AGENTS.md 哨兵），兼容性断言假红。
        self.port_file = home / ('port-%s.txt' % uuid.uuid4().hex[:8])
        self.log_path = home / 'server.log'
        env = _env(home)
        env.update({
            'HARNESS_WEB_TOKEN': TOKEN, 'HARNESS_WEB_NO_OPEN': '1',
            'HARNESS_PORT_FILE': str(self.port_file), 'HARNESS_HOME': str(home),
            'HARNESS_WEB_LIFETIME': '900', 'HARNESS_WEB_MOCK': '0',
            'HARNESS_ENDPOINT': llm.endpoint, 'HARNESS_API_KEY': 'mock-key',
            'HARNESS_MODEL': 'mock', 'HARNESS_MODEL_CONTEXT_WINDOW': '50000',
        })
        self._log = open(self.log_path, 'w', encoding='utf-8')
        self.proc = subprocess.Popen([sys.executable, RUNNER, SERVER_SCRIPT],
                                     stdout=self._log, stderr=subprocess.STDOUT,
                                     text=True, encoding='utf-8', cwd=str(cwd), env=env)
        self.port = self._port()

    def _port(self):
        end = time.time() + BOOT_TIMEOUT
        while time.time() < end:
            if self.proc.poll() is not None:
                log = self.log()
                if _missing_module(log):
                    pytest.skip('本机缺 lightplugin/light-merge 兄弟仓：真起服务用例请在 192.168.0.88 等带兄弟仓的机器上跑')
                raise RuntimeError('服务提前退出：' + log[-2000:])
            try:
                raw = self.port_file.read_text(encoding='utf-8').strip()
            except OSError:
                raw = ''
            if raw:
                try:
                    with socket.create_connection(('127.0.0.1', int(raw)), timeout=1):
                        return int(raw)
                except OSError:
                    pass
            time.sleep(0.2)
        log = self.log()
        if _missing_module(log):
            pytest.skip('本机缺 lightplugin/light-merge 兄弟仓：真起服务用例请在 192.168.0.88 等带兄弟仓的机器上跑')
        raise RuntimeError('服务 180s 未起：' + log[-2000:])

    def log(self):
        try:
            self._log.flush()
            return self.log_path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            return ''

    def post(self, body, timeout=180):
        hs = {'Content-Type': 'application/json; charset=utf-8', 'X-Auth-Token': TOKEN}
        req = urllib.request.Request(f'http://127.0.0.1:{self.port}/v1/chat/completions',
                                     data=json.dumps(body, ensure_ascii=False).encode('utf-8'),
                                     method='POST', headers=hs)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status, resp.read().decode('utf-8', 'replace')
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode('utf-8', 'replace')

    def stop(self):
        try:
            self.proc.kill(); self.proc.wait(timeout=15)
        except Exception:
            pass
        try:
            self._log.close()
        except Exception:
            pass


def _requests(path):
    """JSONL 落盘用英语键（type/seq/data，会话格式 V4），内存事件才是 类型/数据 中文键。"""
    rows = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            pass
    out = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        kind = r.get('type') if 'type' in r else r.get('类型')
        if kind != 'request/header':
            continue
        data = r.get('data') if 'data' in r else r.get('数据')
        if isinstance(data, dict):
            out.append({'数据': data})
    return out


def _session_file(home, sid):
    hits = [p for p in home.rglob('session.jsonl') if p.parent.name == sid]
    assert hits, f'找不到会话 JSONL：{sid}（{home}）\n' + '\n'.join(str(p) for p in home.rglob('*'))
    return max(hits, key=lambda p: p.stat().st_mtime)


@pytest.fixture(scope='module')
def llm(work):
    m = _Mock(work)
    try:
        yield m
    finally:
        m.stop()


@pytest.fixture(scope='module')
def srv(work, llm):
    """带 AGENTS.md 哨兵的工作目录（仓库根找不到 .git 也无妨：项目根回退为工作目录）。"""
    cwd = work / 'repo_with_agents'
    cwd.mkdir(parents=True, exist_ok=True)
    (cwd / 'AGENTS.md').write_text(SENTINEL + '\n仓库规矩：先读再改，别整文件重写。\n', encoding='utf-8')
    s = _Server(work, cwd, llm)
    try:
        yield s
    finally:
        s.stop()


@pytest.mark.timeout(300)
def test_真实请求面工具模式与指令段(srv, work):
    sid = 't0456-e2e'
    st, raw = srv.post({'messages': [{'role': 'user', 'content': 'T0456-PROBE 看一眼工具面'}],
                        'stream': True, 'session_id': sid, '工作目录': str(srv.cwd)})
    assert st == 200, (raw[:2000], srv.log()[-3000:])
    heads = _requests(_session_file(work, sid))
    assert heads, ('请求里没有 request/header 事件（说明装配链没跑到）', srv.log()[-3000:])
    head = heads[-1]['数据']
    tools = head.get('工具模式') or []
    names = []
    for t in tools:
        fn = t.get('function') if isinstance(t, dict) else None
        if isinstance(fn, dict):
            names.append(fn.get('name'))
    assert len(names) >= 20, ('工具模式仍不足 20（死代码没接上）', len(names), names)
    assert 'edit_file' in names, ('工具模式里没有编辑工具（编辑文件 的线名应为 edit_file）', names)
    prompt = head.get('系统提示') or ''
    assert len(prompt) > 0, ('系统提示为空', head)
    assert SENTINEL in prompt, ('系统提示没带上 AGENTS.md 指令段（T-0455 接线没生效）', prompt[:600])
    assert '工具调用规则' in prompt, ('通用契约段丢了（顺序/拼接写反了）', prompt[-600:])


_CONTRACT_FROM_SERVER = None


@pytest.mark.timeout(300)
def test_真实请求面_无指令文件时逐字向后兼容(work, llm):
    """判据 3：没有 AGENTS.md 的目录起服务，系统提示 == 默认系统提示文本()。"""
    empty = work / 'repo_no_agents'
    empty.mkdir(parents=True, exist_ok=True)
    rc, out, kv = _run_light(_CONTRACT_DRIVER, work, 'contract', cwd=empty)
    assert rc == 0, out
    assert 'BEGIN' in out and 'END' in out, ('对照组 driver 没跑出来', out)
    contract = out.split('BEGIN\n', 1)[1].rsplit('\nEND', 1)[0]
    assert contract.strip(), out
    s = _Server(work, empty, llm)
    try:
        sid = 't0456-compat'
        st, raw = s.post({'messages': [{'role': 'user', 'content': 'T0456-COMPAT'}],
                          'stream': True, 'session_id': sid, '工作目录': str(empty)})
        assert st == 200, (raw[:1500], s.log()[-3000:])
        heads = _requests(_session_file(work, sid))
        assert heads, s.log()[-3000:]
        head = heads[-1]['数据']
        assert head.get('系统提示') == contract, (
            '无指令文件时系统提示必须与 默认系统提示文本() 逐字相同（向后兼容）',
            repr(head.get('系统提示'))[:400], repr(contract)[:400])
    finally:
        s.stop()



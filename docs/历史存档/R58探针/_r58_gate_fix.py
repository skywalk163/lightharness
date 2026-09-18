# -*- coding: utf-8 -*-
"""R58 路M 收尾：0.82 装 aiohttp + 定向验证 test_http_client + flaky 重跑 test_重派与心跳 ×10。
复用同步0.82.py 的 SSH 连接模式。"""
import os, re, sys, time, io
from pathlib import Path

ROOT = Path(r'G:\dswork\duan-light-merge')
sys.path.insert(0, str(ROOT / 'lightharness' / 'scripts'))
import paramiko

# 凭据：项目根 .env
env = {}
for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()
user = env['SSH_USER_AI']
pw = env['SSH_PASS_AI']
host = '192.168.0.82'

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect(host, port=22, username=user, password=pw, timeout=20)

def run(cmd, timeout=900):
    print('>>>', cmd[:160])
    stdin, stdout, stderr = cli.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode('utf-8', 'replace')
    err = stderr.read().decode('utf-8', 'replace')
    rc = stdout.channel.recv_exit_status()
    return rc, out, err

# 1. 装 aiohttp
rc, out, err = run('/usr/local/bin/python3.12 -m pip install --no-input aiohttp 2>&1 | tail -3; echo __RC__=${PIPESTATUS[0]}')
print('[aiohttp] rc=%s' % rc)
print(out[-500:])

# 2. 导入实证
rc, out, err = run('/usr/local/bin/python3.12 -c "import aiohttp; print(\'AIOHTTP_OK\', aiohttp.__version__)"')
print('[import] rc=%s %s' % (rc, out.strip()[-80:]))

# 3. 定向 test_http_client.py（同步副本 130354）
rc, out, err = run('cd /tmp/r44-20260918-130354/light-merge && export PYTHONIOENCODING=utf-8 && '
                   '/usr/local/bin/python3.12 -m pytest tests/test_http_client.py -q --tb=line '
                   '-p no:cacheprovider -o addopts= 2>&1 | tail -6; echo __RC__=${PIPESTATUS[0]}')
print('[http_client] rc=%s' % rc)
print(out[-600:])

# 4. flaky 重跑 ×10（单条不算全量）
rc, out, err = run('cd /tmp/r44-20260918-130354/light-merge && export PYTHONIOENCODING=utf-8 && '
                   'for i in $(seq 1 10); do '
                   '/usr/local/bin/python3.12 -m pytest "tests/test_distributed_eval_light.py::test_重派与心跳_杀节点后重派且无静默丢条" '
                   '-q --tb=no -p no:cacheprovider -o addopts= > /tmp/flaky_$i.log 2>&1; '
                   'echo "run$i rc=$?"; done')
print('[flaky x10]')
print(out[-1200:])

cli.close()
print('[done]')

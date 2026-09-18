# -*- coding: utf-8 -*-
"""R57 定向验证：在 0.82（FreeBSD）上执行命令的小助手。

用法:
    python _r57_082.py "<shell 命令>" [超时秒]

凭据从工作区 .env 读取（SSH_USER_AI / SSH_PASS_AI），不落日志。
输出：远端 stdout/stderr + 退出码。
"""
import io, sys, pathlib, paramiko

ENV_PATH = pathlib.Path(r'G:\dswork\duan-light-merge\.env')
env = {}
for line in io.open(ENV_PATH, encoding='utf-8'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

host = env.get('82SSH_HOST') or '192.168.0.82'
cmd = sys.argv[1]
timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 900

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(host, port=22, username=env['SSH_USER_AI'], password=env['SSH_PASS_AI'],
          timeout=15, banner_timeout=15, auth_timeout=15)
chan = c.get_transport().open_session()
chan.settimeout(timeout)
chan.exec_command(cmd)
out = b''
while True:
    try:
        chunk = chan.recv(65536)
    except Exception:
        break
    if not chunk:
        break
    out += chunk
    sys.stdout.write(chunk.decode('utf-8', 'replace'))
    sys.stdout.flush()
rc = chan.recv_exit_status()
sys.stdout.write(f'\n__REMOTE_RC__={rc}\n')
c.close()

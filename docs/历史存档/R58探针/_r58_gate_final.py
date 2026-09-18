# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, r'G:\dswork\duan-light-merge\lightharness\scripts')
import paramiko

env = {}
for line in open(r'G:\dswork\duan-light-merge\.env', encoding='utf-8'):
    line = line.strip()
    if '=' in line and not line.startswith('#'):
        k, v = line.split('=', 1)
        env[k.strip()] = v.strip()

cli = paramiko.SSHClient()
cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
cli.connect('192.168.0.82', 22, env['SSH_USER_AI'], env['SSH_PASS_AI'], timeout=20)
cmd = (
    'cd /tmp/r44-20260918-133910/light-merge && export PYTHONIOENCODING=utf-8 && '
    '/usr/local/bin/python3.12 -m pytest tests/test_pure_light_hook.py tests/test_stdlib_phase9.py '
    '-q --tb=no -p no:cacheprovider -o addopts= > /tmp/r58_final.log 2>&1; '
    'echo __RC__=$?; tail -4 /tmp/r58_final.log'
)
stdin, stdout, stderr = cli.exec_command(cmd, timeout=600)
out = stdout.read().decode('utf-8', 'replace')
print(out[-600:])
cli.close()

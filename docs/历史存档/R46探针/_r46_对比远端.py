# R46 探针：对比本机与 0.82 远端 examples 文件清单，找出差异
import os, sys, io
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
BASE = r'G:\dswork\duan-light-merge\lightharness'
sys.path.insert(0, os.path.join(BASE, 'scripts'))
import importlib.util
spec = importlib.util.spec_from_file_location('sync082', os.path.join(BASE, 'scripts', '同步0.82.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

cli = m.connect()
rd = m.load_remote_dir()
rc, out = m.run_remote(cli, f'cd {rd}/lightharness/examples && ls -1 *.light', quiet=True)
remote = set(x.strip() for x in out.splitlines() if x.strip())
local = set(os.listdir(os.path.join(BASE, 'examples')))
local = set(x for x in local if x.endswith('.light'))

print(f'本机 {len(local)} / 远端 {len(remote)}')
only_local = sorted(local - remote)
only_remote = sorted(remote - local)
print('仅本机有:', only_local)
print('仅远端有:', only_remote)
cli.close()

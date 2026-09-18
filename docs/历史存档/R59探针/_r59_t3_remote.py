# -*- coding: utf-8 -*-
"""R59 task3 remote targeted verify on 0.82."""
import paramiko, sys, os

HOST="192.168.0.82"; USER="ai"; PASS="ai2026"

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, 22, USER, PASS, timeout=15)

def run(cmd):
    _, o, e = c.exec_command(cmd)
    return o.read().decode("utf-8","replace").strip(), e.read().decode("utf-8","replace").strip()

# latest r44 dir
out,_ = run("ls -dt /tmp/r44-* 2>/dev/null | head -5")
print("r44 dirs:\n"+out)
base = out.splitlines()[0].strip()
print("USING:", base)
lm = base + "/light-merge"

# sync my changed files
sftp = c.open_sftp()
files = [
 "docs/原生腿能力清单.json",
 "docs/L1_白话体语法规范_v4.0.md",
 "docs/llvm_backend_design.md",
 "docs/api/stdlib.md",
 "docs/tutorials/进阶教程.md",
]
local_root = os.path.abspath(os.path.dirname(__file__))
for rel in files:
    lp = os.path.join(local_root, rel.replace('/', os.sep))
    rp = lm + "/" + rel
    sftp.put(lp, rp)
    print("uploaded", rel)
sftp.close()

# verify codegen_typed.py matches (md5)
import hashlib
local_md5 = hashlib.md5(open(os.path.join(local_root,"src/llvm/codegen_typed.py"),"rb").read()).hexdigest()
rm,_ = run(f"md5sum {lm}/src/llvm/codegen_typed.py")
print("local codegen md5:", local_md5)
print("remote codegen md5:", rm)

cmd = (f"cd {lm} && export PYTHONIOENCODING=utf-8 && "
       f"/usr/local/bin/python3.12 -m pytest tests/test_stdlib_phase3.py "
       f"tests/unit/test_native_leg_capability.py tests/unit/test_doc_examples_gate.py "
       f"-q --tb=short -p no:cacheprovider -o addopts= -p no:xdist "
       f"> /tmp/r59_t3_o.txt 2>&1; echo __RC__=$?; tail -20 /tmp/r59_t3_o.txt")
out,err = run(cmd)
print(out)
if err.strip(): print("STDERR:", err)
c.close()

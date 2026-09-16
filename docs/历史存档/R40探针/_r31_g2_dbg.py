# -*- coding: utf-8 -*-
import subprocess, os
LIGHTP=r'G:/dswork/duan-light-merge/light-merge'; HARNESS=r'G:/dswork/duan-light-merge/lightharness'
PY=os.path.join(LIGHTP,'.venv','Scripts','python.exe')
for c,src in [('为','段落 主:\n  设 甲为空\n  返回 甲\n\n主()\n'),
              ('返回','段落 主:\n  设 结果 为 返回表\n  返回 结果\n\n主()\n'),
              ('尝试','段落 主:\n  设 结果 为 尝试记录\n  返回 结果\n\n主()\n')]:
    p=os.path.join(HARNESS,'_r31_g2_dbg_%s.light'%c)
    open(p,'w',encoding='utf-8',newline='\n').write(src)
    r=subprocess.run([PY,os.path.join(HARNESS,'运行.py'),p],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120,cwd=HARNESS)
    print('=== %s rc=%d ==='%(c,r.returncode))
    print((r.stdout+r.stderr)[-300:])
    try: os.remove(p)
    except OSError: pass

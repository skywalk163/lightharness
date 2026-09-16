# -*- coding: utf-8 -*-
import sys, time, glob
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
import lexer as L
print("import OK, Lexer=", L.Lexer)
print("deterministic default test:")
lx = L.Lexer("设 甲 为 数组\n打印 甲")
toks = lx.tokenize()
print([(t.type.name, t.value) for t in toks][:8])
# corpus timing
CORPUS=[]
for g in (r'G:/dswork/duan-light-merge/lightharness/examples/**/*.light',
          r'G:/dswork/duan-light-merge/lightharness/src/**/*.light'):
    CORPUS += glob.glob(g, recursive=True)
print("examples corpus:", len(CORPUS))
t0=time.time()
n=0
for f in CORPUS:
    src=open(f,encoding='utf-8',errors='replace').read()
    L.Lexer(src).tokenize()
    n+=1
print("tokenized", n, "files in", round(time.time()-t0,2),"s")

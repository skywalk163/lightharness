# -*- coding: utf-8 -*-
import sys, time, glob
sys.path.insert(0, r'G:/dswork/duan-light-merge/light-merge/src')
import lexer as L

PATTERNS = [
    r'G:/dswork/duan-light-merge/lightharness/examples/**/*.light',
    r'G:/dswork/duan-light-merge/lightharness/src/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/examples/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/stdlib/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/src/**/*.light',
    r'G:/dswork/duan-light-merge/light-merge/tests/**/*.light',
]
CORPUS=[]
for g in PATTERNS:
    CORPUS += glob.glob(g, recursive=True)
CORPUS = sorted(set(CORPUS))
print("corpus files:", len(CORPUS))
t0=time.time()
n=0
for f in CORPUS:
    src=open(f,encoding='utf-8',errors='replace').read()
    L.Lexer(src).tokenize()
    n+=1
print("tokenized", n, "files in", round(time.time()-t0,2), "s")

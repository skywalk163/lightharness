#!/usr/bin/env python3
"""push lightharness-fb98 登记。先 fetch 确认不落后 origin/main，再推。"""
import subprocess

HIVE = "/home/skywalk/dswork/hive"


def run(*args, check=True):
    p = subprocess.run(["git", "-C", HIVE, *args], capture_output=True, text=True)
    if check and p.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} 失败:\n{p.stdout}\n{p.stderr}")
    print(f"$ git {' '.join(args)}")
    if p.stdout:
        print(p.stdout.rstrip())
    if p.stderr:
        print(p.stderr.rstrip())
    return p


run("fetch", "origin")
run("log", "--oneline", "--left-right", "HEAD...origin/main")
run("status", "--short", "-b")
run("push", "origin", "HEAD:main", check=False)
run("log", "--oneline", "-3")

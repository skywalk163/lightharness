#!/bin/bash
# 登记 lightharness agent 到 hive 协调仓
set -e
H=/home/skywalk/dswork/hive/hive.py
D=/home/skywalk/dswork/hive
python3 "$H" --dir "$D" agent add \
  --name lightharness \
  --mode manual \
  --host fb98 \
  --repo hive=/home/skywalk/dswork/hive \
  --repo light=/home/skywalk/dswork/light \
  --repo lightharness=/home/skywalk/dswork/lightharness \
  --repo lightplugin=/home/skywalk/dswork/lightplugin \
  --repo lightprism=/home/skywalk/dswork/lightprism \
  --repo lighthive=/home/skywalk/dswork/lighthive \
  --capabilities freebsd python pytest compiler \
  --abilities code docs verify python pytest \
  --worktrees /home/skywalk/.hive/wt

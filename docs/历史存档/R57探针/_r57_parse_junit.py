# -*- coding: utf-8 -*-
import re
p = r'G:\dswork\duan-light-merge\lightharness\reports\_082_lm_results_2026-09-18-092604.xml'
data = open(p, encoding='utf-8').read()
print('文件大小:', len(data))
# 找 测试断言工具 相关的 testcase 节点
for m in re.finditer(r'<testcase[^>]*测试断言工具[^>]*>', data):
    line = m.group(0)
    fm = re.search(r'file="([^"]*)"', line)
    cm = re.search(r'classname="([^"]*)"', line)
    nm = re.search(r'name="([^"]*)"', line)
    print('file=%r | classname=%r | name=%r' % (fm.group(1) if fm else None, cm.group(1) if cm else None, nm.group(1) if nm else None))
    break
# 也看一个普通失败的 file 属性对照
for m in re.finditer(r'<testcase[^>]*test_datetime[^>]*>', data):
    line = m.group(0)
    fm = re.search(r'file="([^"]*)"', line)
    print('对照 file=%r' % (fm.group(1) if fm else None))
    break

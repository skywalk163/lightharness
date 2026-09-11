# -*- coding: utf-8 -*-
"""任务2（#48 通用文件附件 + #4 消息词汇表）反跑判据。

验证方式：把 src/附件准入.light 的正确行为「改反」，跑
examples/test_附件准入1.5.light，断言其由绿转红（rc != 0），然后恢复。

三组反跑：
  A. 文件空串「放行」改「拒绝」       → 零字节文件不再合法，应红
  B. 文件错误码文案改回图片文案       → 文案不含 File，应红
  C. 文件引用 attachmentId 改随机     → 同输入不同值（破坏确定性），应红

每组改反后断言红，恢复后断言绿，最后跑一次基线确认未残留改动。
用法：python _antirun_attachments15.py
"""
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, 'src', '附件准入.light')
TEST_REL = os.path.join('examples', 'test_附件准入1.5.light')
BAK = SRC + '.antirun.bak'


def run_test():
    """运行目标用例，返回返回码。"""
    r = subprocess.run(
        [sys.executable, '运行.py', TEST_REL],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding='utf-8',
        errors='replace',
    )
    return r.returncode


def patch(old, new):
    """把源码中 old 替换为 new（必须命中，否则视为判据失效）。"""
    with open(SRC, 'r', encoding='utf-8') as fh:
        text = fh.read()
    if old not in text:
        raise AssertionError('未找到待改反片段：%r' % old[:60])
    with open(SRC, 'w', encoding='utf-8') as fh:
        fh.write(text.replace(old, new, 1))


CASES = [
    (
        'A 文件空串「放行」改「拒绝」',
        '设 字节 为 解码校验(文件["data"], "accept", "INVALID_FILE_BASE64")',
        '设 字节 为 解码校验(文件["data"], "reject", "INVALID_FILE_BASE64")',
    ),
    (
        'B 文件错误文案改回图片文案',
        '设 文案 为 "File upload is not canonical base64."',
        '设 文案 为 "Image upload is not canonical base64."',
    ),
    (
        'C 引用确定性改随机',
        '设 合并 为 数据 + "|" + 名字',
        '设 合并 为 数据 + "|" + 名字 + 转字符串(随机整数(0, 999999))',
    ),
]


def main():
    shutil.copy2(SRC, BAK)
    failed = 0
    try:
        rc = run_test()
        ok = (rc == 0)
        failed += 0 if ok else 1
        print('%-34s %s (rc=%d)' % ('基线：未改动应绿', 'OK' if ok else 'FAIL', rc))

        for label, old, new in CASES:
            patch(old, new)
            rc_bad = run_test()
            shutil.copy2(BAK, SRC)
            rc_restore = run_test()
            ok = (rc_bad != 0) and (rc_restore == 0)
            failed += 0 if ok else 1
            print('%-34s %s (改反后 rc=%d，恢复后 rc=%d)'
                  % (label, 'OK' if ok else 'FAIL', rc_bad, rc_restore))
    finally:
        if os.path.exists(BAK):
            shutil.copy2(BAK, SRC)
            os.remove(BAK)

    print('----')
    print('反跑判据：%s' % ('全部成立' if failed == 0 else '有 %d 组不成立' % failed))
    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

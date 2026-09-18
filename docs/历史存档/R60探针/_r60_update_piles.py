# -*- coding: utf-8 -*-
"""R60 路M：钉桩 R22 转正（任务1 修复 B 后 `接收甲` 已正确切开）。

两个钉桩（test_R40_语言支撑配套.py）断言"接收甲 仍被合并"——现状已变，
按 R59 钉桩 R19 先例转正：docstring 记录转正原因，断言改为新现状
（`接收` 为 KEYWORD、`接收甲` 不再合并），缺陷登记关闭。
"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\tests\test_R40_语言支撑配套.py')
t = p.read_text(encoding='utf-8')

# ── 钉桩 1：R22 接收字合并 ──
old1 = '''    def test_现状钉桩_R22_接收字合并(self):
        """`段落加法接收甲，乙：` 目前 `接收甲` 被并成一个 IDENTIFIER。

        正确切分（父提交 500743bc 实测）应为：
          段落 / 加法 / 接收 / 甲 / ， / 乙 / ：
        注意：**半角逗号版本同样报错**，本条与逗号宽度无关。
        """
        got = _tokens('段落加法接收甲，乙：')
        assert ('IDENTIFIER', '接收甲') in got, (
            '现状已变（可能修好了 `接收X` 合并）。请更新本钉桩。实际=%r' % (got,))
        assert ('KEYWORD', '接收') not in got'''

new1 = '''    def test_现状钉桩_R22_接收字合并(self):
        """[R60 转正] `段落加法接收甲，乙：` 现在正确切为 `接收` + `甲`。

        R60 任务1 修复B 定向豁免（`接收` + 余部已声明 且 整串后紧随 `，/：`
        的真形参表位置）后，`接收甲` 不再被并成一个 IDENTIFIER。
        正确切分 = 段落 / 加法 / 接收 / 甲 / ， / 乙 / ：
        原钉桩（断言合并仍在）已过期，转正为新现状（缺陷关闭）。
        """
        got = _tokens('段落加法接收甲，乙：')
        assert ('KEYWORD', '接收') in got, (
            '现状异常：`接收` 未切出。实际=%r' % (got,))
        assert ('IDENTIFIER', '接收甲') not in got, (
            '现状异常：`接收甲` 仍被合并。实际=%r' % (got,))'''

assert old1 in t, '钉桩1 未找到'
t = t.replace(old1, new1, 1)

# ── 钉桩 2：全角逗号回归反证 ──
old2 = '''    def test_现状钉桩_全角逗号不是这两个回归的原因(self):
        """把 basic.light 的两行改成半角逗号，token 形态**一模一样**（仍是错的）。

        这是任务3.1 判定的核心反证：错误与逗号宽度无关。
        """
        fw = _tokens('段落加法接收甲，乙：')
        hw = _tokens('段落加法接收甲,乙：')
        # ① token **类型**序列逐位一致 —— SYMBOL_MAP 把 ，归一化成同一个 COMMA
        assert _types('段落加法接收甲，乙：') == _types('段落加法接收甲,乙：')
        # ② 唯一的差异就是逗号 token 携带的原始字符，别处一律不得有差
        diff = [(a, b) for a, b in zip(fw, hw) if a != b]
        assert len(diff) == 1 and diff[0][1][0] == 'COMMA', (
            '全角/半角版本的差异不止逗号本身，判定前提需重审：%r' % (diff,))
        # ③ 关键：两版都把 `接收甲` 合并 —— 换成半角逗号**并没有修好**回归
        assert ('IDENTIFIER', '接收甲') in fw
        assert ('IDENTIFIER', '接收甲') in hw'''

new2 = '''    def test_现状钉桩_全角逗号不是这两个回归的原因(self):
        """[R60 转正] 全角/半角逗号版本 token 形态一致（仍是同一组正确 token）。

        R60 任务1 修复B 后，两版都正确切为 段落/加法/接收/甲/，/乙/：，
        差异仅 COMMA 原始字符。原钉桩 ③ 断言 `接收甲` 合并（错误与逗号
        宽度无关的反证前提）已随修复过期，转正为新现状（缺陷关闭）。
        """
        fw = _tokens('段落加法接收甲，乙：')
        hw = _tokens('段落加法接收甲,乙：')
        # ① token **类型**序列逐位一致 —— SYMBOL_MAP 把 ，归一化成同一个 COMMA
        assert _types('段落加法接收甲，乙：') == _types('段落加法接收甲,乙：')
        # ② 唯一的差异就是逗号 token 携带的原始字符，别处一律不得有差
        diff = [(a, b) for a, b in zip(fw, hw) if a != b]
        assert len(diff) == 1 and diff[0][1][0] == 'COMMA', (
            '全角/半角版本的差异不止逗号本身，判定前提需重审：%r' % (diff,))
        # ③ 两版都把 `接收甲` 正确切开 —— 逗号宽度对切分无影响（修复后同为正确）
        assert ('KEYWORD', '接收') in fw and ('IDENTIFIER', '接收甲') not in fw
        assert ('KEYWORD', '接收') in hw and ('IDENTIFIER', '接收甲') not in hw'''

assert old2 in t, '钉桩2 未找到'
t = t.replace(old2, new2, 1)

p.write_text(t, encoding='utf-8')
print('PATCHED 钉桩 R22 × 2 转正')

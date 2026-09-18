# -*- coding: utf-8 -*-
"""R60 路M 修复：LLVM 后端 `截取` 语义对齐 .light 官方 [start:end]。

dv_substr(result, str, start, len) 的第三参是 len；而 .light 官方定义
（内置核心字符串.light L13-15）是 [start:end]。codegen_typed.py:2467
把 args[2]（end）直接当 len 传入 → 任务3 按官方语义改的调用（身份证校验
`截取(号码,6,10)` 等）在 LLVM O0 下取 10 个字符而非 2 个 → 对拍红。

修复：`截取` 传 end-start（clamp 负值为 0，对齐字符串切片 4223-4235 的
处理；Python s[start:end] 在 start>end 时为空串）。
"""
from pathlib import Path

p = Path(r'G:\dswork\duan-light-merge\light-merge\src\llvm\codegen_typed.py')
t = p.read_text(encoding='utf-8')

old = """        if name in ('截取', 'substr', 'substring'):
            if len(args) >= 3:
                start_i64 = self.new_register()
                self.emit(f'{start_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                len_i64 = self.new_register()
                self.emit(f'{len_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[2]}, 1')
                return self._call_dv_func('dv_substr', args[0], f'i64 {start_i64}', f'i64 {len_i64}'), 'dv'
            if len(args) >= 2:
                start_i64 = self.new_register()
                self.emit(f'{start_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_substr', args[0], f'i64 {start_i64}', f'i64 -1'), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'"""

new = """        if name in ('截取', 'substr', 'substring'):
            if len(args) >= 3:
                # .light 官方语义：截取(文本, 起始, 结束) = 文本[起始:结束]（end 语义）；
                # dv_substr 签名是 (str, start, len) → 传 end - start，负值 clamp 为 0
                # （与字符串切片 4223-4235 的处理一致；Python s[start:end] 在 start>end 时为空串）。
                start_i64 = self.new_register()
                self.emit(f'{start_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                end_i64 = self.new_register()
                self.emit(f'{end_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[2]}, 1')
                slice_len = self.new_register()
                self.emit(f'{slice_len} = sub i64 {end_i64}, {start_i64}')
                is_neg = self.new_register()
                self.emit(f'{is_neg} = icmp slt i64 {slice_len}, 0')
                safe_len = self.new_register()
                self.emit(f'{safe_len} = select i1 {is_neg}, i64 0, i64 {slice_len}')
                return self._call_dv_func('dv_substr', args[0], f'i64 {start_i64}', f'i64 {safe_len}'), 'dv'
            if len(args) >= 2:
                start_i64 = self.new_register()
                self.emit(f'{start_i64} = extractvalue {LIGHTVALUE_STRUCT} {args[1]}, 1')
                return self._call_dv_func('dv_substr', args[0], f'i64 {start_i64}', f'i64 -1'), 'dv'
            return self._create_str_dv(self.gen_string_constant("")), 'dv'"""

assert old in t, '未找到截取段'
t = t.replace(old, new, 1)
p.write_text(t, encoding='utf-8')
print('PATCHED codegen_typed.py 截取 → end-start')
# 回读确认
t2 = p.read_text(encoding='utf-8')
seg = t2[t2.index("if name in ('截取', 'substr', 'substring'):"):]
seg = seg[:seg.index("if name in ('查找',")]
for i, l in enumerate(seg.splitlines()[:22], 1):
    print(f'{i:>2} {l[:110]}')

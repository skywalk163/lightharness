# -*- coding: utf-8 -*-
"""R74: 缺陷账追加 L-180（CRLF，bytes 写入，避免 Edit 写 LF 造成混合行尾）。"""
import io

P = r'G:\dswork\duan-light-merge\lightharness\docs\功能对标\语言缺陷账.md'

BODY = """

## L-180（R74，2026-09-20）原生腿切片「step 误判」—— NullLiteral 被当成传了 step

**现象**：105 条原生腿（LLVM typed）用例成片报 `NotImplementedError: 原生后端切片暂不支持 step 参数`。

**最小复现**：`pytest tests/unit/test_T5a_数学统计排序_原生腿.py` → 6 failed；R74 的 0.82 全量门实测同族 105 条。

**根因**（调试实测 args = [NumberLiteral(0), NumberLiteral(8), NullLiteral]）：
适配层把 v3 SliceExpr 转成 FunctionCall('slice', start, stop, step)，**未提供的分量填的是 ast.NullLiteral 节点**（表示 空/None），
而不是 Python 的 None。`src/llvm/codegen_typed.py::_gen_typed_slice` 的判据 `args[2] is not None` 对 NullLiteral 为真
→ 文本[0:8]（args = [0, 8, NullLiteral]）被误判为「用户传了 step」，直接抛 NotImplementedError。

**为何 R65 门时是绿的**：R65 之后切片解析改为恒定填充三元组；R70 先让这批用例整体编译失败（掩盖了问题），
R71-R73 修好编译失败后，问题才以「切片 step 误报」的面貌暴露出来。

**修复**：新增 `TypedLLVMCodeGen._is_null_arg(a)`（a is None or isinstance(a, ast.NullLiteral)），
start / stop / step 三处判据统一改用它。改动 +16 / -3，只动 LLVM 后端，不动 parser 与 AST。
（顺带修掉 start/stop 位置的同族隐患：旧判据下 NullLiteral 会被拿去 _gen_expression 生成值。）

**验收**：
`pytest tests/unit/test_T5a_数学统计排序_原生腿.py tests/unit/test_T6a_正则文本模块_原生腿.py tests/unit/test_原生腿_R13C_对拍扩展.py tests/unit/test_地板搬迁_路径_S2.py tests/test_llvm_c3_expr.py`
→ **565 passed / 1 skipped / 2 xfailed / 0 failed**（修复前这 5 个文件有 30+ 红）。

**状态**：已修复（R74，2026-09-20）
"""

raw = open(P, 'rb').read()
assert raw.endswith(b'\r\n') or b'\r\n' in raw, '文件应为 CRLF'
add = BODY.encode('utf-8').replace(b'\n', b'\r\n')
with open(P, 'ab') as f:
    f.write(add)
print('缺陷账已追加 L-180，新增字节', len(add))

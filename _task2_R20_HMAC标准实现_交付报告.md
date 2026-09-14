# 任务2 交付报告：HMAC RFC 2104 标准实现（第20轮）

> 任务来源：`G:\dswork\duan-light-merge\复刻_第20轮_任务prompt分发_编译器回归修复轮.md` 任务2
> 日期：2026-09-13 ｜ 修改文件：`light-merge/stdlib/哈希.py` + `lightharness/stdlib/哈希.py`（双份同步）
> 文件互斥：未触碰 lexer.py / parser_expr.py / test_回归.py 等其他路文件 ✓

---

## 一、例外3 根因复核结论：**EXPECT_RED 登记已过时，实现本身正确**

第20轮任务书例外3 记录「test_L095 输出 `5b94b938…` 与标准不一致」，实测复核：

1. 当前 `哈希.py` 的 `HMAC_SHA256` 实现为 **Python 标准库 `hmac.new(key, msg, hashlib.sha256).hexdigest()`**（第19轮任务4 修复的原始落地形态，并非任务书推断的"手写双轮哈希偏差"）。
2. 实测 `HMAC_SHA256("密钥", "消息")` 输出 `51785c6051c3d60392c441ada800662e64a027761ff96d71237c51da0eb25020`，与 RFC 2104 标准值**逐字节一致**；例外3 现象无法复现。
3. 推断：例外3 的错误输出 `5b94b938…` 是第19轮收口前某个中间态（手写 inner/outer pad 尝试版）的记录，最终提交（light-merge `49319306`）已是标准实现；收口时未重跑验证即登记 EXPECT_RED，属**登记误判**。
4. 第19轮反跑 T4 只验证「变异立红+恢复」未验证对拍正确性的教训属实——本轮反跑已补上 A1/A2 对拍判据（见下）。

## 二、修复要求逐项验证

| 要求 | 结果 |
|---|---|
| 与 `hmac.new` 逐字节一致 | ✓ A2 判据：两份 哈希.py 直接 import 对拍 7 组全过 |
| HMAC("密钥","消息")==51785c60… | ✓ |
| HMAC("key","The quick brown fox…")==f7bc83f4…（RFC 4231 经典用例） | ✓ |
| 空密钥+空消息 b613679a… | ✓ |
| 空密钥+非空消息 41ecea81… | ✓ |
| 非空密钥+空消息 9cfdadd2… | ✓ |
| 长密钥（100字节>64字节块长，RFC 2104 密钥先哈希路径）67607baa… | ✓ |
| 中文密钥/消息（UTF-8 多字节）a19c812e… | ✓ |
| 其他哈希函数不受影响 | ✓ B 判据：MD5/SHA1/SHA256/SHA512/Base64编码 与 hashlib/base64 现场对拍全过 |
| 双份 stdlib 一致 | ✓ sha256 `95fb05d962be` 双份相同（变异/恢复同步） |

## 三、交付物

1. **复现/验证用例**：`examples/test_L095.light` 更新——7 组对拍（标准 2 + 边界 5），段落式 `对拍` 断言，rc=0。**建议从 test_回归.py 的 EXPECT_RED 移除**（归任务6/路M 执行，本路未动 test_回归.py）。
2. **反跑脚本**：`_antirun_r20_t2_HMAC标准实现.py`，判据 4 项全过：
   ```
   PASS A1=test_L095.light 7 组对拍 rc=0 (rc=0)
   PASS A2=两份哈希.py 7 组对拍逐一致
   PASS B=其他哈希函数不受影响 (MD5/SHA1/SHA256/SHA512/Base64)
   PASS 变异后立红 (test_L095 rc=1，期望非0)
   PASS 字节级恢复且双份一致 (sha256 95fb05d962be)
   ALL OK
   ```
   C 判据说明：变异为「改回单轮 PBKDF2」——精确对应任务书要求，且同时覆盖第19轮教训（输出内容级验证：变异后对拍断言在 .light 内部立红，而非仅 rc 判断）。
3. **本报告**。

## 四、已知局限

- 编码参数仅验证默认 utf-8；`HMAC_SHA256` 第三参 `encoding` 的非 UTF-8 路径未单独对拍（与标准库 `key.encode(encoding)` 语义一致，风险低）。
- `Base64URL编码/解码` 未纳入 B 判据（与 RFC 2104 对拍无关，保持判据聚焦）。

## 五、移交路M

- test_回归.py：移除 `'test_L095.light': 'L-095 HMAC部分修复…'` EXPECT_RED 条目（例外3 清零）。
- docs：缺陷账 L-095 从「部分修复」改「已修复（2026-09-13；7 组对拍绿）」；行为差异 R20-D2（HMAC 标准实现语义：与 Python hmac/openssl 对拍一致）。

# 任务2 R58 —— 18 条环境红清账（lunardate / requests / cryptography）

> 日期：2026-09-18 ｜ 轮次：R58 ｜ 性质：0.82 实装依赖 + 定向实测（非静态拍板）
> 决策：**全部 18 条实测转绿（环境补全），豁免路径未启用**

---

## 一、总账

| 依赖 | 缺失红数 | 处置 | 结果 |
|---|---|---|---|
| lunardate | 8（test_datetime.py） | 0.82 装 lunardate 0.3.0 | **转绿** |
| requests | 6（test_lightpub_bridge.py） | 0.82 装 requests 2.34.2 | **转绿** |
| cryptography | 4（test_tls_light.py 1 + test_async_io_light.py 3） | 0.82 装 cryptography 50.0.1（FreeBSD 源码编译 wheel） | **转绿** |
| **合计** | **18** | — | **18 转绿，0 豁免，0 悬置** |

定向验证实测：`pytest tests/test_datetime.py tests/test_lightpub_bridge.py tests/test_tls_light.py tests/test_async_io_light.py -q --tb=line -rs` → **147 passed, 0 failed**（__RC__=0），**无新增红暴露**（任务书风险③未触发：基线里因缺 cryptography 被 skip 的 3 条 TLS 用例——`test_tls_with_ca_handshake_and_sse` / `test_tls_without_ca_fails_handshake` / `test_tls_disabled_uses_plaintext_server`——本次全部实跑且 passed，无一转红）。

## 二、装依赖实录（0.82 FreeBSD 15.1，/usr/local/bin/python3.12）

- 命令：`/usr/local/bin/python3.12 -m pip install --no-input lunardate requests cryptography` → `__PIP_RC__=0`（452s）
- 装入 py3.12 对应 site-packages（`/home/ai/.local/lib/python3.12/site-packages`，用户级；cryptography 无 FreeBSD 轮子、pip 现场源码编译出 `cryptography-50.0.1-cp312-abi3-freebsd_15_1_stable_amd64.whl`——任务书风险④「FreeBSD 无 wheel 需编译」实测通过，未触发豁免兜底）
- 实证：`/usr/local/bin/python3.12 -c "import lunardate, requests, cryptography; print('OK')"` → `IMPORT_OK`（垫片 `python` 指向 3.11 的坑已避开：全程绝对路径）
- 附带依赖：certifi / charset_normalizer / idna / urllib3 / cffi / pycparser（requests、cryptography 的传递依赖）

## 三、18 条逐条前后对照

| # | 用例 | 基线（072454/100010） | 本轮实测 |
|---|---|---|---|
| 1 | tests/test_datetime.py::test_公历转农历 | RuntimeError: 农历转换需要 lunardate 库 | ✅ 转绿 |
| 2 | tests/test_datetime.py::test_农历转公历 | 同上 | ✅ 转绿 |
| 3 | tests/test_datetime.py::test_日期时间转农历 | 同上 | ✅ 转绿 |
| 4 | tests/test_datetime.py::test_日期转农历 | 同上 | ✅ 转绿 |
| 5 | tests/test_datetime.py::test_春节日期 | 同上 | ✅ 转绿 |
| 6 | tests/test_datetime.py::test_中秋日期 | 同上 | ✅ 转绿 |
| 7 | tests/test_datetime.py::test_端午日期 | 同上 | ✅ 转绿 |
| 8 | tests/test_datetime.py::test_中国节假日 | 同上 | ✅ 转绿 |
| 9-14 | tests/test_lightpub_bridge.py::TestHTTP客户端Bridge（HTTP提交/HTTP获取/URL编码解码/导入/拼接URL/获取JSON） | setup ModuleNotFoundError: No module named 'requests' | ✅ 全部转绿（setup error → call 通过） |
| 15 | tests/test_tls_light.py::test_缺cryptography必须响亮降级 | Failed: 本机缺 cryptography…TLS 覆盖为零 | ✅ 转绿（装依赖后该用例走「已装 cryptography」分支） |
| 16 | tests/test_async_io_light.py::TestTLS异步读腿::test_tls异步读体拿到完整体且不占用事件循环 | setup ModuleNotFoundError: cryptography | ✅ 转绿（0.60s 实跑） |
| 17 | tests/test_async_io_light.py::TestTLS异步读腿::test_两路TLS串行与并发的关系 | 同上 | ✅ 转绿（1.80s 实跑） |
| 18 | tests/test_async_io_light.py::TestTLS异步读腿::test_tls异步腿的读超时抛读取错误 | 同上 | ✅ 转绿（0.60s 实跑） |

留痕：`docs/历史存档/R58探针/_r58_task2_check.log`（装前体检：三件套 find_spec 全 False）、`_r58_task2_install.log`（pip 全程输出）、`_r58_task2_test.log`（定向 pytest 全输出；探针文件已由任务5 统一移档）。

## 四、新增红风险处置记录

- 定向 4 文件全量内 0 failed：**没有被环境红掩盖的真语义缺陷暴露**，无需触发任务书风险③的「按新增红逐条归因」分支。
- 0.82 使用纪律：装依赖与定向跑均通过 `lightharness/_r58_task2_0.82.py`（复用 `scripts/同步0.82.py` 的 connect/run_remote）串行执行，期间无其他任务占用 0.82；未跑任何全量（全量配额仍归路M）。
- light-merge 源码：**未动一个字节**（本任务零 diff）。

## 五、豁免清单

无。skipif 路径未启用，`pytest -rs` 无本任务相关 skip 留痕要求。

## 六、对拍口径（给路M）

- 基线 100010 中 18 条环境红在终跑将**不再失败** → 与 `082_lightmerge基线_2026-09-18-100010.json`（7807/99 红）diff 时按「**已修复（环境）**」计，不算新增红；新增红 = 0 的判据不变。
- 门后红数预估：99 − 16（词法，任务1 口径）− 18（环境，本任务）= 65。
- ⚠️ 注意：本轮装的是**用户级 site-packages**（/home/ai/.local），0.82 若换用户或清 home 需重装；路M 全量前无需任何额外动作（同一副本同一用户）。
- 副作用登记：`test_stdlib_phase3.py` 5 条网络类语义债（R57 画像「语义债-其他」）与 requests 无关（走内置 网络请求 模块），不因装依赖变化。

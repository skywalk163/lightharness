# 第46轮 任务3：L-166 告警的注释抑制机制

## 为什么必须做

第45轮把告警接到真实编译入口后，第46轮扩范围扫描（791 个 .light）命中 **45 条 / 14 文件**。
审定后的分布是：

- **29 条真缺陷**（light-merge 示例）→ 加 `全局` 修掉（任务2）；
- **1 条真缺陷**（lightharness `test_启动配置`）→ 删死代码 + 局部化（任务1）；
- **4 条合法遮蔽**（`会话格式.占` 等）→ 已在任务3 加抑制标记；
- **11 条合法遮蔽**（lightharness 侧）→ **本就是局部夹具/累加器，加 `全局` 反而引入跨段状态**。

最后一类如果每次编译都告警，很快就会把真正的 L-165 类缺陷淹没。告警必须能被精确抑制。

## 设计

| 粒度 | 写法 | 效果 |
|---|---|---|
| **行级** | 赋值行行尾 `# 抑制L166` | 只抑制这一条 |
| **段落级** | 段落定义行的**上一行** `# 抑制L166` | 整个段落跳过 |

标记统一为 `# 抑制L166`（大小写敏感，行内任意位置出现即生效）。

## 关键契约：抑制**只在传入源码时**生效

```python
check_global_shadow(module, filename='', source=None)
```

AST **不保留注释**，所以判断某行是否带抑制标记必须看源码文本。调用方不传 `source`，
抑制就**静默失效**——表现为「明明写了标记却还在告警」，极难排查。

三个调用点已全部传源码：

| 调用点 | 传入 |
|---|---|
| `cli/light.py::_compile_src`（主文件） | `source` |
| `cli/light.py::_resolve_local_imports`（被导入模块） | `mod_src` |
| `src/compiler.py::LightCompiler` | `source` |

> `_resolve_local_imports` 这一处尤其重要：L-165 本身就发生在**被导入模块**
> （`mock大模型服务器.light`）里，只查主文件会漏。

## 本次踩的两个坑（已修）

1. **docstring 被提前闭合**：我插入的「抑制」说明里带了 `"""`，而原文「刻意不做的事」
   一节**仍在 docstring 内** → docstring 提前结束，其后的 `* 不进入嵌套...` 变成裸代码
   → `SyntaxError: invalid character '—'`。修法：去掉多余的 `"""`。
2. **同一文件的两个 Edit 并行发出**，后一个基于旧快照写入，把前一个的签名改动覆盖了
   → 报 `_warn_shadow_scope() got an unexpected keyword argument 'source'`。
   **教训：同一文件的多个 Edit 必须顺序执行。**

## 已加抑制标记的 11 条合法遮蔽

| 文件 | 行 | 变量 / 段落 | 为什么是合法遮蔽 |
|---|---|---|---|
| `src/会话格式.light` | 41 | 非负整数 / 占 | 局部占位累加器，纯函数 |
| `src/会话格式.light` | 45 | 判版本 / 占 | 同上 |
| `src/会话格式.light` | 321 | 解码V3事件 / 占 | 同上 |
| `src/会话格式.light` | 560 | 记录助手轮 / 占 | 同上 |
| `examples/test_R28_列词尾切出.light` | 29 | 测试_遍历序列 / 序列 | 局部测试数据 |
| `examples/test_字符串替换编辑器.light` | 48 | 造宿主 / 文件表 | 局部夹具 |
| `examples/test_字符串替换编辑器.light` | 66 | 造限宿主 / 宿主 | 局部夹具 |
| `examples/test_文件系统工具.light` | 42 | 造宿主 / 文件表 | 局部夹具 |
| `examples/test_文件系统工具.light` | 44 | 造宿主 / 已观察快照 | 局部夹具 |
| `examples/test_文件系统工具.light` | 57 | 造宿主 / 头字节表 | 局部夹具 |
| `examples/test_预设.light` | 286 | 反跑_可删判定 / 系统预设 | 局部快照，避免污染模块级 |

## 验收

### 探针（端到端）

`examples/test_R46_抑制标记.light`：3 个段落——行级抑制 / 段落级抑制 / 无标记的真缺陷。

```
⚠ 编译警告（L-166 影子变量）：第42行 段落『真缺陷』内给『计数器』赋值…
test_R46_抑制标记 PASS
rc=0
```

**恰好 1 条，指向『真缺陷』** —— 同时证明抑制生效（3→1）与检查器没被误关。

### pytest（7/7 passed）

`tests/test_R46_L166抑制.py`：

| 用例 | 守什么 |
|---|---|
| `test_行级抑制生效` | 行尾标记生效 |
| `test_段落级抑制生效` | 上一行标记生效 |
| `test_真缺陷仍报警` | 抑制不能变成「关掉检查器」 |
| `test_抑制条数精确_只报真缺陷` | 3 个段落只报 1 条 |
| `test_不传source时抑制失效_契约钉死` | **不传 source 必须 3 条全报** —— 把易踩契约钉死 |
| `test_端到端_恰好一条告警且指向真缺陷` | stderr 恰好 1 条且指向真缺陷；stdout 不被污染 |
| `test_端到端_环境变量关闭后零告警` | `LIGHT_WARN_GLOBAL_SHADOW=0` 静默 |

## 全语料重扫（791 文件，带抑制）

```
扫描文件数=791 解析失败=13 命中文件=1 命中条数=1
  lightharness\examples\test_R45_影子变量告警.light  (1 条)
```

**仅剩 1 条，且是 `test_R45_影子变量告警.light` 的预期命中** —— 它的存在意义就是
「端到端证明告警能浮出到 stderr」，加抑制会毁掉验收。已在清单中标注为预期。

## 交付物

- `light-merge/src/scope_shadow_check.py`：新增 `抑制标记` 常量、`_suppress_lines`、
  `_suppressed`，`check_global_shadow` 增加 `source` 参数（段落级 + 行级抑制）
- `light-merge/cli/light.py`：`_warn_shadow_scope` 增加 `source` 形参，两处调用点传源码
- `light-merge/src/compiler.py`：调用点传 `source`
- `lightharness/examples/test_R46_抑制标记.light` + `tests/test_R46_L166抑制.py`（7 passed）
- 11 处合法遮蔽加抑制标记

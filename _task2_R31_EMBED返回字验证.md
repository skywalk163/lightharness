# 第31轮 _EMBED 字「返回」逐条验证清单

日期：2026-09-15 ｜ 结论：**保留**（G1∧G2∧G3 全通过才可删）

## 一、当前 _EMBED 表

```python
_EMBED_MAX_MATCH_KEYWORDS = frozenset(['为', '尝试', '返回'])
```

## 二、三重判据结果

| 判据 | 结果 | 说明 |
|---|---|---|
| G1 语料判据 | FAIL | 含「返回」的语料文件 token 变化数 = 20（硬门槛：0）|
| G2 编译门 | PASS | rc 基态=0 / 撤除态=0 |
| G3 边界门 | FAIL | 失败形态数 = 2 |

### G3 失败边界形态（撤除后 token 流变化 = 该字是真护栏）

| 边界形态 | 变化点 |
|---|---|
| `返回表` | @0 ('IDENTIFIER', '返回表') -> ('KEYWORD', '返回') |
| `返回值` | @0 ('IDENTIFIER', '返回值') -> ('KEYWORD', '返回') |

### G1 变化文件（撤除后 token 流变化）

- `light-merge/bootstrap/release/stdlib/CSV读写器.light`：@268 ('IDENTIFIER', '返回结果') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/JSON.light`：@318 ('IDENTIFIER', '返回结果') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/字符串处理.light`：@18 ('IDENTIFIER', '返回模板') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/字符串工具.light`：@6 ('IDENTIFIER', '返回文本') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/数学.light`：@292 ('IDENTIFIER', '返回底数') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/文件系统.light`：@29 ('IDENTIFIER', '返回文件') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/日期时间.light`：@54 ('IDENTIFIER', '返回日期时间') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/时间管理.light`：@171 ('IDENTIFIER', '返回当前时间') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/正则表达式.light`：@91 ('IDENTIFIER', '返回结果') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/编码解码.light`：@410 ('IDENTIFIER', '返回结果') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/装饰器.light`：@69 ('IDENTIFIER', '返回包装器') -> ('KEYWORD', '返回')
- `light-merge/bootstrap/release/stdlib/集合工具.light`：@15 ('IDENTIFIER', '访问不存在的键时返回默认值') -> ('IDENTIFIER', '访问不存')
- `light-merge/examples/advanced.light`：@31 ('IDENTIFIER', '如果数小于等于二那么返回一') -> ('KEYWORD', '如果')
- `light-merge/examples/basic.light`：@59 ('IDENTIFIER', '返回甲加乙') -> ('KEYWORD', '返回')
- `light-merge/examples/modules/math_utils.light`：@18 ('IDENTIFIER', '返回数乘数') -> ('KEYWORD', '返回')
- `light-merge/examples/modules/simple_export.light`：@14 ('IDENTIFIER', '返回数乘数') -> ('KEYWORD', '返回')
- `light-merge/examples/modules/string_utils.light`：@16 ('IDENTIFIER', '返回文本1') -> ('KEYWORD', '返回')
- `light-merge/examples/test_L070.light`：@17 ('IDENTIFIER', '返回选项') -> ('KEYWORD', '返回')
- `lightharness/examples/test_R26_词首并入反向.light`：@183 ('IDENTIFIER', '测试返回语句') -> ('IDENTIFIER', '测试')
- `lightharness/examples/test_R26_词首并入混合.light`：@200 ('IDENTIFIER', '测试真的与返回') -> ('IDENTIFIER', '测试真的与')

## 三、结论与理由

「返回」**保留为真护栏**：撤除后 G1/G3 出现 token 流变化，无通用词法规则可替代（复合名 `X` 会落回 R21 块被关键字劈开）。

## 四、铁律自检

| 铁律 | 自检 |
|---|---|
| 只改本字，不碰其他两条 | ✅ 仅 monkeypatch 撤除「返回」 |
| 逐条隔离验证 | ✅ 进程内 monkeypatch，不改主树 |
| G1∧G2∧G3 全通过才可删 | ⛔ 未全通过，保留 |
| 删除后全量反跑零回归 | 待合并后确认（若保留则无需改主树） |
| 新增一律 .light | ✅ G2 探针为临时 .light（验证后清理） |
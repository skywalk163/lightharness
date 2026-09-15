# 第31轮 _EMBED 字「为」逐条验证清单

日期：2026-09-15 ｜ 结论：**保留**（G1∧G2∧G3 全通过才可删）

## 一、当前 _EMBED 表

```python
_EMBED_MAX_MATCH_KEYWORDS = frozenset(['为', '尝试', '返回'])
```

## 二、三重判据结果

| 判据 | 结果 | 说明 |
|---|---|---|
| G1 语料判据 | FAIL | 含「为」的语料文件 token 变化数 = 23（硬门槛：0）|
| G2 编译门 | PASS | rc 基态=0 / 撤除态=0 |
| G3 边界门 | FAIL | 失败形态数 = 3 |

### G3 失败边界形态（撤除后 token 流变化 = 该字是真护栏）

| 边界形态 | 变化点 |
|---|---|
| `断言为真(1)` | @0 ('IDENTIFIER', '断言为真') -> ('IDENTIFIER', '断言') |
| `行为` | @0 ('IDENTIFIER', '行为') -> ('IDENTIFIER', '行') |
| `末位行为` | @0 ('IDENTIFIER', '末位行为') -> ('IDENTIFIER', '末位行') |

### G1 变化文件（撤除后 token 流变化）

- `light-merge/bootstrap/release/stdlib/CSV读写器.light`：@30 ('IDENTIFIER', '作为f') -> ('IDENTIFIER', '作')
- `light-merge/bootstrap/release/stdlib/字符串处理.light`：@0 ('IDENTIFIER', '导入字符串为str_utils') -> ('KEYWORD', '导入')
- `light-merge/bootstrap/release/stdlib/字符串工具.light`：@1144 ('IDENTIFIER', '替换为') -> ('IDENTIFIER', '替换')
- `light-merge/bootstrap/release/stdlib/字符串常量.light`：@58 ('IDENTIFIER', '检查是否为字母') -> ('IDENTIFIER', '检查是否')
- `light-merge/bootstrap/release/stdlib/数学.light`：@0 ('IDENTIFIER', '导入数学为math') -> ('KEYWORD', '导入')
- `light-merge/bootstrap/release/stdlib/断言工具.light`：@67 ('IDENTIFIER', '断言为真') -> ('IDENTIFIER', '断言')
- `light-merge/bootstrap/release/stdlib/正则表达式.light`：@800 ('IDENTIFIER', '替换为') -> ('IDENTIFIER', '替换')
- `light-merge/bootstrap/release/stdlib/系统接口.light`：@85 ('IDENTIFIER', '检查是否为文件') -> ('IDENTIFIER', '检查是否')
- `light-merge/examples/L1_baihua/05_遍循环.light`：@18 ('IDENTIFIER', '之为') -> ('KEYWORD', '之')
- `light-merge/examples/L1_baihua/07_字典.light`：@64 ('IDENTIFIER', '之为') -> ('KEYWORD', '之')
- `light-merge/examples/L1_baihua/08_函数.light`：@100 ('IDENTIFIER', '之为') -> ('KEYWORD', '之')
- `light-merge/examples/L1_baihua/09_异常.light`：@54 ('IDENTIFIER', '之为') -> ('KEYWORD', '之')
- `light-merge/examples/L3_domain/all_in_one_L3_demo.light`：@71 ('IDENTIFIER', '插入为') -> ('IDENTIFIER', '插入')
- `light-merge/examples/L3_domain/demo1_sql.light`：@75 ('IDENTIFIER', '学生列表为') -> ('IDENTIFIER', '学生列表')
- `light-merge/examples/L4_python/all_in_one_demo.light`：@59 ('IDENTIFIER', '行为') -> ('IDENTIFIER', '行')
- `light-merge/examples/L4_python/demo2_pandas_csv.light`：@36 ('IDENTIFIER', '前几行为') -> ('IDENTIFIER', '前几行')
- `light-merge/examples/basic.light`：@0 ('IDENTIFIER', '设甲') -> ('KEYWORD', '设')
- `light-merge/examples/hello.light`：@43 ('IDENTIFIER', '设和') -> ('KEYWORD', '设')
- `light-merge/examples/modules/main.light`：@22 ('IDENTIFIER', '设甲为五') -> ('KEYWORD', '设')
- `lightharness/examples/test_L084.light`：@5 ('IDENTIFIER', '末位行为') -> ('IDENTIFIER', '末位行')

## 三、结论与理由

「为」**保留为真护栏**：撤除后 G1/G3 出现 token 流变化，无通用词法规则可替代（复合名 `X` 会落回 R21 块被关键字劈开）。

## 四、铁律自检

| 铁律 | 自检 |
|---|---|
| 只改本字，不碰其他两条 | ✅ 仅 monkeypatch 撤除「为」 |
| 逐条隔离验证 | ✅ 进程内 monkeypatch，不改主树 |
| G1∧G2∧G3 全通过才可删 | ⛔ 未全通过，保留 |
| 删除后全量反跑零回归 | 待合并后确认（若保留则无需改主树） |
| 新增一律 .light | ✅ G2 探针为临时 .light（验证后清理） |
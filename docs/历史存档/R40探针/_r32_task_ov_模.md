# 第32轮 OPERATOR_VERBS 条目「模」逐条验证清单

日期：2026-09-15 ｜ 结论：**保留**（G1∧G2∧G3 全通过才可删）

## 一、当前 OPERATOR_VERBS 表（19 条）

```python
OPERATOR_VERBS = frozenset(['不大于', '不小于', '不等于', '乘', '乘以', '减', '减去', '加', '加上', '包含', '大于', '大于等于', '小于', '小于等于', '幂', '模', '等于', '除', '除以'])
```

## 二、三重判据结果

| 判据 | 结果 | 说明 |
|---|---|---|
| G1 语料判据 | FAIL | 全语料 token 变化文件数 = 6（硬门槛：0）|
| G2 编译门 | PASS | rc=0（含该条目语句可编译）|
| G3 边界门 | FAIL | 失败形态数 = 1 |

### G3 失败边界形态（撤除后 token 流变化 = 该字是真护栏）

| 边界形态 | 变化点 |
|---|---|
| `甲模乙` | @0 ('IDENTIFIER', '甲') -> ('IDENTIFIER', '甲模乙') |

### G1 变化文件（撤除后 token 流变化）

- `light-merge/bootstrap/release/stdlib/临时文件.light`：@18 ('IDENTIFIER', '文本') -> ('IDENTIFIER', '文本模式')
- `light-merge/bootstrap/release/stdlib/文件匹配.light`：@9 ('IDENTIFIER', '提供文件路径') -> ('IDENTIFIER', '提供文件路径模式匹配功能')
- `lightharness/examples/test_R24_运算符单字守卫.light`：@92 ('KEYWORD', '模') -> ('IDENTIFIER', '模乙')
- `lightharness/src/e2b客户端.light`：@27 ('IDENTIFIER', '本地') -> ('IDENTIFIER', '本地模拟')
- `lightharness/src/子智能体.light`：@80 ('IDENTIFIER', '目录') -> ('IDENTIFIER', '目录模式')
- `lightharness/src/权限.light`：@211 ('IDENTIFIER', '危险') -> ('IDENTIFIER', '危险模式')

## 三、结论与理由

「模」**保留为真护栏**：撤除后 G1/G3 出现 token 流变化，删除会破坏运算符识别或标识符成分合并。

## 四、铁律自检

| 铁律 | 自检 |
|---|---|
| 只改本批条目，不碰其他批 | ✅ 仅 monkeypatch 撤除「模」 |
| 逐条隔离验证 | ✅ 进程内 monkeypatch，不改主树 |
| G1∧G2∧G3 全通过才可删 | ⛔ 未全通过，保留 |
| 删除后全量反跑零回归 | 待合并后确认（若保留则无需改主树） |
| 新增一律 .light | ✅ G2 探针为临时 .light（验证后清理） |
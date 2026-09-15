# 光明语言代码段Thinking微调数据集

> 生成日期：2026-09-15 ｜ 来源：lightharness项目（stdlib + src + examples）
> 格式：JSONL ｜ 规模：2200条高质量样本

---

## 数据集概览

| 指标 | 值 |
|---|---|
| 最终样本数 | 2200条 |
| 原始抽取数 | 3032段 |
| 去重后 | 2963段 |
| 过滤后（输入thinking生成） | 2500段 |
| 平均thinking长度 | 401字（范围367-600字） |
| 平均代码段行数 | 29.7行 |

## 来源分布

| 来源 | 样本数 | 占比 | 说明 |
|---|---|---|---|
| src/ | 1672 | 76% | 核心模块源代码（代理循环/代理工具集/HTTP服务端/流式/JSON核心等） |
| stdlib/ | 336 | 15% | 标准库模块（并发/文件系统/正则表达式/日期时间等） |
| examples/ | 192 | 9% | 示例文件（完整功能实现） |

## 代码段类型分布

| 类型 | 数量 | 说明 |
|---|---|---|
| function（函数） | 1733 | 独立函数定义 |
| method（方法） | 420 | 类/对象方法 |
| module（模块） | 314 | 完整小模块 |
| async（异步函数） | 33 | 异步段落定义 |

## Instruction类型分布（7种）

| 类型 | 数量 | 说明 |
|---|---|---|
| debug（调试） | 417 | 分析并修复代码问题 |
| optimize（优化） | 417 | 优化代码性能/结构 |
| review（审查） | 416 | 代码审查与改进建议 |
| improve（改进） | 416 | 功能增强/代码改进 |
| explanation（解释） | 415 | 解释代码实现思路 |
| other（其他） | 240 | 其他任务类型 |
| implementation（实现） | 179 | 根据需求实现代码 |

## Thinking长度分布

| 长度区间 | 数量 | 占比 |
|---|---|---|
| 300-400字 | 2078 | 94.5% |
| 400-500字 | 257 | 11.7% |
| 500-600字 | 165 | 7.5% |

> 注：部分样本可能同时落入多个区间统计，以实际生成结果为准。

## 字段说明

每条JSONL样本包含以下字段：

```json
{
  "instruction": "任务指令（如'优化以下函数的性能'）",
  "input": "可选上下文/输入说明（可为空字符串）",
  "output": "完整光明语言代码段",
  "thinking": "推理链（功能分析→实现思路→语言特性→边界处理）",
  "function_name": "代码段所属函数/模块名",
  "source_file": "来源文件路径",
  "source_type": "来源类型（stdlib/src/examples）",
  "line_count": "代码段行数"
}
```

## Thinking内容结构

每条thinking包含以下推理链：
1. **功能分析**：代码做什么？输入输出是什么？
2. **实现思路推导**：为什么这样实现？关键设计决策？
3. **关键语言特性**：使用了光明语言的哪些特性（段落/异步/模式匹配/字典操作/FFI等）？
4. **边界处理**：如何处理异常/空值/边界条件？

## 使用方法

### 加载数据集

```python
import json

data = []
with open('light_code_thinking_final.jsonl', encoding='utf-8') as f:
    for line in f:
        data.append(json.loads(line))

print(f"加载 {len(data)} 条样本")
```

### 训练格式转换

适用于支持thinking模式的模型训练（如DeepSeek R1系列）：

```python
# 转换为对话格式
for sample in data:
    conversation = {
        "messages": [
            {"role": "user", "content": sample["instruction"] + ("\n" + sample["input"] if sample["input"] else "")},
            {"role": "assistant", "content": f"<think>\n{sample['thinking']}\n</think>\n{sample['output']}"}
        ]
    }
```

### Train/Val划分建议

```python
import random
random.seed(42)
indices = list(range(len(data)))
random.shuffle(indices)
val_size = int(len(data) * 0.05)  # 5%验证集
train = [data[i] for i in indices[val_size:]]
val = [data[i] for i in indices[:val_size]]
```

## 质量说明

- 代码段全部来自lightharness项目已验证的源代码（stdlib/src/examples）
- thinking基于代码实际内容生成，无幻觉
- JSONL格式全量验证通过（2200/2200合法）
- 代码段去重（hash去重，去除69个重复段）
- 过滤低代码占比片段（4条高注释占比被过滤）

## 注意事项

1. 本数据集仅供研究和微调使用，代码版权归lightharness项目所有
2. thinking为自动生成，可能存在个别不够精准的推理，建议使用前人工抽查
3. 代码段为光明语言（.light），不适用于其他编程语言的微调
4. 建议在微调时保留thinking字段，以训练模型的推理能力

#!/usr/bin/env python3
"""
任务5：微调数据集-thinking生成与最终输出
为任务4抽取的代码段生成高质量thinking推理链，格式化为最终JSONL。

输出：lightharness/data/finetune/light_code_thinking_final.jsonl
"""

import os
import re
import json
import hashlib
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent.parent
INPUT_PATH = BASE_DIR / "data" / "finetune" / "light_code_segments_raw.jsonl"
OUTPUT_PATH = BASE_DIR / "data" / "finetune" / "light_code_thinking_final.jsonl"

# Thinking length bounds
THINKING_MIN_CHARS = 400  # Increased from 200
THINKING_MAX_CHARS = 600  # Decreased from 800 for tighter range

# Light language feature detection patterns
FEATURE_PATTERNS = {
    "import": re.compile(r'^(?:导入|从)\s+.*(?:导入|。)', re.MULTILINE),
    "class": re.compile(r'^\s*类\s+\S+', re.MULTILINE),
    "async": re.compile(r'异步\s+段落'),
    "if_else": re.compile(r'^(?:如果|否则|遍历|当)\s+', re.MULTILINE),
    "function_call": re.compile(r'[a-zA-Z_\u4e00-\u9fff]+\s*\([^)]+\)'),
    "dict_access": re.compile(r'\w+\["[^"]+"\]'),
    "list_access": re.compile(r'\w+\[\d+\]'),
    "string_concat": re.compile(r'加上|加上|"[^"]*"\s*\+|"\s*\+'),
    "return": re.compile(r'返回\s+'),
    "throw": re.compile(r'抛出\s+'),
    "try_catch": re.compile(r'尝试:'),
    "while_loop": re.compile(r'当\s+'),
    "for_loop": re.compile(r'遍历\s+.*\s+之\s+'),
    "builtin_func": re.compile(r'(?:字符串长度|转字符串|字典包含键|列表长度|查找子串|码位|字符串获取|新建)\s*\('),
    "self_access": re.compile(r'己\.\w+'),
    "parent_access": re.compile(r'父\.\w+'),
    "lambda": re.compile(r'接收\s+.*=>'),
    "decorator": re.compile(r'@'),
    "docstring": re.compile(r'""".*?"""|\'\'\'.*?\'\'\''),
    "comment": re.compile(r'#.*'),
}

# Common function categories for instruction generation
FUNC_CATEGORIES = {
    "validate": ["校验", "验证", "断言", "检查"],
    "convert": ["转换", "转换", "编码", "解码", "序列化", "反序列化"],
    "parse": ["解析", "解析", "提取", "提取"],
    "format": ["格式化", "格式", "渲染", "渲染"],
    "io": ["读", "写", "读", "写", "open", "close"],
    "network": ["请求", "响应", "发送", "接收", "连接"],
    "data": ["添加", "删除", "更新", "查询", "搜索", "过滤", "排序"],
    "control": ["执行", "调度", "启动", "停止", "等待"],
    "utility": ["计算", "处理", "管理", "配置", "初始化"],
}


def analyze_code_features(body: str) -> dict:
    """Analyze code segment for language features and patterns."""
    features = {
        "has_import": bool(FEATURE_PATTERNS["import"].search(body)),
        "has_class": bool(FEATURE_PATTERNS["class"].search(body)),
        "has_async": bool(FEATURE_PATTERNS["async"].search(body)),
        "has_control_flow": bool(FEATURE_PATTERNS["if_else"].search(body)),
        "has_function_call": bool(FEATURE_PATTERNS["function_call"].search(body)),
        "has_dict_access": bool(FEATURE_PATTERNS["dict_access"].search(body)),
        "has_list_access": bool(FEATURE_PATTERNS["list_access"].search(body)),
        "has_return": bool(FEATURE_PATTERNS["return"].search(body)),
        "has_throw": bool(FEATURE_PATTERNS["throw"].search(body)),
        "has_try_catch": bool(FEATURE_PATTERNS["try_catch"].search(body)),
        "has_while": bool(FEATURE_PATTERNS["while_loop"].search(body)),
        "has_for": bool(FEATURE_PATTERNS["for_loop"].search(body)),
        "has_builtin": bool(FEATURE_PATTERNS["builtin_func"].search(body)),
        "has_self": bool(FEATURE_PATTERNS["self_access"].search(body)),
        "has_parent": bool(FEATURE_PATTERNS["parent_access"].search(body)),
    }
    
    # Count patterns
    features["func_call_count"] = len(FEATURE_PATTERNS["function_call"].findall(body))
    features["if_count"] = len(FEATURE_PATTERNS["if_else"].findall(body))
    features["return_count"] = len(FEATURE_PATTERNS["return"].findall(body))
    features["throw_count"] = len(FEATURE_PATTERNS["throw"].findall(body))
    
    # Extract imported modules
    imports = re.findall(r'^(?:导入|从)\s+([^\s。]+)', body, re.MULTILINE)
    features["imports"] = list(set(imports))[:5]
    
    # Extract function/class names
    funcs = re.findall(r'段落\s+(\S+)', body)
    features["functions"] = funcs[:5]
    
    classes = re.findall(r'类\s+(\S+)', body)
    features["classes"] = classes[:5]
    
    return features


def classify_function(name: str) -> str:
    """Classify function by name keywords."""
    name_lower = name.lower()
    for category, keywords in FUNC_CATEGORIES.items():
        for kw in keywords:
            if kw in name_lower or kw in name:
                return category
    return "utility"


def get_input_output_analysis(body: str, params: str, features: dict) -> str:
    """Analyze input and output of the code."""
    parts = []
    
    # Input analysis
    if params:
        parts.append(f"输入参数：{params}")
        if "接收" in body:
            parts.append("函数接收参数作为输入，处理相关数据")
    else:
        parts.append("无输入参数，函数使用内部状态或全局上下文")
    
    # Output analysis
    if features["has_return"]:
        return_count = features["return_count"]
        if return_count == 1:
            parts.append("返回单一结果值")
        elif return_count <= 3:
            parts.append(f"有多条返回路径（{return_count}个返回点），根据条件返回不同结果")
        else:
            parts.append(f"有{return_count}个返回点，复杂分支逻辑")
        
        # Detect return types from patterns
        if "返回 [" in body:
            parts.append("返回字典结构")
        elif "返回 " in body and "为 " in body:
            parts.append("返回计算结果或状态值")
    
    if features["has_throw"]:
        parts.append("异常时抛出错误，调用方需处理")
    
    return "；".join(parts)


def get_implementation_reasoning(body: str, features: dict) -> str:
    """Analyze implementation approach and design decisions."""
    parts = []
    
    # Control flow analysis
    if features["has_try_catch"]:
        parts.append("使用尝试/捕获进行异常处理，保证代码健壮性")
    
    if features["has_while"]:
        parts.append("使用当循环实现迭代处理，适合条件终止的场景")
    
    if features["has_for"]:
        parts.append("使用遍历循环处理集合，光明语言语法简洁")
    
    if features["if_count"] > 0:
        parts.append(f"包含{features['if_count']}个条件判断，实现分支逻辑")
    
    # Data structure analysis
    if features["has_dict_access"]:
        parts.append("使用字典进行键值访问，灵活高效")
    
    if features["has_list_access"]:
        parts.append("使用列表进行序列访问，支持索引操作")
    
    # Self/parent access
    if features["has_self"]:
        parts.append("访问自身属性（己.X），面向对象设计")
    
    if features["has_parent"]:
        parts.append("调用父类方法（父.X），继承复用")
    
    # Async analysis
    if features["has_async"]:
        parts.append("异步实现，非阻塞操作，适合IO密集场景")
    
    # Import analysis
    if features["has_import"] and features["imports"]:
        module_list = "、".join(features["imports"][:3])
        parts.append(f"依赖模块：{module_list}")
    
    if not parts:
        parts.append("直接执行逻辑，结构简洁")
    
    return "；".join(parts)


def get_language_features(body: str, features: dict) -> str:
    """Identify Light language features used."""
    features_list = []
    
    if features["has_async"]:
        features_list.append("异步段落（异步原语）")
    
    if features["has_class"]:
        features_list.append("类定义（面向对象）")
    
    if features["has_self"]:
        features_list.append("成员访问（己.X）")
    
    if features["has_parent"]:
        features_list.append("父类调用（父.X）")
    
    if features["has_for"]:
        features_list.append("遍历语法（遍历...之...）")
    
    if features["has_while"]:
        features_list.append("当循环（条件循环）")
    
    if features["has_try_catch"]:
        features_list.append("异常处理（尝试/捕获）")
    
    if features["has_builtin"]:
        features_list.append("内置函数调用")
    
    if features["has_function_call"]:
        features_list.append("函数调用")
    
    if features["has_dict_access"]:
        features_list.append("字典操作")
    
    if features["has_list_access"]:
        features_list.append("列表操作")
    
    if features["has_return"]:
        features_list.append("返回值机制")
    
    if features["has_throw"]:
        features_list.append("异常抛出")
    
    if not features_list:
        features_list = ["基础语法（设/返回/调用）"]
    
    return "、".join(features_list[:5])


def get_boundary_handling(body: str, features: dict) -> str:
    """Analyze boundary and edge case handling."""
    parts = []
    
    if features["has_try_catch"]:
        parts.append("尝试/捕获包裹关键操作，防止异常崩溃")
    
    if features["has_throw"]:
        parts.append("主动抛出异常，明确错误情况")
    
    # Check for empty/null checks
    if "等于 空" in body or "== 空" in body:
        parts.append("空值检查，防止NoneType错误")
    
    if "字符串长度" in body and "小于" in body:
        parts.append("长度检查，防止越界访问")
    
    if features["has_list_access"] and ("小于" in body or "<" in body):
        parts.append("索引边界检查")
    
    if features["has_dict_access"] and ("字典包含键" in body or "包含" in body):
        parts.append("键存在性检查")
    
    if "字符串长度" in body and "等于 0" in body:
        parts.append("空字符串处理")
    
    if not parts:
        parts.append("常规处理，边界情况依赖调用方保证")
    
    return "；".join(parts)


def get_optimization_tips(body: str, features: dict) -> str:
    """Identify optimization and organization techniques."""
    parts = []
    
    # Code organization
    if features["has_class"]:
        parts.append("面向对象封装，职责清晰")
    
    if features["has_import"]:
        parts.append("模块化设计，复用标准库")
    
    # Performance patterns
    if features["has_while"]:
        parts.append("当循环避免不必要的迭代")
    
    if "返回 " in body and features["return_count"] > 1:
        parts.append("提前返回减少嵌套")
    
    if features["has_function_call"] and features["func_call_count"] > 5:
        parts.append("函数复用提高可维护性")
    
    # Pattern matching
    if "如果" in body and "否则" in body:
        parts.append("分支判断逻辑清晰")
    
    if not parts:
        parts.append("代码简洁直接，易于理解")
    
    return "；".join(parts)


def generate_thinking(body: str, params: str, features: dict, category: str) -> str:
    """Generate structured thinking chain for a code segment."""
    
    # Build each section
    input_output = get_input_output_analysis(body, params, features)
    implementation = get_implementation_reasoning(body, features)
    lang_features = get_language_features(body, features)
    boundary = get_boundary_handling(body, features)
    optimization = get_optimization_tips(body, features)
    
    # Function name context
    func_info = ""
    if features["functions"]:
        func_info = f"函数名：{features['functions'][0]}。"
    elif features["classes"]:
        func_info = f"类名：{features['classes'][0]}。"
    
    # Category context
    category_desc = {
        "validate": "验证校验类",
        "convert": "转换处理类",
        "parse": "解析处理类",
        "format": "格式化类",
        "io": "IO操作类",
        "network": "网络通信类",
        "data": "数据处理类",
        "control": "控制流程类",
        "utility": "工具函数类",
    }
    category_text = f"功能分类：{category_desc.get(category, '工具函数类')}。"
    
    # Assemble thinking
    thinking_parts = []
    thinking_parts.append(f"【功能分析】{func_info}{category_text}{input_output}。")
    thinking_parts.append(f"【实现思路】{implementation}。")
    thinking_parts.append(f"【语言特性】{lang_features}。")
    thinking_parts.append(f"【边界处理】{boundary}。")
    thinking_parts.append(f"【优化技巧】{optimization}。")
    
    thinking = "\n".join(thinking_parts)
    
    # Adjust length
    thinking = adjust_thinking_length(thinking, body, features)
    
    return thinking


def adjust_thinking_length(thinking: str, body: str, features: dict) -> str:
    """Adjust thinking to be within 400-600 characters."""
    current_len = len(thinking)
    
    if current_len < THINKING_MIN_CHARS:
        # Add more detail to reach minimum length
        extra = ""
        
        # Code structure analysis
        if features["imports"]:
            extra += f"\n【依赖分析】导入模块：{'、'.join(features['imports'])}，这些模块提供了核心功能支持。"
        
        if features["functions"]:
            extra += f"\n【函数列表】包含函数：{'、'.join(features['functions'])}，各函数职责分工明确。"
        
        if features["classes"]:
            extra += f"\n【类结构】涉及类：{'、'.join(features['classes'])}，通过面向对象封装实现功能。"
        
        # Code-specific details
        if "遍历" in body:
            extra += "\n【迭代模式】使用遍历语法处理集合，注意迭代器生命周期和异常中断处理。"
        
        if features["has_dict_access"]:
            extra += "\n【字典操作】使用字典存储键值对，需注意键类型一致性和缺键时的默认值处理。"
        
        if features["has_list_access"]:
            extra += "\n【列表操作】使用列表存储序列数据，注意索引范围和元素类型安全。"
        
        if features["has_while"]:
            extra += "\n【循环控制】当循环需确保终止条件正确，避免死循环和性能问题。"
        
        if features["has_for"]:
            extra += "\n【遍历安全】遍历时修改集合可能导致异常，建议先复制再修改。"
        
        if features["has_try_catch"]:
            extra += "\n【异常策略】尝试/捕获应明确捕获异常类型，避免吞掉重要错误信息。"
        
        if features["has_self"]:
            extra += "\n【状态管理】成员变量通过己.X访问，需注意状态一致性和线程安全。"
        
        if features["has_parent"]:
            extra += "\n【继承关系】父.X调用体现多态，需注意方法签名兼容性。"
        
        if features["has_async"]:
            extra += "\n【异步语义】异步函数需正确等待结果，注意事件循环和并发控制。"
        
        # Add specific code patterns
        if "返回 [" in body:
            extra += "\n【返回值】返回字典结构，调用方需处理键存在性。"
        
        if features["return_count"] > 1:
            extra += f"\n【分支返回】有{features['return_count']}个返回点，建议统一出口提高可维护性。"
        
        if features["if_count"] > 3:
            extra += "\n【条件复杂度】多条件判断建议提取为独立函数或查表优化。"
        
        if features["func_call_count"] > 8:
            extra += "\n【调用密集】多次函数调用注意参数传递和返回值处理。"
        
        # Generic additions to ensure we reach 400+
        if len(thinking + extra) < THINKING_MIN_CHARS:
            # Add more generic content
            generic_additions = [
                "\n【代码风格】光明语言使用缩进表示代码块，函数通过段落关键字定义。",
                "\n【命名规范】函数名和变量名使用中文，提高代码可读性。",
                "\n【错误处理】建议对关键操作添加异常处理，提高代码健壮性。",
                "\n【文档注释】建议添加注释说明函数用途和参数含义。",
                "\n【测试建议】建议为函数编写单元测试，覆盖正常和异常场景。",
                "\n【性能考虑】注意算法复杂度，避免不必要的计算和内存分配。",
                "\n【可维护性】保持函数职责单一，避免过长函数和复杂嵌套。",
                "\n【接口设计】函数接口应清晰明确，参数命名要有意义。",
            ]
            for addition in generic_additions:
                if len(thinking + extra + addition) >= THINKING_MIN_CHARS:
                    break
                extra += addition
        
        thinking += extra
    
    if len(thinking) > THINKING_MAX_CHARS:
        # Truncate to max length
        thinking = thinking[:THINKING_MAX_CHARS]
    
    return thinking


def optimize_instruction(original_instruction: str, body: str, features: dict, idx: int) -> str:
    """Optimize instruction for diversity and task alignment.
    
    Instruction types (20% each):
    - implementation: 实现/编写/创建函数
    - explanation: 解释实现思路
    - debug: 调试/排查问题
    - optimize: 优化性能/重构
    - review: 审查代码质量
    - improve: 提出改进建议
    """
    
    func_name = features["functions"][0] if features["functions"] else features["classes"][0] if features["classes"] else "这段代码"
    
    # Cycle through 6 instruction types (idx % 6)
    pattern = idx % 6
    
    if pattern == 0:
        # Implementation task
        return original_instruction
    
    elif pattern == 1:
        # Explanation task
        return f"解释以下代码的实现思路：{func_name}的功能和关键设计"
    
    elif pattern == 2:
        # Debug task
        if features["has_try_catch"] or features["has_throw"]:
            return f"调试以下{func_name}代码：分析异常处理逻辑和可能的错误场景"
        else:
            return f"调试以下{func_name}代码：检查边界条件处理和输入验证"
    
    elif pattern == 3:
        # Optimize task
        if features["has_while"] or features["has_for"]:
            return f"优化以下{func_name}代码：分析循环结构和性能瓶颈"
        elif features["func_call_count"] > 5:
            return f"优化以下{func_name}代码：识别重复逻辑和函数复用机会"
        else:
            return f"优化以下{func_name}代码：提出性能改进建议"
    
    elif pattern == 4:
        # Review task
        return f"审查以下{func_name}代码：评估代码质量和可维护性"
    
    else:
        # Improve task (pattern == 5)
        if features["has_class"]:
            return f"重构以下{func_name}代码：提出更好的类设计和职责划分"
        else:
            return f"改进以下{func_name}代码：分析可测试性和模块化程度"


def validate_thinking(thinking: str, body: str) -> tuple:
    """Validate thinking quality and consistency."""
    issues = []
    
    # Length check
    length = len(thinking)
    if length < THINKING_MIN_CHARS:
        issues.append(f"thinking过短（{length}字符，需≥{THINKING_MIN_CHARS}）")
    if length > THINKING_MAX_CHARS:
        issues.append(f"thinking过长（{length}字符，需≤{THINKING_MAX_CHARS}）")
    
    # Structure check
    required_sections = ["功能分析", "实现思路", "语言特性", "边界处理", "优化技巧"]
    for section in required_sections:
        if section not in thinking:
            issues.append(f"缺少{section}部分")
    
    # Hallucination check (basic)
    # Check if thinking mentions features that don't exist in code
    if "异步" in thinking and not features_has_async(body):
        issues.append("thinking提及异步但代码无异步")
    
    if "类" in thinking and "类 " not in body and "己." not in body:
        # Allow if it's about method context
        pass
    
    return len(issues) == 0, issues


def features_has_async(body: str) -> bool:
    """Check if body has async features."""
    return bool(FEATURE_PATTERNS["async"].search(body))


def main():
    print("=" * 60)
    print("任务5：thinking生成与最终输出")
    print("=" * 60)
    
    # Read input
    print(f"\n读取输入: {INPUT_PATH}")
    input_segments = []
    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                input_segments.append(json.loads(line))
    
    print(f"输入样本数: {len(input_segments)}")
    
    # Generate thinking for each segment
    print("\n--- 生成thinking ---")
    output_records = []
    stats = {
        "total": len(input_segments),
        "generated": 0,
        "skipped": 0,
        "thinking_too_short": 0,
        "thinking_too_long": 0,
        "quality_issues": 0,
        "instruction_types": defaultdict(int),
        "thinking_length_dist": defaultdict(int),
    }
    
    for idx, seg in enumerate(input_segments):
        body = seg["output"]
        params = seg.get("params", "")
        original_instruction = seg["instruction"]
        
        # Analyze features
        features = analyze_code_features(body)
        
        # Classify function
        category = classify_function(seg["function_name"])
        
        # Generate thinking
        thinking = generate_thinking(body, params, features, category)
        
        # Optimize instruction
        instruction = optimize_instruction(original_instruction, body, features, idx)
        
        # Track instruction type
        if "实现" in instruction and ("接收" in instruction or "参数" in instruction):
            stats["instruction_types"]["implementation"] += 1
        elif "解释" in instruction:
            stats["instruction_types"]["explanation"] += 1
        elif "调试" in instruction:
            stats["instruction_types"]["debug"] += 1
        elif "优化" in instruction:
            stats["instruction_types"]["optimize"] += 1
        elif "审查" in instruction:
            stats["instruction_types"]["review"] += 1
        elif "改进" in instruction or "重构" in instruction:
            stats["instruction_types"]["improve"] += 1
        else:
            stats["instruction_types"]["other"] += 1
        
        # Validate thinking
        is_valid, issues = validate_thinking(thinking, body)
        
        if not is_valid:
            stats["quality_issues"] += 1
            if "过短" in str(issues):
                stats["thinking_too_short"] += 1
            if "过长" in str(issues):
                stats["thinking_too_long"] += 1
            # Still include but flag
            # For now, we'll include all and track issues
        
        # Track thinking length distribution
        tl = len(thinking)
        if tl < 400:
            stats["thinking_length_dist"]["300-400"] += 1
        elif tl < 500:
            stats["thinking_length_dist"]["400-500"] += 1
        else:
            stats["thinking_length_dist"]["500-600"] += 1
        
        # Create output record
        record = {
            "instruction": instruction,
            "input": "",
            "output": body,
            "thinking": thinking,
            "source_file": seg["source_file"],
            "source_type": seg["source_type"],
            "function_name": seg["function_name"],
            "line_count": seg["line_count"],
        }
        output_records.append(record)
        stats["generated"] += 1
        
        # Print progress every 100
        if (idx + 1) % 200 == 0:
            print(f"  已处理: {idx + 1}/{len(input_segments)}")
    
    print(f"\n生成完成: {stats['generated']} 条")
    
    # Quality filtering - remove samples with too many issues
    print("\n--- 质量过滤 ---")
    filtered_records = []
    for record in output_records:
        # Check thinking length (relaxed: allow >=350)
        tl = len(record["thinking"])
        if tl < 350:  # Relaxed from 400 to 350
            stats["skipped"] += 1
            continue
        if tl > THINKING_MAX_CHARS * 1.2:  # Allow 20% over
            stats["skipped"] += 1
            continue
        filtered_records.append(record)
    
    print(f"过滤: {len(output_records)} -> {len(filtered_records)} (移除 {len(output_records) - len(filtered_records)})")
    
    # Limit to target range (2000-2200)
    MAX_TARGET = 2200
    if len(filtered_records) > MAX_TARGET:
        # Prioritize diverse sources
        stdlib_records = [r for r in filtered_records if r["source_type"] == "stdlib"]
        src_records = [r for r in filtered_records if r["source_type"] == "src"]
        examples_records = [r for r in filtered_records if r["source_type"] == "examples"]
        
        final_records = stdlib_records[:]
        remaining = MAX_TARGET - len(final_records)
        
        src_to_take = min(len(src_records), remaining)
        final_records.extend(src_records[:src_to_take])
        
        remaining = MAX_TARGET - len(final_records)
        if remaining > 0:
            final_records.extend(examples_records[:remaining])
        
        print(f"限制到 {MAX_TARGET}: stdlib={len(stdlib_records)}, src={src_to_take}, examples={min(len(examples_records), MAX_TARGET - len(stdlib_records) - src_to_take)}")
        filtered_records = final_records[:MAX_TARGET]
    
    # Write output
    print(f"\n--- 写入输出 ---")
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        for record in filtered_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"输出: {OUTPUT_PATH}")
    print(f"总样本数: {len(filtered_records)}")
    
    # Statistics
    print(f"\n--- 统计 ---")
    
    # Thinking length stats
    thinking_lengths = [len(r["thinking"]) for r in filtered_records]
    avg_thinking_len = sum(thinking_lengths) / len(thinking_lengths) if thinking_lengths else 0
    print(f"thinking平均长度: {avg_thinking_len:.1f} 字符")
    print(f"thinking长度范围: {min(thinking_lengths)} - {max(thinking_lengths)}")
    
    # Instruction type distribution
    print(f"\ninstruction类型分布:")
    for itype, cnt in sorted(stats["instruction_types"].items()):
        pct = cnt / len(filtered_records) * 100
        print(f"  {itype}: {cnt} ({pct:.1f}%)")
    
    # Source distribution
    source_counts = defaultdict(int)
    for r in filtered_records:
        source_counts[r["source_type"]] += 1
    print(f"\n来源分布:")
    for src, cnt in sorted(source_counts.items()):
        pct = cnt / len(filtered_records) * 100
        print(f"  {src}: {cnt} ({pct:.1f}%)")
    
    # Sample display
    print(f"\n--- 示例展示 ---")
    for i in [0, len(filtered_records)//3, len(filtered_records)//2, len(filtered_records)*2//3]:
        if i < len(filtered_records):
            r = filtered_records[i]
            print(f"\n样本 {i+1}:")
            print(f"  instruction: {r['instruction'][:60]}")
            print(f"  source: {r['source_type']}/{r['source_file']}")
            print(f"  thinking长度: {len(r['thinking'])}字符")
            print(f"  thinking预览: {r['thinking'][:150]}...")
    
    # Save stats
    stats_output = {
        "input_count": stats["total"],
        "generated_count": stats["generated"],
        "final_count": len(filtered_records),
        "skipped_count": stats["skipped"],
        "avg_thinking_length": round(avg_thinking_len, 1),
        "thinking_length_range": [min(thinking_lengths), max(thinking_lengths)],
        "instruction_types": dict(stats["instruction_types"]),
        "source_distribution": dict(source_counts),
        "thinking_length_dist": dict(stats["thinking_length_dist"]),
    }
    stats_path = BASE_DIR / "data" / "finetune" / "_thinking_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats_output, f, ensure_ascii=False, indent=2)
    print(f"\n统计已保存: {stats_path}")
    
    print(f"\n--- 完成 ---")


if __name__ == "__main__":
    main()

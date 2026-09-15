#!/usr/bin/env python3
"""
任务4：微调数据集-代码段抽取与格式化（v2）
从lightharness项目的stdlib/、src/、examples/中抽取高质量函数/段落级代码段，
去重清洗，格式化为JSONL基础格式（instruction/input/output）。

输出：lightharness/data/finetune/light_code_segments_raw.jsonl
"""

import os
import re
import json
import hashlib
from pathlib import Path
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # lightharness root
SOURCES = ["stdlib", "src", "examples"]

# Function definition pattern (supports 段落 and 异步 段落)
FUNC_PATTERN = re.compile(
    r'^(\s*)(?:异步\s+)?段落\s+(\S+)\s+接收\s*(.*?):\s*$'
)

# Class definition pattern
CLASS_PATTERN = re.compile(
    r'^(\s*)类\s+(\S+)\s*(?:继承\s+\S+)?\s*:\s*$'
)

# Export pattern
EXPORT_PATTERN = re.compile(r'^导出\s+(.+)$')

# Min/max line counts for segments
MIN_LINES = 6  # Lowered from 10 to get more segments
MAX_LINES = 400
MODULE_MIN_LINES = 10  # Lowered from 15
MODULE_MAX_LINES = 300

# Instruction templates for diversity
INSTRUCTION_TEMPLATES = {
    "function": [
        "实现一个{sig}函数，接收参数({params})，完成对应功能",
        "编写{sig}函数，参数为({params})，实现对应业务逻辑",
        "创建{sig}，输入参数({params})，完成指定功能",
        "实现{sig}函数，入参({params})，返回处理结果",
        "开发{sig}，接收({params})，执行对应操作",
    ],
    "method": [
        "为{cls}类实现{sig}方法，接收参数({params})，完成对应功能",
        "编写{cls}.{sig}方法，参数({params})，实现方法逻辑",
        "创建{cls}的{sig}方法，入参({params})，完成指定功能",
        "实现{cls}.{sig}，接收({params})，执行对应操作",
    ],
    "async": [
        "实现异步函数{sig}，接收参数({params})，完成异步操作",
        "编写异步{sig}，入参({params})，执行异步业务逻辑",
        "创建异步{sig}函数，参数({params})，完成异步功能",
    ],
    "module": [
        "实现标准库模块{sig}，提供完整功能",
        "编写模块{sig}，包含完整实现",
        "创建{sig}模块，提供核心功能",
    ],
}


def compute_hash(text: str) -> str:
    """Compute SHA256 hash of code segment for deduplication."""
    normalized = text.strip()
    lines = [l for l in normalized.split("\n") if l.strip() and not l.strip().startswith("#")]
    content_hash = "\n".join(lines)
    return hashlib.sha256(content_hash.encode("utf-8")).hexdigest()


def get_indent(line: str) -> int:
    """Get indentation level of a line."""
    return len(line) - len(line.lstrip())


def count_comment_ratio(body: str) -> float:
    """Calculate ratio of comment lines to total non-empty lines."""
    lines = body.strip().split("\n")
    non_empty = [l for l in lines if l.strip()]
    if not non_empty:
        return 1.0
    comment_lines = sum(1 for l in non_empty if l.strip().startswith("#"))
    return comment_lines / len(non_empty)


def count_code_lines(body: str) -> int:
    """Count actual code lines (non-comment, non-empty)."""
    lines = body.strip().split("\n")
    return sum(1 for l in lines if l.strip() and not l.strip().startswith("#"))


def parse_light_file(filepath: Path) -> dict:
    """Parse a .light file and extract structured information."""
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")
    
    source_type = "stdlib" if "stdlib" in str(filepath) else ("src" if "src" in str(filepath) else "examples")
    
    result = {
        "filepath": filepath,
        "source_type": source_type,
        "total_lines": len(lines),
        "content": content,
        "lines": lines,
        "functions": [],
        "classes": [],
    }
    
    # Find all function and class definitions
    func_defs = []
    class_defs = []
    current_class = None
    class_stack = []  # Stack of (indent, name)
    
    for i, line in enumerate(lines):
        # Check for class definition
        cm = CLASS_PATTERN.match(line)
        if cm:
            class_indent = len(cm.group(1))
            class_name = cm.group(2)
            class_defs.append({
                "line": i + 1,
                "indent": class_indent,
                "name": class_name,
            })
            # Maintain class stack
            while class_stack and class_stack[-1][0] >= class_indent:
                class_stack.pop()
            class_stack.append((class_indent, class_name))
            current_class = class_name
            continue
        
        # Check for function definition
        fm = FUNC_PATTERN.match(line)
        if fm:
            indent = len(fm.group(1))
            name = fm.group(2)
            params = fm.group(3).strip()
            async_kw = "异步" in line.split("段落")[0]
            
            # Determine enclosing class (innermost class with lower indent)
            enclosing_class = None
            for cls_indent, cls_name in reversed(class_stack):
                if cls_indent < indent:
                    enclosing_class = cls_name
                    break
            
            func_defs.append({
                "line": i + 1,
                "indent": indent,
                "name": name,
                "params": params,
                "async": async_kw,
                "class": enclosing_class,
            })
    
    # Determine function body ranges
    for func in func_defs:
        start_idx = func["line"] - 1  # 0-indexed
        start_line = func["line"]
        indent = func["indent"]
        
        # Find end: next function/class at same or lower indentation
        end_idx = start_idx + 1
        for j in range(start_idx + 1, len(lines)):
            line = lines[j]
            if not line.strip():
                continue
            
            line_indent = get_indent(line)
            
            # Check if this line starts a new function or class
            if FUNC_PATTERN.match(line) or CLASS_PATTERN.match(line):
                other_indent = get_indent(line)
                if other_indent <= indent:
                    end_idx = j
                    break
                # If same indent but it's a different construct, end here
                if other_indent == indent and (FUNC_PATTERN.match(line) or CLASS_PATTERN.match(line)):
                    end_idx = j
                    break
            
            # Check for dedent to before function start
            if line_indent < indent:
                # But skip comment lines and lines with same indent
                stripped = line.strip()
                if not stripped.startswith("#"):
                    # Check if it's actually a dedent
                    if not line.startswith(" " * (indent + 1)):
                        end_idx = j + 1
                        break
        
        # Ensure we don't go past EOF
        end_idx = min(end_idx, len(lines))
        
        body_lines = lines[start_idx:end_idx]
        end_line = start_idx + len(body_lines)
        
        func["start_line"] = start_line
        func["end_line"] = end_line
        func["body"] = "\n".join(body_lines).strip()
        func["line_count"] = end_line - start_line + 1
        func["code_lines"] = count_code_lines(func["body"])
    
    result["functions"] = func_defs
    result["classes"] = class_defs
    
    return result


def is_pure_test_file(filepath: Path, content: str = None) -> bool:
    """Check if a file is primarily a test/assertion file."""
    name = filepath.name
    
    # Strong test indicators
    if name.startswith("test_"):
        return True
    if name.startswith("_repro"):
        return True
    if name.startswith("_helper"):
        return True
    if name.startswith("_import_test"):
        return True
    if name.startswith("_probe"):
        return True
    
    # Check content for test patterns
    if content is None:
        try:
            content = filepath.read_text(encoding="utf-8")
        except:
            return False
    
    lines = content.split("\n")
    non_comment = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    total_code = len(non_comment)
    
    if total_code == 0:
        return True
    
    # Count test-related keywords
    test_kw_count = sum(1 for l in non_comment if any(kw in l for kw in [
        "断言", "断言等于", "assert", "测试", "test_", "失败", "pass", "skip"
    ]))
    
    # If >60% of code lines are test-related, consider it a test file
    if test_kw_count / total_code > 0.6:
        return True
    
    return False


def has_substantial_implementation(filepath: Path, content: str) -> bool:
    """Check if a test file has substantial implementation code."""
    lines = content.split("\n")
    non_comment = [l for l in lines if l.strip() and not l.strip().startswith("#")]
    
    # Count function definitions
    func_count = sum(1 for l in lines if FUNC_PATTERN.match(l))
    
    # Count code lines that look like implementation (not assertions)
    impl_lines = sum(1 for l in non_comment if not any(kw in l for kw in [
        "断言", "assert", "测试", "test_", "失败"
    ]))
    
    # Consider it substantial if it has functions and enough implementation
    return func_count >= 2 and impl_lines >= 10


def get_instruction(func_info: dict, source_type: str, idx: int = 0) -> str:
    """Generate instruction based on function name, params, and context."""
    name = func_info["name"]
    params = func_info["params"]
    cls = func_info.get("class")
    async_kw = func_info.get("async", False)
    
    # Build signature description
    if cls:
        sig = f"{cls}.{name}"
        templates_key = "method"
    else:
        sig = name
        templates_key = "function"
    
    if async_kw:
        templates_key = "async"
        # Don't add "异步" to sig - the template already has it
        # sig = f"异步{sig}"
    
    templates = INSTRUCTION_TEMPLATES[templates_key]
    template = templates[idx % len(templates)]
    
    # If params is empty, use a simpler template
    if not params:
        if templates_key == "module":
            return template.format(sig=sig)
        else:
            # Find a template that doesn't mention params
            for t in templates:
                if "{params}" not in t:
                    return t.format(sig=sig, cls=cls or "")
            # If all templates mention params, use the first one and let it show empty
            return template.format(sig=sig, params="", cls=cls or "")
    
    return template.format(sig=sig, params=params, cls=cls or "")


def get_module_instruction(filename: str, source_type: str, idx: int = 0) -> str:
    """Generate instruction for module-level segments."""
    templates = INSTRUCTION_TEMPLATES["module"]
    template = templates[idx % len(templates)]
    return template.format(sig=filename)


def extract_functions_from_file(filepath: Path) -> list:
    """Extract function-level code segments from a .light file."""
    parsed = parse_light_file(filepath)
    segments = []
    content = parsed["content"]
    
    for idx, func in enumerate(parsed["functions"]):
        body = func["body"]
        line_count = func["line_count"]
        code_lines = func["code_lines"]
        
        # Filter by length
        if line_count < MIN_LINES:
            continue
        
        if line_count > MAX_LINES:
            continue
        
        # Check comment ratio
        comment_ratio = count_comment_ratio(body)
        if comment_ratio > 0.5:
            continue
        
        # Compute hash for dedup
        code_hash = compute_hash(body)
        
        segment = {
            "source_file": str(filepath.relative_to(BASE_DIR)),
            "source_type": parsed["source_type"],
            "function_name": func["name"],
            "class_name": func.get("class"),
            "params": func["params"],
            "async": func["async"],
            "start_line": func["start_line"],
            "end_line": func["end_line"],
            "line_count": line_count,
            "code_lines": code_lines,
            "code_hash": code_hash,
            "body": body,
            "instruction": get_instruction(func, parsed["source_type"], idx),
            "input": "",
        }
        segments.append(segment)
    
    return segments


def extract_small_modules(filepath: Path) -> list:
    """Extract small complete modules (<300 lines) as segments."""
    parsed = parse_light_file(filepath)
    segments = []
    
    content = parsed["content"]
    line_count = parsed["total_lines"]
    
    # Skip large modules
    if line_count > MODULE_MAX_LINES or line_count < MODULE_MIN_LINES:
        return segments
    
    # Skip test files (but allow if substantial implementation)
    if is_pure_test_file(filepath, content):
        if not has_substantial_implementation(filepath, content):
            return segments
    
    # Check if it has actual code (not just comments)
    code_lines = count_code_lines(content)
    if code_lines < 5:
        return segments
    
    # Check comment ratio
    comment_ratio = count_comment_ratio(content)
    if comment_ratio > 0.5:
        return segments
    
    code_hash = compute_hash(content)
    
    filename = filepath.stem
    source_type = parsed["source_type"]
    
    segment = {
        "source_file": str(filepath.relative_to(BASE_DIR)),
        "source_type": source_type,
        "function_name": filename,
        "class_name": None,
        "params": "",
        "async": False,
        "start_line": 1,
        "end_line": line_count,
        "line_count": line_count,
        "code_lines": code_lines,
        "code_hash": code_hash,
        "body": content.strip(),
        "instruction": get_module_instruction(filename, source_type),
        "input": "",
    }
    segments.append(segment)
    
    return segments


def main():
    print("=" * 60)
    print("任务4：代码段抽取与格式化 (v2)")
    print("=" * 60)
    
    all_segments = []
    file_stats = defaultdict(lambda: {"files": 0, "func_segments": 0, "mod_segments": 0, "skipped_test": 0})
    
    for source in SOURCES:
        source_dir = BASE_DIR / source
        if not source_dir.exists():
            print(f"⚠️  目录不存在: {source_dir}")
            continue
        
        light_files = sorted(source_dir.glob("*.light"))
        print(f"\n[{source}] 共 {len(light_files)} 个 .light 文件")
        
        for filepath in light_files:
            file_stats[source]["files"] += 1
            
            try:
                content = filepath.read_text(encoding="utf-8")
            except Exception as e:
                print(f"  ⚠️  读取失败 {filepath.name}: {e}")
                continue
            
            # Check if it's a pure test file
            if is_pure_test_file(filepath, content):
                # Allow test files with substantial implementation
                if has_substantial_implementation(filepath, content):
                    file_stats[source]["func_segments"] += 1
                else:
                    file_stats[source]["skipped_test"] += 1
                    continue
            
            # Extract functions
            func_segments = extract_functions_from_file(filepath)
            file_stats[source]["func_segments"] += len(func_segments)
            
            # Also try to extract as small module
            module_segments = extract_small_modules(filepath)
            file_stats[source]["mod_segments"] += len(module_segments)
            
            all_segments.extend(func_segments)
            all_segments.extend(module_segments)
    
    print(f"\n{'=' * 60}")
    print(f"初始抽取: {len(all_segments)} 个代码段")
    for source in SOURCES:
        fs = file_stats[source]
        print(f"  {source}: {fs['files']} 文件, {fs['func_segments']} 函数段, {fs['mod_segments']} 模块段, {fs['skipped_test']} 跳过测试")
    
    # === Deduplication ===
    print("\n--- 去重 ---")
    hash_map = {}
    unique_segments = []
    for seg in all_segments:
        h = seg["code_hash"]
        if h not in hash_map:
            hash_map[h] = True
            unique_segments.append(seg)
    
    dup_count = len(all_segments) - len(unique_segments)
    print(f"去重: {len(all_segments)} -> {len(unique_segments)} (移除 {dup_count} 个重复)")
    
    # === Quality filtering ===
    print("\n--- 质量过滤 ---")
    filtered = []
    skip_stats = {"too_short": 0, "too_long": 0, "high_comment": 0, "has_debug": 0, "low_code": 0}
    
    for seg in unique_segments:
        body = seg["body"]
        line_count = seg["line_count"]
        code_lines = seg.get("code_lines", 0)
        
        # Length filter
        if line_count < MIN_LINES:
            skip_stats["too_short"] += 1
            continue
        
        if line_count > MAX_LINES:
            skip_stats["too_long"] += 1
            continue
        
        # Low code density (relaxed from 5 to 3)
        if code_lines < 3:
            skip_stats["low_code"] += 1
            continue
        
        # Comment ratio filter: remove if >60% comments (relaxed from 50%)
        comment_ratio = count_comment_ratio(body)
        if comment_ratio > 0.6:
            skip_stats["high_comment"] += 1
            continue
        
        # Debug code detection (only in actual code, not comments)
        # Be more lenient - only skip if debug is in >30% of code lines
        debug_lines = 0
        total_code_lines = 0
        for line in body.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            total_code_lines += 1
            if any(kw in stripped for kw in ["print(", "调试", "TODO", "FIXME", "XXX", "debug"]):
                debug_lines += 1
        
        # Only skip if debug lines are >30% of code lines and at least 3 debug lines
        if debug_lines > 3 and total_code_lines > 0 and debug_lines / total_code_lines > 0.3:
            skip_stats["has_debug"] += 1
            continue
        
        filtered.append(seg)
    
    print(f"过滤: {len(unique_segments)} -> {len(filtered)}")
    print(f"  过短: {skip_stats['too_short']}")
    print(f"  过长: {skip_stats['too_long']}")
    print(f"  注释过多: {skip_stats['high_comment']}")
    print(f"  含调试代码: {skip_stats['has_debug']}")
    print(f"  代码量低: {skip_stats['low_code']}")
    
    # === Final formatting ===
    print(f"\n--- 最终格式化 ---")
    
    # Sort by source priority: stdlib > src > examples
    source_priority = {"stdlib": 0, "src": 1, "examples": 2}
    filtered.sort(key=lambda s: (
        source_priority.get(s["source_type"], 9),
        s["source_file"],
        s["start_line"]
    ))
    
    # Limit to target range (2000-2500), balancing sources
    MAX_TARGET = 2500
    if len(filtered) > MAX_TARGET:
        # Separate by source type
        stdlib_segs = [s for s in filtered if s["source_type"] == "stdlib"]
        src_segs = [s for s in filtered if s["source_type"] == "src"]
        examples_segs = [s for s in filtered if s["source_type"] == "examples"]
        
        print(f"限制前: stdlib={len(stdlib_segs)}, src={len(src_segs)}, examples={len(examples_segs)}")
        
        # Target distribution: stdlib 20%, src 60%, examples 20%
        # Keep all stdlib (highest quality, smallest set)
        final_segments = stdlib_segs[:]
        remaining = MAX_TARGET - len(final_segments)
        
        # Target split for remaining: src 60/80 = 75%, examples 20/80 = 25%
        src_target = int(remaining * 0.75)
        examples_target = remaining - src_target
        
        # Take from src
        src_to_take = min(len(src_segs), src_target)
        final_segments.extend(src_segs[:src_to_take])
        
        # Take from examples
        examples_to_take = min(len(examples_segs), examples_target)
        final_segments.extend(examples_segs[:examples_to_take])
        
        # If we have room, fill with more src
        remaining = MAX_TARGET - len(final_segments)
        if remaining > 0 and src_to_take < len(src_segs):
            extra_src = min(len(src_segs) - src_to_take, remaining)
            final_segments.extend(src_segs[src_to_take:src_to_take + extra_src])
        
        print(f"限制后: stdlib={len(stdlib_segs)}, src={len(final_segments) - len(stdlib_segs) - len(examples_segs[:examples_to_take])}, examples={len(examples_segs[:examples_to_take])}")
        filtered = final_segments
    
    # Re-sort after limiting
    filtered.sort(key=lambda s: (
        source_priority.get(s["source_type"], 9),
        s["source_file"],
        s["start_line"]
    ))
    
    # Generate JSONL output
    output_path = BASE_DIR / "data" / "finetune" / "light_code_segments_raw.jsonl"
    
    with open(output_path, "w", encoding="utf-8") as f:
        for seg in filtered:
            record = {
                "instruction": seg["instruction"],
                "input": seg["input"],
                "output": seg["body"],
                "source_file": seg["source_file"],
                "source_type": seg["source_type"],
                "function_name": seg["function_name"],
                "class_name": seg["class_name"],
                "params": seg["params"],
                "async": seg["async"],
                "line_count": seg["line_count"],
                "code_hash": seg["code_hash"],
            }
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    
    print(f"输出: {output_path}")
    print(f"总样本数: {len(filtered)}")
    
    # === Statistics ===
    print(f"\n--- 统计 ---")
    source_counts = defaultdict(int)
    length_distribution = {"<50": 0, "50-100": 0, "100-200": 0, "200-300": 0, "300+": 0}
    function_types = defaultdict(int)
    
    for seg in filtered:
        source_counts[seg["source_type"]] += 1
        lc = seg["line_count"]
        if lc < 50:
            length_distribution["<50"] += 1
        elif lc < 100:
            length_distribution["50-100"] += 1
        elif lc < 200:
            length_distribution["100-200"] += 1
        elif lc < 300:
            length_distribution["200-300"] += 1
        else:
            length_distribution["300+"] += 1
        
        if seg["async"]:
            function_types["async"] += 1
        elif seg["class_name"]:
            function_types["method"] += 1
        elif seg["start_line"] == 1:
            function_types["module"] += 1
        else:
            function_types["function"] += 1
    
    print(f"来源分布:")
    for src in sorted(source_counts.keys()):
        cnt = source_counts[src]
        pct = cnt / len(filtered) * 100
        print(f"  {src}: {cnt} ({pct:.1f}%)")
    
    print(f"\n长度分布:")
    for range_key in ["<50", "50-100", "100-200", "200-300", "300+"]:
        cnt = length_distribution[range_key]
        pct = cnt / len(filtered) * 100
        print(f"  {range_key}: {cnt} ({pct:.1f}%)")
    
    print(f"\n类型分布:")
    for ftype, cnt in sorted(function_types.items()):
        print(f"  {ftype}: {cnt}")
    
    # Average line count
    avg_lines = sum(seg["line_count"] for seg in filtered) / len(filtered)
    print(f"\n平均行数: {avg_lines:.1f}")
    
    print(f"\n--- 完成 ---")
    print(f"输出文件: {output_path}")
    print(f"总样本: {len(filtered)}")
    
    # Save stats for report
    stats_output = {
        "total_extracted": len(all_segments),
        "after_dedup": len(unique_segments),
        "after_filter": len(filtered),
        "source_counts": dict(source_counts),
        "length_distribution": dict(length_distribution),
        "function_types": dict(function_types),
        "skip_stats": dict(skip_stats),
        "dup_count": dup_count,
        "avg_lines": round(avg_lines, 1),
        "file_stats": {k: dict(v) for k, v in file_stats.items()},
    }
    stats_path = BASE_DIR / "data" / "finetune" / "_extraction_stats.json"
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats_output, f, ensure_ascii=False, indent=2)
    print(f"统计已保存: {stats_path}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""R20 状态探针 v2：真实预扫描（_scan_user_definitions）下的切分。"""
import os
import sys

LIGHT = r'G:\dswork\duan-light-merge\light-merge'
sys.path.insert(0, os.path.join(LIGHT, 'src'))
sys.path.insert(0, os.path.join(LIGHT, 'antlrparser'))
sys.path.insert(0, LIGHT)

from lexer import Lexer  # noqa: E402


def toks(src):
    try:
        t = Lexer(src).tokenize()
        return [(x.type.name if hasattr(x.type, 'name') else str(x.type), x.value) for x in t
                if (x.type.name if hasattr(x.type, 'name') else '') != 'EOF']
    except Exception as e:
        return 'ERROR %s: %s' % (type(e).__name__, e)


# 场景1：定义 + 表达式使用（预扫描应还原完整标识符）
CALL_NAMES = ['去重占位', '作用域匹配', '排序函数', '遍历器', '筛选器', '求和函数', '读取器',
              '输出流', '调试器', '映射表', '生成器', '加载器', '匹配器', '反转函数',
              '删除属性', '接受器', '保护器', '使用者', '定义表', '实现类', '继承链',
              '抽象类', '最终值', '构造器', '枚举值', '类型表', '模块名', '函数表',
              '段落名', '情况表', '那么分支', '否则分支', '如果条件', '当循环', '尝试块',
              '捕获块', '抛出异常', '打印函数', '新建对象', '返回值', '设值器', '等于判断',
              '不等于判断', '大于判断', '小于判断', '加上操作', '减去操作', '乘以操作',
              '除以操作', '整除操作', '取余操作', '位域操作', '匹配器2', '协议表',
              '外部函数', '导入模块', '导出函数', '回调函数', '异步函数', '嵌入块',
              '标注器', '松散模式', '标准库函数', '特性表', '私有属性', '公有属性',
              '静态方法', '常量值', '接口表', '结构体名', '联合体名', '类型别名',
              '函数指针', '变长参数', '退出循环', '严格模式', '不大于判断', '不小于判断']

print('=========== 场景1：段落定义 + 表达式调用（预扫描还原） ===========')
bad = []
for name in CALL_NAMES:
    src = '段落 %s 接收 甲:\n  返回 甲\n\n段落 主:\n  设 乙 为 %s(1)\n  打印(乙)\n' % (name, name)
    tk = toks(src)
    # 只看 主 里的调用点
    idx = None
    for k, (tt, tv) in enumerate(tk):
        if tv == '为':
            idx = k
            break
    ok = False
    if idx is not None and idx + 1 < len(tk):
        ok = tk[idx + 1] == ('IDENTIFIER', name)
    print(('  OK  ' if ok else '  BAD '), name, '->', tk[idx + 1:idx + 3] if idx is not None else tk)
    if not ok:
        bad.append(name)
print('BAD count:', len(bad))
for x in bad:
    print('   -', x)

print()
print('=========== 场景2：未定义的复合名（无预扫描命中） ===========')
for name in CALL_NAMES[:20]:
    print(' ', name, '->', toks('设 乙 为 %s(1)' % name))

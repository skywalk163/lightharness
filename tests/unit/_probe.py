from test_support import run_light_source
cases = [
    ("exact_pass", '设 输入 为 {"拥有者":{"会话id":"s1"}, "建议名":"part1", "内容":"abc"}\n打印("OK")'),
    ("key_weizhi", '设 引 为 {"定位符":"x"}\n打印("OK")'),
    ("key_chaxun", '设 引 为 {"检索提示":"y"}\n打印("OK")'),
    ("two_kv", '设 引 为 {"a":"x", "b":"y"}\n打印("OK")'),
    ("nested", '设 引 为 {"拥有者":{"会话id":"s1"}, "k":"v"}\n打印("OK")'),
]
for label, src in cases:
    r = run_light_source(src)
    print(label, "RC=", r.rc, "OUT=", repr(r.stdout.strip()))

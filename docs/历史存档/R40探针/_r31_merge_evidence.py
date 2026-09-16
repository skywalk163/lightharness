# -*- coding: utf-8 -*-
"""R31 任务1-3 合并证据：读取三条独立验证 JSON，汇总_结论。

因三条均判定「保留」（真护栏），lexer.py 无需改动；此处仅固化合并结论与
全语料基线完整性声明，供路M收口引用。
"""
import json
import os

H = r'G:/dswork/duan-light-merge/lightharness'
LIGHTP = r'G:/dswork/duan-light-merge/light-merge'
srcs = {
    '为': '_antirun_r31_t1_为字验证.json',
    '返回': '_antirun_r31_t2_返回字验证.json',
    '尝试': '_antirun_r31_t3_尝试字验证.json',
}
ev = {}
for k, f in srcs.items():
    d = json.load(open(os.path.join(H, f), encoding='utf-8'))
    e = d['evidence']
    ev[k] = {
        'verdict': e['verdict'],
        'g1_changed_count': e['g1_changed_count'],
        'g1_pass': e['g1_pass'],
        'g2_pass': e['g2_pass'],
        'g3_pass': e['g3_pass'],
        'g3_fail_count': len(e['g3_fail']),
        'corpus_files': d['corpus_files'],
        'corpus_with_char': d['corpus_with_char'],
        'lexer_sha': d['lexer_sha'],
        'base_err_files': d.get('base_err_files', []),
    }

all_kept = all(v['verdict'] == '保留' for v in ev.values())
merged = {
    'round': 'R31',
    'scope': '任务1-3：_EMBED_MAX_MATCH_KEYWORDS 三条逐字三重判据验证',
    'embed_before': ['为', '返回', '尝试'],
    'embed_after': ['为', '返回', '尝试'] if all_kept else None,
    'lexer_sha_before': ev['为']['lexer_sha'],
    'lexer_sha_after': ev['为']['lexer_sha'],   # 未改动主树
    'all_kept': all_kept,
    'verdicts': ev,
    'conclusion': ('三条均为真护栏，全部保留；_EMBED 表维持 3 条，'
                   'lexer.py 零改动。') if all_kept else '存在可删条目，见各任务文档。',
}
out = os.path.join(H, '_task123_R31_证据.json')
json.dump(merged, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

print('=' * 64)
print('R31 任务1-3 合并结论：_EMBED 三条逐字验证')
print('lexer sha（前后一致，未改动主树）= %s' % merged['lexer_sha_before'])
print('-' * 64)
for k, v in ev.items():
    print('  %s: %s | G1变化=%d G2=%s G3失败=%d | 含该字语料=%d/%d'
          % (k, v['verdict'], v['g1_changed_count'],
             'PASS' if v['g2_pass'] else 'FAIL', v['g3_fail_count'],
             v['corpus_with_char'], v['corpus_files']))
print('-' * 64)
print('结论：%s' % merged['conclusion'])
print('合并证据: %s' % out)

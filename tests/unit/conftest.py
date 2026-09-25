# -*- coding: utf-8 -*-
"""pytest 配置：把 tests/unit 加入 sys.path，使 `from test_support import ...` 可用。"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

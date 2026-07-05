#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""兼容性导入层
自动解决常见的导入问题
"""

import sys
import importlib.util

# 检查是否能导入execjs
try:
    import execjs
except ImportError:
    try:
        # 尝试导入PyExecJS
        import PyExecJS as execjs
        sys.modules['execjs'] = execjs
        print("✅ 已创建execjs到PyExecJS的兼容层")
    except ImportError:
        print("❌ 无法创建execjs兼容层")

# 检查并修复zai-sdk导入问题
if importlib.util.find_spec('zai_sdk') is not None:
    import zai_sdk
    if importlib.util.find_spec('zai') is None:
        sys.modules['zai'] = zai_sdk
        print("✅ 已创建zai到zai_sdk的兼容层")

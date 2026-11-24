"""资源路径解析：源码运行走工程根，PyInstaller 打包后走 sys._MEIPASS。

所有 assets 下的资源必须经 resource_path() 拼接，禁止硬编码相对路径。
"""

from __future__ import annotations

import os
import sys


def resource_path(*parts: str) -> str:
    if getattr(sys, "frozen", False):            # PyInstaller 打包后
        # _MEIPASS 是 PyInstaller 注入的私有属性，用 getattr 访问避免静态检查告警
        base = getattr(sys, "_MEIPASS")
    else:                                        # 源码运行：src/ 的上一级即工程根
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)

"""最高分持久化：读写 %APPDATA%\\2048Desktop\\save.json，任何异常都降级不崩溃。"""

from __future__ import annotations

import json
import os
from pathlib import Path

from .config import APP_ID

APP_DIR = Path(os.environ.get("APPDATA") or Path.home()) / APP_ID
SAVE_FILE = APP_DIR / "save.json"


def load_best() -> int:
    """读取最高分；文件缺失、乱码、类型不对或负数一律按 0 处理。"""
    try:
        data = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
        return max(0, int(data.get("best", 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def save_best(best: int) -> None:
    """原子写入最高分：先写临时文件再 os.replace，避免写一半损坏。"""
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SAVE_FILE.with_name("save.tmp")
        tmp.write_text(json.dumps({"best": int(best)}, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, SAVE_FILE)
    except OSError:
        pass                             # 存档失败不影响游戏

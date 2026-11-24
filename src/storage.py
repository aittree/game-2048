"""持久化：最高分、显示设置、排行榜。

存档位于 %APPDATA%\\2048Desktop\\save.json；文件缺失、乱码或字段类型不对时降级为默认值，不崩溃。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import APP_ID

MAX_RECORDS = 10                # 排行榜保留条数

APP_DIR = Path(os.environ.get("APPDATA") or Path.home()) / APP_ID
SAVE_FILE = APP_DIR / "save.json"


@dataclass
class Record:
    name: str
    score: int
    time: str = ""


@dataclass
class Profile:
    best: int = 0
    fullscreen: bool = False
    leaderboard: list[Record] = field(default_factory=list)


def load_profile() -> Profile:
    """读取存档；兼容只有 {"best": n} 的旧版本文件。"""
    try:
        raw = json.loads(SAVE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Profile()
    if not isinstance(raw, dict):
        return Profile()

    best = raw.get("best", 0)
    records: list[Record] = []
    for item in raw.get("leaderboard") or []:
        if not isinstance(item, dict):
            continue
        name, score = item.get("name"), item.get("score")
        if isinstance(name, str) and isinstance(score, int):
            records.append(Record(name=name, score=score, time=str(item.get("time", ""))))
    records.sort(key=lambda r: -r.score)

    return Profile(
        best=best if isinstance(best, int) and best > 0 else 0,
        fullscreen=bool(raw.get("fullscreen", False)),
        leaderboard=records[:MAX_RECORDS],
    )


def save_profile(profile: Profile) -> None:
    """原子写入：先写临时文件再替换，避免写一半损坏存档；失败不影响游戏。"""
    data = {
        "best": profile.best,
        "fullscreen": profile.fullscreen,
        "leaderboard": [
            {"name": r.name, "score": r.score, "time": r.time} for r in profile.leaderboard
        ],
    }
    try:
        APP_DIR.mkdir(parents=True, exist_ok=True)
        tmp = SAVE_FILE.with_name("save.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, SAVE_FILE)
    except OSError:
        pass


def qualifies(profile: Profile, score: int) -> bool:
    """本局分数是否有资格进入前 10：0 分不入榜，满 10 条时需高于末位。"""
    if score <= 0:
        return False
    if len(profile.leaderboard) < MAX_RECORDS:
        return True
    return score > min(r.score for r in profile.leaderboard)


def insert_record(profile: Profile, name: str, score: int) -> int | None:
    """登记一条成绩，返回 0 起的名次；没资格进榜返回 None。"""
    if not qualifies(profile, score):
        return None
    record = Record(name=name, score=score, time=datetime.now().strftime("%Y-%m-%d %H:%M"))
    profile.leaderboard.append(record)
    profile.leaderboard.sort(key=lambda r: -r.score)   # 稳定排序：同分先到先得
    del profile.leaderboard[MAX_RECORDS:]
    return profile.leaderboard.index(record)

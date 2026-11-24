"""动画：维护滑动／合并／新块弹出的进度，只影响绘制，不改变逻辑。

逻辑在按键瞬间已结算到终态，动画只是把「起点 → 终点」插值播放（docs/03 §5.4）。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..config import ANIM_MS

if TYPE_CHECKING:
    from ..board import MoveResult

SLIDE_RATIO = 0.7            # 0~0.7 滑动，0.7~1.0 合并与新块缩放
MERGE_PULSE = 0.15           # 合并目标最大放大比例
NEW_TILE_START_SCALE = 0.6   # 新块弹出起始缩放


def ease_out_cubic(t: float) -> float:
    return 1 - (1 - t) ** 3


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


class Animator:
    def __init__(self, duration_ms: int = ANIM_MS) -> None:
        self.duration = duration_ms
        self.elapsed = duration_ms        # 初始为「已完成」，表示无动画
        self.result: "MoveResult | None" = None
        self.new_pos: tuple[int, int] | None = None

    @property
    def active(self) -> bool:
        return self.result is not None and self.elapsed < self.duration

    @property
    def progress(self) -> float:
        return min(1.0, self.elapsed / self.duration)

    def start(self, result: "MoveResult", new_pos: tuple[int, int] | None) -> None:
        self.result = result
        self.new_pos = new_pos
        self.elapsed = 0

    def stop(self) -> None:
        """立即结束动画（重开、撤销、关闭浮层时调用，避免旧动画叠在新局面上）。"""
        self.elapsed = self.duration
        self.result = None
        self.new_pos = None

    def update(self, dt_ms: int) -> None:
        if not self.active:
            return
        self.elapsed += dt_ms
        if self.elapsed >= self.duration:
            # 结束后清空，回到纯静态绘制，避免残留
            self.elapsed = self.duration
            self.result = None
            self.new_pos = None
